"""Phase 3C — Capability Registry policy composition tests.

Verifies the frozen composition rules: forbidden classes must be non-executable,
enabled requires verified trust + non-forbidden class, WRITE_CONFIRM /
ROLLBACK_CONFIRM / LIVE_PROVIDER_GATED gate coherence, READ_ONLY cannot carry a
write execution mode, EXPERIMENTAL_DISABLED is non-executable.

Phase: 3C — Static dev-only Capability Registry
"""

from __future__ import annotations

from hermes_cli.dev_web_capability_registry_policy import check_capability_policy


def _base(cid: str = "tool.read.x") -> dict:
    return {
        "capabilityId": cid,
        "category": "tool",
        "source": "static_manifest",
        "status": "enabled",
        "permissionClass": "READ_ONLY",
        "trustLevel": "BUILTIN_VERIFIED",
        "executionMode": "read_only",
        "routeExposure": "no_route",
        "requiresApproval": False,
        "requiresDryRun": False,
        "requiresConfirmation": False,
        "requiresAudit": True,
        "requiresBudget": False,
        "requiresKillSwitch": False,
        "devOnly": True,
        "productionAllowed": False,
    }


def _policy_errors(entry: dict) -> list[tuple[str, str]]:
    return [(e.field, e.reason) for e in check_capability_policy(entry)]


class TestForbiddenClassesNonExecutable:
    def test_admin_forbidden_enabled_rejected(self) -> None:
        e = _base()
        e["permissionClass"] = "ADMIN_FORBIDDEN"
        e["status"] = "enabled"
        assert _policy_errors(e)

    def test_external_forbidden_must_be_blocked(self) -> None:
        e = _base()
        e["permissionClass"] = "EXTERNAL_FORBIDDEN"
        e["trustLevel"] = "EXTERNAL_FORBIDDEN"
        e["status"] = "enabled"
        errs = _policy_errors(e)
        assert any(field == "EXTERNAL_FORBIDDEN" or "EXTERNAL_FORBIDDEN" in reason for field, reason in errs)
        assert any(field == "must be disabled or blocked" or "must be disabled or blocked" in reason for field, reason in errs)

    def test_production_forbidden_must_be_blocked(self) -> None:
        e = _base()
        e["permissionClass"] = "PRODUCTION_FORBIDDEN"
        e["trustLevel"] = "EXTERNAL_FORBIDDEN"
        e["status"] = "disabled"
        # disabled is acceptable for a forbidden class
        assert _policy_errors(e) == []

    def test_blocked_forbidden_ok(self) -> None:
        e = _base()
        e["permissionClass"] = "ADMIN_FORBIDDEN"
        e["trustLevel"] = "EXPERIMENTAL_DISABLED"
        e["status"] = "blocked"
        e["blockedReason"] = "x"
        assert _policy_errors(e) == []


class TestEnabledRequiresVerified:
    def test_enabled_with_experimental_disabled_rejected(self) -> None:
        e = _base()
        e["trustLevel"] = "EXPERIMENTAL_DISABLED"
        assert _policy_errors(e)

    def test_enabled_with_forbidden_class_rejected(self) -> None:
        e = _base()
        e["permissionClass"] = "ADMIN_FORBIDDEN"
        assert _policy_errors(e)


class TestGateCoherence:
    def test_write_confirm_requires_dry_run(self) -> None:
        e = _base()
        e["permissionClass"] = "WRITE_CONFIRM"
        e["executionMode"] = "confirmed_execute"
        e["requiresDryRun"] = False
        e["requiresConfirmation"] = True
        e["requiresAudit"] = True
        assert any(field == "dry-run" or "dry-run" in reason for field, reason in _policy_errors(e))

    def test_write_confirm_requires_confirmation(self) -> None:
        e = _base()
        e["permissionClass"] = "WRITE_CONFIRM"
        e["executionMode"] = "confirmed_execute"
        e["requiresDryRun"] = True
        e["requiresConfirmation"] = False
        e["requiresAudit"] = True
        assert any(field == "confirmation" or "confirmation" in reason for field, reason in _policy_errors(e))

    def test_write_confirm_requires_audit(self) -> None:
        e = _base()
        e["permissionClass"] = "WRITE_CONFIRM"
        e["executionMode"] = "confirmed_execute"
        e["requiresDryRun"] = True
        e["requiresConfirmation"] = True
        e["requiresAudit"] = False
        assert any(field == "audit" or "audit" in reason for field, reason in _policy_errors(e))

    def test_write_confirm_complete_ok(self) -> None:
        e = _base()
        e["permissionClass"] = "WRITE_CONFIRM"
        e["executionMode"] = "confirmed_execute"
        e["requiresDryRun"] = True
        e["requiresConfirmation"] = True
        e["requiresAudit"] = True
        assert _policy_errors(e) == []

    def test_rollback_confirm_requires_confirmation_and_audit(self) -> None:
        e = _base()
        e["permissionClass"] = "ROLLBACK_CONFIRM"
        e["executionMode"] = "confirmed_execute"
        e["requiresConfirmation"] = False
        e["requiresAudit"] = False
        errs = _policy_errors(e)
        assert any(field == "confirmation" or "confirmation" in reason for field, reason in errs)
        assert any(field == "audit" or "audit" in reason for field, reason in errs)

    def test_rollback_confirm_complete_ok(self) -> None:
        e = _base()
        e["permissionClass"] = "ROLLBACK_CONFIRM"
        e["executionMode"] = "confirmed_execute"
        e["requiresConfirmation"] = True
        e["requiresAudit"] = True
        assert _policy_errors(e) == []

    def test_live_provider_gated_requires_all_gates(self) -> None:
        e = _base()
        e["permissionClass"] = "LIVE_PROVIDER_GATED"
        e["executionMode"] = "manual_live"
        e["requiresAudit"] = False
        # missing approval, budget, killswitch, audit
        errs = _policy_errors(e)
        assert any(field == "approval" or "approval" in reason for field, reason in errs)
        assert any(field == "budget" or "budget" in reason for field, reason in errs)
        assert any(field == "kill-switch" or "kill-switch" in reason for field, reason in errs)
        assert any(field == "audit" or "audit" in reason for field, reason in errs)

    def test_live_provider_gated_complete_ok(self) -> None:
        e = _base()
        e["permissionClass"] = "LIVE_PROVIDER_GATED"
        e["executionMode"] = "manual_live"
        e["requiresApproval"] = True
        e["requiresBudget"] = True
        e["requiresKillSwitch"] = True
        e["requiresAudit"] = True
        assert _policy_errors(e) == []


class TestReadOnlyNoWriteGate:
    def test_read_only_cannot_confirmed_execute(self) -> None:
        e = _base()
        e["executionMode"] = "confirmed_execute"
        assert any(field == "READ_ONLY cannot use" or "READ_ONLY cannot use" in reason for field, reason in _policy_errors(e))

    def test_read_only_cannot_manual_live(self) -> None:
        e = _base()
        e["executionMode"] = "manual_live"
        assert any(field == "READ_ONLY cannot use" or "READ_ONLY cannot use" in reason for field, reason in _policy_errors(e))


class TestFirstVersionFlags:
    def test_dev_only_false_rejected(self) -> None:
        e = _base()
        e["devOnly"] = False
        assert any(field == "devOnly" or "devOnly" in reason for field, reason in _policy_errors(e))

    def test_production_allowed_true_rejected(self) -> None:
        e = _base()
        e["productionAllowed"] = True
        assert any(field == "productionAllowed" or "productionAllowed" in reason for field, reason in _policy_errors(e))

    def test_blocked_without_reason_rejected(self) -> None:
        e = _base()
        e["status"] = "blocked"
        e["permissionClass"] = "ADMIN_FORBIDDEN"
        e["trustLevel"] = "EXPERIMENTAL_DISABLED"
        assert any(field == "blockedReason" or "blockedReason" in reason for field, reason in _policy_errors(e))
