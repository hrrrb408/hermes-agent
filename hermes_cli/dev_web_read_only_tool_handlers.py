"""Phase 2A Read-only Tool Handlers for the Hermes Dev WebUI.

This module implements the five Phase 2A read-only inspection handlers and a
single ``dispatch_read_only_tool`` entry point used by the controlled-execution
handler-call gate (``dev_web_tool_handler_call.py``).

Each handler is a bounded, deterministic, side-effect-free pure function that
inspects only dev-local / in-process state. They are NOT registered Hermes
agent tools and are NOT part of the production tool dispatch path. They mirror
the bounded-reimplementation pattern used for the ``clarify`` handler: no
import of ``tools/`` (which would trigger production registry side effects),
no provider, no network write, no filesystem mutation, no shell execution that
mutates state.

Safety invariants (enforced structurally and re-checked here):
  - read-only: no writes, no DB mutation, no Provider, no production mutation
  - externalSideEffects is False: the only "I/O" is read-only inspection of
    dev-local in-process state, dev-only JSONL audit logs (containment-guarded),
    repo-local docs, and read-only process/port observation (ps/pgrep/lsof).
    No network calls, no file writes, no provider calls, no signaling of any
    process.
  - never accesses ``~/.hermes`` or production ``state.db``
  - never stops / restarts / replaces / signals the production gateway
  - never stores raw token / full tokenHash / raw arguments / secrets

All hermes_cli imports beyond the registry are lazy (inside functions) to keep
this module import-clean and avoid import cycles with the execute chain.

Phase: 2A — Real Tool Execution MVP (Read-only Multi-tool Execution)
Status: read-only handlers implemented
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable, Mapping

from hermes_cli.dev_web_read_only_tool_registry import (
    PHASE_2A_READ_ONLY_TOOL_IDS,
    get_read_only_tool_definition,
    normalize_read_only_tool_arguments,
)


# ---------------------------------------------------------------------------
# 1. Constants
# ---------------------------------------------------------------------------

# Production Gateway expected PID baseline (Phase 1G-10A refreshed value).
# This is READ-ONLY observation only: the handler compares the observed PID
# against this baseline and reports drift as a warning. It NEVER stops,
# restarts, replaces, or signals the gateway. A future authorized refresh
# phase updates this constant; it is not updated by Phase 2A.
PRODUCTION_GATEWAY_EXPECTED_PID = 1962
PRODUCTION_GATEWAY_COMMAND_PATTERN = "hermes_cli.main gateway run"

# Dev WebUI ports (read-only observation).
_DEV_PORT_5180 = 5180
_DEV_PORT_5181 = 5181

# Bounded output limits (mirrors dev_web_tool_policy output caps).
_MAX_RESULT_BYTES = 64 * 1024  # 64 KiB serialized
_MAX_DOCS_LISTED = 200

# Release-status constants (sealed Phase 1G facts + Phase 2/2A status).
_PHASE_1G_STATUS = "SEALED"
_PHASE_2_STATUS = "UNLOCKED"
_PHASE_2A_STATUS = "in_progress"
_FINAL_SEAL_ID = "FINAL-SEAL-1G-11-001"
_PHASE_2_UNLOCK_ID = "PHASE-2-UNLOCK-1G-11-001"
_HUMAN_DECISION_ID = "HUMAN-DECISION-1G-10B-001"
_NEXT_RECOMMENDED_PHASE = "Phase 2B — Provider Schema / API Controlled Integration"

# Secret redaction (bounded, stdlib-only — mirrors the execute gate).
_SECRET_VALUE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"sk-[a-zA-Z0-9_\-]{8,}"),
    re.compile(r"Bearer\s+\S+", re.IGNORECASE),
    re.compile(r"Authorization\s*:\s*\S+", re.IGNORECASE),
    re.compile(r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----"),
)
_REDACTED_VALUE = "[REDACTED]"


def _redact_value(value: Any) -> Any:
    """Redact secret-looking string values recursively."""
    if isinstance(value, str):
        for pattern in _SECRET_VALUE_PATTERNS:
            if pattern.search(value):
                return _REDACTED_VALUE
        return value
    if isinstance(value, dict):
        return {k: _redact_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact_value(v) for v in value]
    return value


def _truncate_result(value: Any) -> Any:
    """Bound the serialized size of a result to _MAX_RESULT_BYTES."""
    import json

    try:
        serialized = json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        return {"error": "result_not_json_serializable"}
    if len(serialized) <= _MAX_RESULT_BYTES:
        return value
    # Truncate large structures defensively.
    return {
        "truncated": True,
        "originalSizeBytes": len(serialized),
        "maxBytes": _MAX_RESULT_BYTES,
        "preview": serialized[: _MAX_RESULT_BYTES // 2],
    }


# ---------------------------------------------------------------------------
# 2. Handler: tool_policy_read
# ---------------------------------------------------------------------------


def handle_tool_policy_read(
    arguments: Mapping[str, Any] | None,
    hermes_home: str | None,  # noqa: ARG001 — unused, kept for uniform signature
) -> dict[str, Any]:
    """Return the current tool-execution policy summary.

    Pure in-process read of the policy module constants. No filesystem, no
    network, no provider, no production access.
    """
    from hermes_cli.dev_web_tool_policy import (
        CANDIDATE_ALLOWLIST,
        STATIC_ALLOWLIST,
        STATIC_DENYLIST,
    )

    include_disabled = bool(arguments.get("includeDisabled", False)) if arguments else False

    result: dict[str, Any] = {
        "staticAllowlist": sorted(STATIC_ALLOWLIST),
        "staticAllowlistSize": len(STATIC_ALLOWLIST),
        "candidateAllowlist": sorted(CANDIDATE_ALLOWLIST),
        "candidateAllowlistSize": len(CANDIDATE_ALLOWLIST),
        "readOnly": True,
        "providerRequired": False,
        "writeRequired": False,
        "externalSideEffects": False,
        "phase2aReadOnlyTools": sorted(PHASE_2A_READ_ONLY_TOOL_IDS),
        "phaseBoundaries": {
            "providerSchemaSent": False,
            "providerApiCalled": False,
            "toolWriteRoutes": 0,
            "clarifySupported": "clarify" in STATIC_ALLOWLIST,
        },
    }
    if include_disabled:
        result["disabledToolCount"] = len(STATIC_DENYLIST)
        result["disabledToolReason"] = (
            "Tools not on the read-only allowlist are blocked by the static "
            "allowlist gate (Gate 3) and cannot reach execution in Phase 2A."
        )

    return {
        "type": "tool_policy_read",
        "message": (
            f"Static allowlist has {len(STATIC_ALLOWLIST)} tool(s); "
            f"{len(PHASE_2A_READ_ONLY_TOOL_IDS)} Phase 2A read-only tools."
        ),
        "result": _truncate_result(_redact_value(result)),
    }


# ---------------------------------------------------------------------------
# 3. Handler: route_governance_read
# ---------------------------------------------------------------------------


def handle_route_governance_read(
    arguments: Mapping[str, Any] | None,
    hermes_home: str | None,  # noqa: ARG001 — unused
) -> dict[str, Any]:
    """Return the current route-governance summary by introspecting the app.

    Builds a stateless app instance (``hermes_home=None``) and counts routes the
    same way the route-governance tests do, so the reported numbers are
    guaranteed consistent with the frozen Phase 1G baseline (34/34/5/0/1/1)
    unless the contract genuinely drifted.
    """
    include_details = bool(arguments.get("includeDetails", False)) if arguments else False

    from hermes_cli.dev_web_api import create_dev_web_api_app
    from hermes_cli.dev_web_config import DevWebApiConfig

    app = create_dev_web_api_app(DevWebApiConfig(hermes_home=None))
    prefix = DevWebApiConfig().api_prefix

    # OpenAPI paths under the business prefix.
    try:
        spec = app.openapi()
        openapi_paths = [p for p in spec.get("paths", {}) if p.startswith(prefix)]
    except Exception:
        openapi_paths = []

    # Runtime routes (starlette Route objects with a .path).
    runtime_paths: list[str] = []
    for route in app.routes:
        path = getattr(route, "path", None)
        if isinstance(path, str) and path.startswith(prefix):
            runtime_paths.append(path)

    # Tool GET routes under /tools.
    tool_get_routes: list[str] = []
    for p in openapi_paths:
        if p.startswith(f"{prefix}/tools"):
            methods = spec.get("paths", {}).get(p, {})
            if "get" in methods:
                tool_get_routes.append(p)

    # Tool write routes: any mutating method under /tools EXCEPT dry-run/execute.
    _write_methods = {"post", "put", "patch", "delete"}
    _non_write_tool_routes = {f"{prefix}/tools/dry-run", f"{prefix}/tools/execute"}
    tool_write_routes: list[str] = []
    for p in openapi_paths:
        if not p.startswith(f"{prefix}/tools"):
            continue
        methods = spec.get("paths", {}).get(p, {})
        mutating = _write_methods & set(methods.keys())
        if mutating and p not in _non_write_tool_routes:
            tool_write_routes.append(p)

    tool_dry_run_routes = [p for p in openapi_paths if p == f"{prefix}/tools/dry-run"]
    tool_execution_routes = [p for p in openapi_paths if p == f"{prefix}/tools/execute"]

    from hermes_cli.dev_web_tool_policy import STATIC_ALLOWLIST

    result: dict[str, Any] = {
        "openApiPaths": len(openapi_paths),
        "runtimeRoutes": len(runtime_paths),
        "toolGetRoutes": len(tool_get_routes),
        "toolWriteRoutes": len(tool_write_routes),
        "toolDryRunRoutes": len(tool_dry_run_routes),
        "toolExecutionRoutes": len(tool_execution_routes),
        "staticAllowlist": sorted(STATIC_ALLOWLIST),
        "routeGovernanceStatus": "frozen_baseline" if len(openapi_paths) == 34 else "warning",
    }
    if len(openapi_paths) != 34 or len(tool_write_routes) != 0:
        result["warning"] = "route_governance_baseline_drift_detected"

    if include_details:
        result["details"] = {
            "openApiBusinessPaths": sorted(openapi_paths),
            "toolGetRoutePaths": sorted(tool_get_routes),
        }

    return {
        "type": "route_governance_read",
        "message": (
            f"OpenAPI paths={len(openapi_paths)}, runtime routes={len(runtime_paths)}, "
            f"tool GET={len(tool_get_routes)}, write={len(tool_write_routes)}, "
            f"dry-run={len(tool_dry_run_routes)}, execution={len(tool_execution_routes)}."
        ),
        "result": _truncate_result(_redact_value(result)),
    }


# ---------------------------------------------------------------------------
# 4. Handler: audit_events_read
# ---------------------------------------------------------------------------


def handle_audit_events_read(
    arguments: Mapping[str, Any] | None,
    hermes_home: str | None,
) -> dict[str, Any]:
    """Return a bounded, redacted audit-event summary from the dev JSONL stores.

    Reads only the dev HERMES_HOME audit stores via the containment-guarded
    ``read_audit_events`` reader. Never reads ``~/.hermes`` or production
    ``state.db`` (the reader rejects those paths).
    """
    from hermes_cli.dev_web_tool_audit_read import read_audit_events

    args = arguments or {}
    limit = args.get("limit", 20)
    if not isinstance(limit, int) or limit < 1:
        limit = 20
    limit = min(limit, 100)

    filters_applied: dict[str, Any] = {}
    tool_id_filter = args.get("toolId")
    if isinstance(tool_id_filter, str) and tool_id_filter.strip():
        filters_applied["toolId"] = tool_id_filter.strip()

    # Query each audit kind with a bounded limit. The reader normalizes and
    # redacts every item (never raw token / tokenHash / raw arguments).
    items: list[dict[str, Any]] = []
    for kind in ("dry_run", "pre_execution", "post_execution"):
        read_result = read_audit_events(
            audit_kind=kind,
            limit=limit,
            canonical_name=tool_id_filter if isinstance(tool_id_filter, str) else None,
            hermes_home=hermes_home,
        )
        if read_result.success:
            for item in read_result.items:
                enriched = dict(item)
                enriched["auditKind"] = kind
                # Optional in-memory filters (eventType / status / correlationId).
                if _matches_optional_filter(enriched, args):
                    items.append(enriched)

    event_type_filter = args.get("eventType")
    if isinstance(event_type_filter, str) and event_type_filter.strip():
        filters_applied["eventType"] = event_type_filter.strip()
    status_filter = args.get("status")
    if isinstance(status_filter, str) and status_filter.strip():
        filters_applied["status"] = status_filter.strip()
    correlation_id_filter = args.get("correlationId")
    if isinstance(correlation_id_filter, str) and correlation_id_filter.strip():
        filters_applied["correlationId"] = correlation_id_filter.strip()

    result: dict[str, Any] = {
        "items": items,
        "count": len(items),
        "hasMore": len(items) >= limit,
        "filtersApplied": filters_applied,
        "redactionApplied": True,
    }

    return {
        "type": "audit_events_read",
        "message": f"Returned {len(items)} redacted audit event(s) across 3 kinds.",
        "result": _truncate_result(_redact_value(result)),
    }


def _matches_optional_filter(item: dict[str, Any], args: Mapping[str, Any]) -> bool:
    """Apply optional eventType / status / correlationId filters in memory."""
    event_type = args.get("eventType")
    if isinstance(event_type, str) and event_type.strip():
        # item["decision"] holds the eventType-derived value for post_execution;
        # for dry_run it holds the dry-run decision. Match loosely.
        haystack = str(item.get("decision") or item.get("auditKind") or "")
        if event_type.strip() not in haystack:
            return False
    status = args.get("status")
    if isinstance(status, str) and status.strip():
        haystack = " ".join(
            str(item.get(k) or "") for k in ("executionStatus", "handlerCallStatus", "decision")
        )
        if status.strip() not in haystack:
            return False
    correlation_id = args.get("correlationId")
    if isinstance(correlation_id, str) and correlation_id.strip():
        haystack = " ".join(
            str(item.get(k) or "")
            for k in (
                "executeRequestId",
                "handlerLookupId",
                "dispatchId",
                "handlerCallId",
                "preExecutionAuditId",
                "dryRunRequestId",
            )
        )
        if correlation_id.strip() not in haystack:
            return False
    return True


# ---------------------------------------------------------------------------
# 5. Handler: dev_environment_read
# ---------------------------------------------------------------------------


def _probe_system_state() -> dict[str, Any]:
    """Read-only, defensive system-state probe.

    Uses ``shutil.which`` before shelling out, bounds output, and swallows all
    errors to safe defaults. NEVER accesses ``~/.hermes``, NEVER reads
    production ``state.db``, NEVER stops / restarts / replaces / signals any
    process. ``ps`` / ``pgrep`` / ``lsof`` are read-only process/port
    inspection only.
    """
    state: dict[str, Any] = {
        "productionGatewayPidObserved": None,
        "productionGatewayProcessCount": 0,
        "productionGatewayCommandSummary": None,
        "port5180": "unknown",
        "port5181": "unknown",
    }

    # Production gateway observation (read-only pgrep).
    pgrep = shutil.which("pgrep")
    if pgrep:
        try:
            proc = subprocess.run(
                [pgrep, "-f", PRODUCTION_GATEWAY_COMMAND_PATTERN],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            pids = [line.strip() for line in proc.stdout.splitlines() if line.strip().isdigit()]
            state["productionGatewayProcessCount"] = len(pids)
            if pids:
                state["productionGatewayPidObserved"] = int(pids[0])
        except (OSError, subprocess.SubprocessError, ValueError):
            state["productionGatewayProcessCount"] = 0

    # Port observation (read-only lsof).
    lsof = shutil.which("lsof")
    if lsof:
        for port_key, port_num in (("port5180", _DEV_PORT_5180), ("port5181", _DEV_PORT_5181)):
            try:
                proc = subprocess.run(
                    [lsof, "-nP", f"-iTCP:{port_num}", "-sTCP:LISTEN"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )
                state[port_key] = "in_use" if proc.stdout.strip() else "free"
            except (OSError, subprocess.SubprocessError):
                state[port_key] = "unknown"

    return state


def handle_dev_environment_read(
    arguments: Mapping[str, Any] | None,
    hermes_home: str | None,
) -> dict[str, Any]:
    """Return the dev environment health summary.

    Pure read-only: HERMES_HOME identity, dev gateway status (from env), port
    observation, and read-only production gateway PID/count observation. Never
    accesses ``~/.hermes`` or production ``state.db``; never signals the
    gateway.
    """
    args = arguments or {}
    include_ports = bool(args.get("includePorts", True))
    include_prod_check = bool(args.get("includeProductionGatewayReadOnlyCheck", True))

    # Resolve and validate the dev HERMES_HOME (without touching production).
    home_env = os.environ.get("HERMES_HOME", "") or (hermes_home or "")
    is_dev_home = False
    home_display = ""
    if home_env:
        try:
            home_path = Path(home_env).resolve()
            prod_path = Path.home() / ".hermes"
            is_dev_home = home_path != prod_path.resolve()
            # Display only the basename + a sanitized form (no secret exposure).
            home_display = str(home_path)
        except (OSError, ValueError):
            is_dev_home = False
            home_display = ""

    result: dict[str, Any] = {
        "hermesHome": home_display,
        "isDevHome": is_dev_home,
        "devGatewayStatus": "unknown",
        "productionGatewayPidExpected": PRODUCTION_GATEWAY_EXPECTED_PID,
    }

    # Dev gateway status from env (kill-switch presence), read-only.
    dev_gateway_status = "not_running"
    if os.environ.get("HERMES_AGENT_RUN_ENABLED", "").strip() == "true":
        dev_gateway_status = "enabled_flag_set"
    result["devGatewayStatus"] = dev_gateway_status

    if include_ports or include_prod_check:
        probe = _probe_system_state()
        if include_prod_check:
            result["productionGatewayPidObserved"] = probe["productionGatewayPidObserved"]
            result["productionGatewayProcessCount"] = probe["productionGatewayProcessCount"]
            result["productionGatewayCommandSummary"] = (
                f"{PRODUCTION_GATEWAY_COMMAND_PATTERN} (read-only observation)"
            )
            observed = probe["productionGatewayPidObserved"]
            if observed is None or observed != PRODUCTION_GATEWAY_EXPECTED_PID:
                result["productionSafetyStatus"] = "warning"
                result["warning"] = "production_gateway_pid_drift"
            else:
                result["productionSafetyStatus"] = "baseline_confirmed"
        if include_ports:
            result["port5180"] = probe["port5180"]
            result["port5181"] = probe["port5181"]

    return {
        "type": "dev_environment_read",
        "message": (
            f"HERMES_HOME is dev={is_dev_home}; production gateway PID "
            f"observed={result.get('productionGatewayPidObserved')} "
            f"(expected {PRODUCTION_GATEWAY_EXPECTED_PID})."
        ),
        "result": _truncate_result(_redact_value(result)),
    }


# ---------------------------------------------------------------------------
# 6. Handler: release_status_read
# ---------------------------------------------------------------------------


def handle_release_status_read(
    arguments: Mapping[str, Any] | None,
    hermes_home: str | None,  # noqa: ARG001 — unused
) -> dict[str, Any]:
    """Return the docs/webui release-status summary.

    Reads only repo-local ``docs/webui/`` files. Never reads arbitrary user
    paths or ``~/.hermes``.
    """
    args = arguments or {}
    include_timeline = bool(args.get("includePhaseTimeline", False))
    include_p2_backlog = bool(args.get("includeP2Backlog", False))

    # Locate the repo docs/webui directory (relative to this module).
    docs_dir = Path(__file__).resolve().parents[1] / "docs" / "webui"
    phase_docs: list[str] = []
    seal_doc_present = False
    if docs_dir.is_dir():
        try:
            for entry in sorted(docs_dir.iterdir()):
                if len(phase_docs) >= _MAX_DOCS_LISTED:
                    break
                name = entry.name
                if entry.is_file() and name.endswith(".md") and not name.startswith("."):
                    phase_docs.append(name)
                    if "phase-1g-11-final-release-seal" in name:
                        seal_doc_present = True
        except OSError:
            phase_docs = []

    result: dict[str, Any] = {
        "phase1gStatus": _PHASE_1G_STATUS,
        "phase2Status": _PHASE_2_STATUS,
        "phase2aStatus": _PHASE_2A_STATUS,
        "finalSealId": _FINAL_SEAL_ID,
        "phase2UnlockId": _PHASE_2_UNLOCK_ID,
        "humanDecisionId": _HUMAN_DECISION_ID,
        "releaseAuthorization": "granted_by_designated_human_approver",
        "sealDocPresent": seal_doc_present,
        "docsWebuiFileCount": len(phase_docs),
        "nextRecommendedPhase": _NEXT_RECOMMENDED_PHASE,
    }

    if include_timeline:
        result["phaseTimeline"] = [
            {"phase": "Phase 1G", "status": _PHASE_1G_STATUS},
            {"phase": "Phase 2", "status": _PHASE_2_STATUS},
            {"phase": "Phase 2A", "status": _PHASE_2A_STATUS},
            {"phase": "Phase 2B", "status": "not_started"},
            {"phase": "Phase 2C", "status": "not_started"},
        ]

    if include_p2_backlog:
        result["p2Backlog"] = [
            "Phase 2B — Provider Schema / API Controlled Integration",
            "Phase 2C — Tool Write Controlled Execution",
            "Phase 2D — Audit Hardening",
            "Phase 2E — Frontend Polish",
        ]

    # A bounded, sanitized list of repo doc basenames (no full paths, no secrets).
    result["docsWebuiBasenames"] = phase_docs

    return {
        "type": "release_status_read",
        "message": (
            f"Phase 1G {_PHASE_1G_STATUS}, Phase 2 {_PHASE_2_STATUS}, "
            f"Phase 2A {_PHASE_2A_STATUS}."
        ),
        "result": _truncate_result(_redact_value(result)),
    }


# ---------------------------------------------------------------------------
# 7. Dispatch table + entry point
# ---------------------------------------------------------------------------

# Each handler has a uniform (arguments, hermes_home) -> dict signature.
# Arguments arriving here are ALREADY normalized by the registry's
# validate/normalize functions (called from build_handler_call_plan), so the
# handlers receive only whitelisted, type-checked, secret-free values.
_READ_ONLY_HANDLERS: dict[str, Callable[[Mapping[str, Any] | None, str | None], dict[str, Any]]] = {
    "tool_policy_read": handle_tool_policy_read,
    "route_governance_read": handle_route_governance_read,
    "audit_events_read": handle_audit_events_read,
    "dev_environment_read": handle_dev_environment_read,
    "release_status_read": handle_release_status_read,
}


def dispatch_read_only_tool(
    tool_id: str,
    arguments: Mapping[str, Any] | None,
    *,
    hermes_home: str | None = None,
) -> dict[str, Any]:
    """Dispatch a Phase 2A read-only tool to its bounded handler.

    Pre-normalizes arguments through the registry whitelist so handlers never
    receive untrusted input. Returns the safe result envelope
    ``{"type": <toolId>, "message": <summary>, "result": <structured>}``.

    Raises ``ValueError`` for an unknown tool id (the caller — the handler-call
    gate — only reaches this for verified Phase 2A read-only tools, so this is
    a defense-in-depth backstop, never expected in practice).
    """
    if tool_id not in PHASE_2A_READ_ONLY_TOOL_IDS:
        raise ValueError(f"Unknown Phase 2A read-only tool: {tool_id!r}")

    normalized = normalize_read_only_tool_arguments(tool_id, arguments)
    handler = _READ_ONLY_HANDLERS[tool_id]
    raw_result = handler(normalized, hermes_home)

    # Defense-in-depth: every handler result is re-redacted and size-bounded.
    if not isinstance(raw_result, dict):
        return {
            "type": tool_id,
            "message": "Read-only tool returned an invalid result shape.",
            "result": {"error": "invalid_handler_result_shape"},
        }
    raw_result["result"] = _truncate_result(_redact_value(raw_result.get("result", {})))
    return raw_result


def supported_read_only_tool_ids() -> frozenset[str]:
    """Return the set of Phase 2A read-only tool ids (for gate checks)."""
    return PHASE_2A_READ_ONLY_TOOL_IDS
