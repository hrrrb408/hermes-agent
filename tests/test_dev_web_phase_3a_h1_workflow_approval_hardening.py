"""Phase 3A-H1 — Workflow approval gate hardening (Lens 6: Token Scope Boundary).

Adversarial boundary tests for the step approval: it lives under the dedicated
``workflow_step_approval`` scope (distinct from ``write_execute`` /
``rollback_execute`` / ``provider_write_preview_confirm``), is single-use,
step-bound (execution + step + digest), TTL-bounded, cannot authorize a write
or rollback execution, and never persists the plain token / raw arguments.
The expiry + replay + cross-scope + cross-step + changed-input paths are all
blocked with the precise workflow blocked reason.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hermes_cli.dev_web_confirmation_store import (
    SCOPE_PROVIDER_WRITE_PREVIEW_CONFIRM,
    SCOPE_ROLLBACK_EXECUTE,
    SCOPE_WORKFLOW_STEP_APPROVAL,
    SCOPE_WRITE_EXECUTE,
    VALID_SCOPES,
    create_confirmation_token,
    verify_confirmation_token,
)
from hermes_cli.dev_web_workflow_approval import (
    _map_token_blocked_reason,
    compute_step_digest,
    consume_step_approval,
    issue_step_approval,
    verify_step_approval,
)
from hermes_cli.dev_web_workflow_schema import (
    BLOCKED_APPROVAL_ALREADY_USED,
    BLOCKED_APPROVAL_DIGEST_MISMATCH,
    BLOCKED_APPROVAL_EXPIRED,
    BLOCKED_APPROVAL_REQUIRED,
    BLOCKED_APPROVAL_SCOPE_MISMATCH,
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


# ---------------------------------------------------------------------------
# 1. Scope registration + isolation
# ---------------------------------------------------------------------------


class TestScopeIsolation:
    def test_workflow_scope_registered(self) -> None:
        assert SCOPE_WORKFLOW_STEP_APPROVAL == "workflow_step_approval"
        assert SCOPE_WORKFLOW_STEP_APPROVAL in VALID_SCOPES

    def test_workflow_scope_is_distinct_from_write_and_rollback(self) -> None:
        assert SCOPE_WORKFLOW_STEP_APPROVAL != SCOPE_WRITE_EXECUTE
        assert SCOPE_WORKFLOW_STEP_APPROVAL != SCOPE_ROLLBACK_EXECUTE
        assert SCOPE_WORKFLOW_STEP_APPROVAL != SCOPE_PROVIDER_WRITE_PREVIEW_CONFIRM

    def test_workflow_token_cannot_authorize_write_execute(self, dev_home: str) -> None:
        issue = create_confirmation_token(
            {"x": 1}, scope=SCOPE_WORKFLOW_STEP_APPROVAL, argument_digest="d" * 64,
            hermes_home=dev_home,
        )
        assert issue is not None
        res = verify_confirmation_token(
            issue.token, expected_scope=SCOPE_WRITE_EXECUTE, expected_digest="d" * 64,
            hermes_home=dev_home,
        )
        assert not res.verified  # scope mismatch — never a write authorization

    def test_workflow_token_cannot_authorize_rollback_execute(self, dev_home: str) -> None:
        issue = create_confirmation_token(
            {"x": 1}, scope=SCOPE_WORKFLOW_STEP_APPROVAL, argument_digest="d" * 64,
            hermes_home=dev_home,
        )
        res = verify_confirmation_token(
            issue.token, expected_scope=SCOPE_ROLLBACK_EXECUTE, expected_digest="d" * 64,
            hermes_home=dev_home,
        )
        assert not res.verified


# ---------------------------------------------------------------------------
# 2. Issue + verify (happy path)
# ---------------------------------------------------------------------------


class TestIssueVerify:
    def test_issue_and_verify_same_step(self, dev_home: str) -> None:
        wfx, step = _wfx(), new_workflow_id("wfs_")
        issue = issue_step_approval(
            workflow_execution_id=wfx, step_id=step, step_type=STEP_READ_ONLY_TOOL,
            step_input={"includePorts": True}, hermes_home=dev_home,
        )
        assert issue.issued
        assert issue.raw_token is not None
        assert issue.approval is not None
        # The approval id IS the underlying confirmation-token id (cft_…).
        assert issue.approval.approval_id.startswith("cft_")
        v = verify_step_approval(
            raw_token=issue.raw_token, workflow_execution_id=wfx, step_id=step,
            step_type=STEP_READ_ONLY_TOOL, step_input={"includePorts": True}, hermes_home=dev_home,
        )
        assert v.verified

    def test_missing_token_blocked(self, dev_home: str) -> None:
        v = verify_step_approval(
            raw_token=None, workflow_execution_id=_wfx(), step_id="wfs_a",
            step_type=STEP_READ_ONLY_TOOL, step_input={}, hermes_home=dev_home,
        )
        assert not v.verified
        assert v.blocked_reason == BLOCKED_APPROVAL_REQUIRED

    def test_malformed_execution_id_blocked(self, dev_home: str) -> None:
        issue = issue_step_approval(
            workflow_execution_id="not_a_wfx_id", step_id="wfs_a",
            step_type=STEP_READ_ONLY_TOOL, step_input={}, hermes_home=dev_home,
        )
        assert not issue.issued
        assert issue.blocked_reason == BLOCKED_APPROVAL_STEP_MISMATCH


# ---------------------------------------------------------------------------
# 3. Binding (step + execution + digest)
# ---------------------------------------------------------------------------


class TestStepBinding:
    def test_wrong_step_blocked(self, dev_home: str) -> None:
        wfx = _wfx()
        issue = issue_step_approval(
            workflow_execution_id=wfx, step_id="wfs_a", step_type=STEP_READ_ONLY_TOOL,
            step_input={"includePorts": True}, hermes_home=dev_home,
        )
        v = verify_step_approval(
            raw_token=issue.raw_token, workflow_execution_id=wfx, step_id="wfs_b",
            step_type=STEP_READ_ONLY_TOOL, step_input={"includePorts": True}, hermes_home=dev_home,
        )
        assert not v.verified
        assert v.blocked_reason in (BLOCKED_APPROVAL_STEP_MISMATCH, BLOCKED_APPROVAL_DIGEST_MISMATCH)

    def test_changed_input_blocked(self, dev_home: str) -> None:
        wfx, step = _wfx(), new_workflow_id("wfs_")
        issue = issue_step_approval(
            workflow_execution_id=wfx, step_id=step, step_type=STEP_READ_ONLY_TOOL,
            step_input={"includePorts": True}, hermes_home=dev_home,
        )
        v = verify_step_approval(
            raw_token=issue.raw_token, workflow_execution_id=wfx, step_id=step,
            step_type=STEP_READ_ONLY_TOOL, step_input={"includePorts": False}, hermes_home=dev_home,
        )
        assert not v.verified
        assert v.blocked_reason == BLOCKED_APPROVAL_DIGEST_MISMATCH

    def test_digest_is_deterministic_and_input_sensitive(self) -> None:
        d1 = compute_step_digest(workflow_execution_id="wfx_1", step_id="wfs_1", step_type=STEP_READ_ONLY_TOOL, step_input={"a": 1})
        d2 = compute_step_digest(workflow_execution_id="wfx_1", step_id="wfs_1", step_type=STEP_READ_ONLY_TOOL, step_input={"a": 1})
        d3 = compute_step_digest(workflow_execution_id="wfx_1", step_id="wfs_1", step_type=STEP_READ_ONLY_TOOL, step_input={"a": 2})
        assert d1 == d2
        assert d1 != d3
        # 256-bit hex digest.
        assert len(d1) == 64


# ---------------------------------------------------------------------------
# 4. Single-use consumption
# ---------------------------------------------------------------------------


class TestSingleUse:
    def test_consume_twice_rejected(self, dev_home: str) -> None:
        wfx, step = _wfx(), new_workflow_id("wfs_")
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

    def test_consume_does_not_verify_on_mismatch(self, dev_home: str) -> None:
        wfx, step = _wfx(), new_workflow_id("wfs_")
        issue = issue_step_approval(
            workflow_execution_id=wfx, step_id=step, step_type=STEP_READ_ONLY_TOOL,
            step_input={"a": 1}, hermes_home=dev_home,
        )
        c = consume_step_approval(
            raw_token=issue.raw_token, workflow_execution_id=wfx, step_id=step,
            step_type=STEP_READ_ONLY_TOOL, step_input={"a": 2}, hermes_home=dev_home,
        )
        assert not c.verified


# ---------------------------------------------------------------------------
# 5. Expiry
# ---------------------------------------------------------------------------


class TestExpiry:
    def test_expired_token_blocked(self, dev_home: str) -> None:
        wfx, step = _wfx(), new_workflow_id("wfs_")
        # ttl_seconds=0 → the token expires the instant it is issued; by the
        # time verify runs, _now() > expires_at.
        issue = issue_step_approval(
            workflow_execution_id=wfx, step_id=step, step_type=STEP_READ_ONLY_TOOL,
            step_input={}, hermes_home=dev_home, ttl_seconds=0,
        )
        assert issue.issued
        v = verify_step_approval(
            raw_token=issue.raw_token, workflow_execution_id=wfx, step_id=step,
            step_type=STEP_READ_ONLY_TOOL, step_input={}, hermes_home=dev_home,
        )
        assert not v.verified
        assert v.blocked_reason == BLOCKED_APPROVAL_EXPIRED

    def test_expired_reason_maps_correctly(self) -> None:
        # The blocked-reason mapping for the underlying store's EXPIRED reason
        # resolves to the workflow approval EXPIRED reason.
        from hermes_cli.dev_web_confirmation_store import BLOCKED_TOKEN_EXPIRED

        assert _map_token_blocked_reason(BLOCKED_TOKEN_EXPIRED) == BLOCKED_APPROVAL_EXPIRED

    def test_scope_mismatch_maps_correctly(self) -> None:
        from hermes_cli.dev_web_confirmation_store import BLOCKED_TOKEN_SCOPE_MISMATCH

        assert _map_token_blocked_reason(BLOCKED_TOKEN_SCOPE_MISMATCH) == BLOCKED_APPROVAL_SCOPE_MISMATCH


# ---------------------------------------------------------------------------
# 6. No plain-token / raw-argument persistence
# ---------------------------------------------------------------------------


class TestNoSecretPersistence:
    def test_plain_token_never_persisted(self, dev_home: str) -> None:
        wfx, step = _wfx(), new_workflow_id("wfs_")
        issue = issue_step_approval(
            workflow_execution_id=wfx, step_id=step, step_type=STEP_READ_ONLY_TOOL,
            step_input={"secretish": "sk-" + "a" * 20}, hermes_home=dev_home,
        )
        assert issue.issued
        # The raw token is `cft_….secret`; the secret portion must never appear
        # in any file under the dev home.
        token_secret = issue.raw_token.split(".", 1)[1]
        for path in Path(dev_home).rglob("*.json"):
            blob = path.read_text(encoding="utf-8")
            assert token_secret not in blob, f"token secret persisted in {path}"
            # And no raw step input arguments are persisted on the token record.
            data = json.loads(blob)
            assert "secretish" not in json.dumps(data)

    def test_record_is_valid_json(self, dev_home: str) -> None:
        wfx, step = _wfx(), new_workflow_id("wfs_")
        issue = issue_step_approval(
            workflow_execution_id=wfx, step_id=step, step_type=STEP_READ_ONLY_TOOL,
            step_input={}, hermes_home=dev_home,
        )
        token_id = issue.raw_token.split(".", 1)[0]
        token_dir = Path(dev_home) / "gateway" / "dev" / "tool-confirmation-tokens"
        record = json.loads((token_dir / f"{token_id}.json").read_text("utf-8"))
        assert record["tokenId"] == token_id
        assert record["scope"] == SCOPE_WORKFLOW_STEP_APPROVAL
