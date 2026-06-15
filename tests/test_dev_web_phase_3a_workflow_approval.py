"""Phase 3A — Workflow approval gate tests.

Verifies the step approval: it reuses the Phase 2C-H1 confirmation store under
the ``workflow_step_approval`` scope, is single-use, step-bound (step + execution
+ digest), TTL-bounded, and never authorizes write/rollback execution (those
keep their own scopes).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_cli.dev_web_confirmation_store import (
    SCOPE_WORKFLOW_STEP_APPROVAL,
    VALID_SCOPES,
    create_confirmation_token,
    verify_confirmation_token,
)
from hermes_cli.dev_web_workflow_approval import (
    compute_step_digest,
    consume_step_approval,
    issue_step_approval,
    verify_step_approval,
)
from hermes_cli.dev_web_workflow_schema import (
    BLOCKED_APPROVAL_ALREADY_USED,
    BLOCKED_APPROVAL_DIGEST_MISMATCH,
    BLOCKED_APPROVAL_REQUIRED,
    BLOCKED_APPROVAL_STEP_MISMATCH,
    STEP_READ_ONLY_TOOL,
    new_workflow_id,
)


@pytest.fixture
def dev_home(tmp_path: Path) -> str:
    home = tmp_path / "hermes-home-dev"
    home.mkdir()
    return str(home)


def _wfx() -> str:
    return new_workflow_id("wfx_")


class TestScopeRegistration:
    def test_workflow_scope_registered(self) -> None:
        assert SCOPE_WORKFLOW_STEP_APPROVAL in VALID_SCOPES
        assert SCOPE_WORKFLOW_STEP_APPROVAL == "workflow_step_approval"

    def test_workflow_scope_cannot_authorize_write(self, dev_home: str) -> None:
        # A workflow-scoped token must NOT verify under the write_execute scope.
        issue = create_confirmation_token(
            {"x": 1}, scope=SCOPE_WORKFLOW_STEP_APPROVAL, argument_digest="d" * 64,
            hermes_home=dev_home,
        )
        assert issue is not None
        res = verify_confirmation_token(
            issue.token, expected_scope="write_execute", expected_digest="d" * 64,
            hermes_home=dev_home,
        )
        assert not res.verified  # scope mismatch


class TestIssueVerifyConsume:
    def test_issue_and_verify_same_step(self, dev_home: str) -> None:
        wfx = _wfx()
        step = new_workflow_id("wfs_")
        issue = issue_step_approval(
            workflow_execution_id=wfx, step_id=step, step_type=STEP_READ_ONLY_TOOL,
            step_input={"includePorts": True}, hermes_home=dev_home,
        )
        assert issue.issued
        assert issue.raw_token is not None
        v = verify_step_approval(
            raw_token=issue.raw_token, workflow_execution_id=wfx, step_id=step,
            step_type=STEP_READ_ONLY_TOOL, step_input={"includePorts": True},
            hermes_home=dev_home,
        )
        assert v.verified

    def test_wrong_step_blocked(self, dev_home: str) -> None:
        wfx = _wfx()
        issue = issue_step_approval(
            workflow_execution_id=wfx, step_id="wfs_a", step_type=STEP_READ_ONLY_TOOL,
            step_input={"includePorts": True}, hermes_home=dev_home,
        )
        v = verify_step_approval(
            raw_token=issue.raw_token, workflow_execution_id=wfx, step_id="wfs_b",
            step_type=STEP_READ_ONLY_TOOL, step_input={"includePorts": True},
            hermes_home=dev_home,
        )
        assert not v.verified
        assert v.blocked_reason in (BLOCKED_APPROVAL_STEP_MISMATCH, BLOCKED_APPROVAL_DIGEST_MISMATCH)

    def test_changed_input_blocked(self, dev_home: str) -> None:
        wfx = _wfx()
        step = new_workflow_id("wfs_")
        issue = issue_step_approval(
            workflow_execution_id=wfx, step_id=step, step_type=STEP_READ_ONLY_TOOL,
            step_input={"includePorts": True}, hermes_home=dev_home,
        )
        v = verify_step_approval(
            raw_token=issue.raw_token, workflow_execution_id=wfx, step_id=step,
            step_type=STEP_READ_ONLY_TOOL, step_input={"includePorts": False},
            hermes_home=dev_home,
        )
        assert not v.verified
        assert v.blocked_reason == BLOCKED_APPROVAL_DIGEST_MISMATCH

    def test_single_use_enforced(self, dev_home: str) -> None:
        wfx = _wfx()
        step = new_workflow_id("wfs_")
        issue = issue_step_approval(
            workflow_execution_id=wfx, step_id=step, step_type=STEP_READ_ONLY_TOOL,
            step_input={}, hermes_home=dev_home,
        )
        c1 = consume_step_approval(
            raw_token=issue.raw_token, workflow_execution_id=wfx, step_id=step,
            step_type=STEP_READ_ONLY_TOOL, step_input={}, hermes_home=dev_home,
        )
        assert c1.verified
        c2 = consume_step_approval(
            raw_token=issue.raw_token, workflow_execution_id=wfx, step_id=step,
            step_type=STEP_READ_ONLY_TOOL, step_input={}, hermes_home=dev_home,
        )
        assert not c2.verified
        assert c2.blocked_reason == BLOCKED_APPROVAL_ALREADY_USED

    def test_missing_token_blocked(self, dev_home: str) -> None:
        v = verify_step_approval(
            raw_token=None, workflow_execution_id=_wfx(), step_id="wfs_a",
            step_type=STEP_READ_ONLY_TOOL, step_input={}, hermes_home=dev_home,
        )
        assert not v.verified
        assert v.blocked_reason == BLOCKED_APPROVAL_REQUIRED

    def test_digest_is_deterministic(self) -> None:
        d1 = compute_step_digest(workflow_execution_id="wfx_1", step_id="wfs_1", step_type=STEP_READ_ONLY_TOOL, step_input={"a": 1})
        d2 = compute_step_digest(workflow_execution_id="wfx_1", step_id="wfs_1", step_type=STEP_READ_ONLY_TOOL, step_input={"a": 1})
        d3 = compute_step_digest(workflow_execution_id="wfx_1", step_id="wfs_1", step_type=STEP_READ_ONLY_TOOL, step_input={"a": 2})
        assert d1 == d2
        assert d1 != d3
