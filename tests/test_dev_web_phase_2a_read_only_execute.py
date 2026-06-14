"""Phase 2A — Read-only tool execute tests.

Verifies the full Phase 1G controlled-execution chain admits each Phase 2A
read-only tool end-to-end (dry-run -> confirmation token -> digest verification
-> pre-execution audit -> handler lookup -> dispatch planning -> handler call
-> post-execution audit), and that the block reasons still fire for unsupported
tools, missing confirmation tokens, and digest mismatches.

Exports ``run_read_only_tool_to_completion`` for reuse by the audit test.

Phase: 2A — Real Tool Execution MVP (Read-only Multi-tool Execution)
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from hermes_cli.dev_web_tool_execute import evaluate_tool_execute_request
from hermes_cli.dev_web_tool_execute_confirmation import issue_confirmation_token
from hermes_cli.dev_web_tool_execute_digest import build_dry_run_decision_digest_package
from hermes_cli.dev_web_tool_execute_preflight import DryRunHistoricalLookupResult
from hermes_cli.dev_web_tool_dry_run import dry_run_tool_policy

# (tool_id, risk_tier)
READ_ONLY_TOOLS_WITH_RISK = [
    ("tool_policy_read", "R0"),
    ("route_governance_read", "R0"),
    ("audit_events_read", "R1"),
    ("dev_environment_read", "R1"),
    ("release_status_read", "R1"),
]


def _make_audit_event(
    *, request_id: str, tool_id: str, risk_tier: str, timestamp: str, digest: str
) -> dict[str, Any]:
    return {
        "eventId": f"evt-{tool_id}",
        "eventType": "tool_dry_run",
        "timestamp": timestamp,
        "schemaVersion": 1,
        "phase": "2A",
        "requestId": request_id,
        "canonicalName": tool_id,
        "toolExists": True,
        "riskTier": risk_tier,
        "decision": "would_allow",
        "reasonCodes": [],
        "policyNotes": [],
        "forbiddenFields": [],
        "missingRequiredFields": [],
        "redactionApplied": False,
        "redactionReasonCodes": [],
        "redactedArgumentsPreview": {},
        "sourceContext": None,
        "uiOrigin": None,
        "executionAllowed": False,
        "dispatchAllowed": False,
        "providerSchemaAllowed": False,
        "auditWritten": True,
        "staticAllowlistSize": 6,
        "candidateAllowlistMatched": True,
        "denylistMatched": False,
        "durationMs": None,
        "resultStatus": "ok",
        "errorCode": None,
        "errorClass": None,
        "dryRunDecisionDigest": digest,
        "digestAlgorithm": "sha256",
        "digestPackageVersion": "1",
        "canonicalizationVersion": "json-sort-v1",
    }


def run_read_only_tool_to_completion(
    hermes_home: str,
    tool_id: str,
    *,
    risk_tier: str,
    arguments: dict[str, Any] | None = None,
    monkeypatch_probe: Any = None,
) -> dict[str, Any]:
    """Drive one read-only tool through the full controlled-execution chain.

    Returns the execute result safe-dict. Asserts the dry-run would_allow and
    that the token issues successfully.
    """
    import os

    os.environ["HERMES_TOOL_EXECUTION_ENABLED"] = "true"
    os.environ["HERMES_AGENT_TOOLS_ENABLED"] = "true"
    os.environ["HERMES_TOOL_HANDLER_CALL_ENABLED"] = "true"

    if monkeypatch_probe is not None:
        import hermes_cli.dev_web_read_only_tool_handlers as handlers

        handlers._probe_system_state = monkeypatch_probe  # type: ignore[attr-defined]

    # 1. dry-run
    dr = dry_run_tool_policy(tool_id, arguments)
    assert dr.decision == "would_allow", f"{tool_id}: {dr.decision}"

    request_id = f"req-{tool_id}"
    fixed_ts = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    computed_expires = (
        datetime.fromisoformat(fixed_ts) + timedelta(seconds=300)
    ).isoformat()

    # 2. digest package
    dp = build_dry_run_decision_digest_package(
        dry_run_request_id=request_id,
        canonical_name=tool_id,
        risk_tier=risk_tier,
        policy_decision="would_allow",
        allowlisted=True,
        audit_written=True,
        audit_event_id=f"evt-{tool_id}",
        arguments=arguments,
        created_at=fixed_ts,
        expires_at=computed_expires,
    )
    assert dp.success
    digest = dp.digest

    # 3. write the audit event carrying the digest
    audit_path = f"{hermes_home}/gateway/dev/audit/tool-dry-run-audit.jsonl"
    event = _make_audit_event(
        request_id=request_id,
        tool_id=tool_id,
        risk_tier=risk_tier,
        timestamp=fixed_ts,
        digest=digest,
    )
    with open(audit_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")

    # 4. issue confirmation token
    now = datetime.now(timezone.utc)
    dr_record = DryRunHistoricalLookupResult(
        found=True,
        error_code=None,
        dry_run_request_id=request_id,
        canonical_name=tool_id,
        decision="would_allow",
        risk_tier=risk_tier,
        policy_version=None,
        arguments_digest=None,
        dry_run_decision_digest=digest,
        audit_written=True,
        audit_event_id=f"evt-{tool_id}",
        created_at=fixed_ts,
        expires_at=computed_expires,
        lookup_source="test",
        redaction_status="none",
        safe_summary={},
    )
    tok = issue_confirmation_token(
        hermes_home=hermes_home,
        dry_run_record=dr_record,
        canonical_name=tool_id,
        risk_tier=risk_tier,
        dry_run_request_id=request_id,
        dry_run_decision_digest=digest,
        now=now,
    )
    assert tok.issued, f"{tool_id}: token issue failed {tok.error_code}"

    # 5. execute
    result = evaluate_tool_execute_request(
        canonical_name=tool_id,
        arguments_preview=arguments,
        dry_run_request_id=request_id,
        dry_run_decision_digest=digest,
        confirmation_token=tok.raw_token,
        request_id=f"exec-{tool_id}",
        hermes_home=hermes_home,
    )
    return result.to_safe_dict()


@pytest.fixture
def phase_2a_home(tmp_path):
    home = tmp_path / "hermes-home-dev"
    (home / "gateway" / "dev" / "audit").mkdir(parents=True, exist_ok=True)
    (home / "gateway" / "dev" / "tokens").mkdir(parents=True, exist_ok=True)
    return str(home)


class TestReadOnlyExecuteCompletion:
    @pytest.mark.parametrize("tool_id,risk_tier", READ_ONLY_TOOLS_WITH_RISK)
    def test_read_only_tool_completes(self, phase_2a_home, tool_id, risk_tier) -> None:
        # dev_environment_read probes the system; inject a safe fake so the
        # test never depends on real production state.
        fake_probe = lambda: {  # noqa: E731
            "productionGatewayPidObserved": 28428,
            "productionGatewayProcessCount": 1,
            "productionGatewayCommandSummary": "hermes_cli.main gateway run",
            "port5180": "free",
            "port5181": "free",
        }
        rd = run_read_only_tool_to_completion(
            phase_2a_home, tool_id, risk_tier=risk_tier, monkeypatch_probe=fake_probe
        )
        assert rd["executionCompleted"] is True, f"{tool_id}: {rd['decision']} {rd.get('errorCode')}"
        assert rd["toolHandlerCalled"] is True

    @pytest.mark.parametrize("tool_id,risk_tier", READ_ONLY_TOOLS_WITH_RISK)
    def test_provider_flags_stay_false(self, phase_2a_home, tool_id, risk_tier) -> None:
        fake_probe = lambda: {  # noqa: E731
            "productionGatewayPidObserved": 28428,
            "productionGatewayProcessCount": 1,
            "productionGatewayCommandSummary": "x",
            "port5180": "free",
            "port5181": "free",
        }
        rd = run_read_only_tool_to_completion(
            phase_2a_home, tool_id, risk_tier=risk_tier, monkeypatch_probe=fake_probe
        )
        se = rd["sideEffects"]
        assert se["providerSchemaSent"] is False
        assert se["providerApiCalled"] is False
        assert se["externalSideEffects"] is False
        assert se["filesystemChanged"] is False
        assert se["networkCalled"] is False
        # Top-level policy flags also stay False.
        assert rd["executionAllowed"] is False
        assert rd["dispatchAllowed"] is False
        assert rd["providerSchemaAllowed"] is False
        assert rd["providerApiCalled"] is False

    @pytest.mark.parametrize("tool_id,risk_tier", READ_ONLY_TOOLS_WITH_RISK)
    def test_decision_and_preview_type_per_tool(
        self, phase_2a_home, tool_id, risk_tier
    ) -> None:
        fake_probe = lambda: {  # noqa: E731
            "productionGatewayPidObserved": 28428, "productionGatewayProcessCount": 1,
            "productionGatewayCommandSummary": "x", "port5180": "free", "port5181": "free",
        }
        rd = run_read_only_tool_to_completion(
            phase_2a_home, tool_id, risk_tier=risk_tier, monkeypatch_probe=fake_probe
        )
        assert rd["decision"] == f"{tool_id}_execution_completed"
        assert rd["resultPreview"]["previewType"] == tool_id
        tr = rd["toolResult"]
        assert tr["type"] == tool_id
        assert isinstance(tr.get("result"), dict)
        assert isinstance(tr.get("message"), str)

    @pytest.mark.parametrize("tool_id,risk_tier", READ_ONLY_TOOLS_WITH_RISK)
    def test_full_audit_chain_ids_present(
        self, phase_2a_home, tool_id, risk_tier
    ) -> None:
        fake_probe = lambda: {  # noqa: E731
            "productionGatewayPidObserved": 28428, "productionGatewayProcessCount": 1,
            "productionGatewayCommandSummary": "x", "port5180": "free", "port5181": "free",
        }
        rd = run_read_only_tool_to_completion(
            phase_2a_home, tool_id, risk_tier=risk_tier, monkeypatch_probe=fake_probe
        )
        assert rd["preExecutionAuditId"].startswith("pea_")
        assert rd["executeRequestId"].startswith("exe_")
        assert rd["handlerLookupId"].startswith("hl_")
        assert rd["dispatchId"].startswith("dsp_")
        assert rd["handlerCallId"].startswith("thc_")
        assert rd["postExecutionAuditId"].startswith("pexa_")


class TestReadOnlyExecuteBlockReasons:
    def test_unsupported_tool_blocked_by_allowlist(self, phase_2a_home) -> None:
        # read_file is a candidate but NOT on STATIC_ALLOWLIST -> blocked.
        import os

        os.environ["HERMES_TOOL_EXECUTION_ENABLED"] = "true"
        os.environ["HERMES_AGENT_TOOLS_ENABLED"] = "true"
        os.environ["HERMES_TOOL_HANDLER_CALL_ENABLED"] = "true"
        result = evaluate_tool_execute_request(
            canonical_name="read_file",
            dry_run_request_id="req-x",
            dry_run_decision_digest="sha256:x",
            confirmation_token="tok",
            hermes_home=phase_2a_home,
        )
        rd = result.to_safe_dict()
        assert rd["executionCompleted"] is False
        assert rd["decision"] == "blocked_by_allowlist"

    def test_missing_confirmation_token_blocks(self, phase_2a_home) -> None:
        import os

        os.environ["HERMES_TOOL_EXECUTION_ENABLED"] = "true"
        os.environ["HERMES_AGENT_TOOLS_ENABLED"] = "true"
        os.environ["HERMES_TOOL_HANDLER_CALL_ENABLED"] = "true"
        # tool_policy_read is allowlisted, but no confirmation token supplied.
        result = evaluate_tool_execute_request(
            canonical_name="tool_policy_read",
            dry_run_request_id="req-nobody",
            dry_run_decision_digest=None,
            confirmation_token=None,
            hermes_home=phase_2a_home,
        )
        rd = result.to_safe_dict()
        assert rd["executionCompleted"] is False
        # The chain blocks before reaching the handler.
        assert rd["toolHandlerCalled"] is False

    def test_digest_mismatch_blocks(self, phase_2a_home) -> None:
        # Build a valid audit+token for tool_policy_read, then execute with a
        # tampered (mismatched) digest — the chain must block before the handler.
        import os

        os.environ["HERMES_TOOL_EXECUTION_ENABLED"] = "true"
        os.environ["HERMES_AGENT_TOOLS_ENABLED"] = "true"
        os.environ["HERMES_TOOL_HANDLER_CALL_ENABLED"] = "true"
        tool_id, risk_tier = "tool_policy_read", "R0"
        request_id = "req-mismatch"
        fixed_ts = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        computed_expires = (
            datetime.fromisoformat(fixed_ts) + timedelta(seconds=300)
        ).isoformat()
        dp = build_dry_run_decision_digest_package(
            dry_run_request_id=request_id, canonical_name=tool_id, risk_tier=risk_tier,
            policy_decision="would_allow", allowlisted=True, audit_written=True,
            audit_event_id=f"evt-{tool_id}-m", created_at=fixed_ts, expires_at=computed_expires,
        )
        real_digest = dp.digest
        event = _make_audit_event(
            request_id=request_id, tool_id=tool_id, risk_tier=risk_tier,
            timestamp=fixed_ts, digest=real_digest,
        )
        with open(f"{phase_2a_home}/gateway/dev/audit/tool-dry-run-audit.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
        now = datetime.now(timezone.utc)
        dr_record = DryRunHistoricalLookupResult(
            found=True, error_code=None, dry_run_request_id=request_id,
            canonical_name=tool_id, decision="would_allow", risk_tier=risk_tier,
            policy_version=None, arguments_digest=None,
            dry_run_decision_digest=real_digest, audit_written=True,
            audit_event_id=f"evt-{tool_id}-m", created_at=fixed_ts,
            expires_at=computed_expires, lookup_source="test",
            redaction_status="none", safe_summary={},
        )
        tok = issue_confirmation_token(
            hermes_home=phase_2a_home, dry_run_record=dr_record,
            canonical_name=tool_id, risk_tier=risk_tier,
            dry_run_request_id=request_id, dry_run_decision_digest=real_digest, now=now,
        )
        assert tok.issued
        # Execute with a MISMATCHED digest.
        result = evaluate_tool_execute_request(
            canonical_name=tool_id, dry_run_request_id=request_id,
            dry_run_decision_digest="sha256:0000000000000000000000000000000000000000000000000000000000000000",
            confirmation_token=tok.raw_token, hermes_home=phase_2a_home,
        )
        rd = result.to_safe_dict()
        assert rd["executionCompleted"] is False
        assert rd["toolHandlerCalled"] is False


if __name__ == "__main__":
    raise SystemExit(__import__("pytest").main([__file__, "-q"]))
