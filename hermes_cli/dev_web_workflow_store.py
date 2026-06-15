"""Phase 3A Dev-only Workflow State Store for the Hermes Dev WebUI.

A dev-only, file-backed store for the manual Agent Workflow MVP. Each workflow
definition, execution state, and timeline is a JSON document under
``$HERMES_HOME/gateway/dev/workflow-store`` (dev HERMES_HOME only).

Security / integrity model (frozen):
  - confined to the dev ``HERMES_HOME``; never ``~/.hermes``, never the repo,
    never production ``state.db``
  - atomic writes (temp file + ``os.replace``); a crashed write never leaves a
    half-written document
  - corruption-safe: a malformed document is skipped (returns ``None`` /
    read-only), never leaked to the caller, never crashes the API
  - advisory file lock (``fcntl`` on Unix; ImportError-guarded fallback) so two
    concurrent API workers cannot interleave a timeline append
  - every persisted field is JSON-native; the safe-dict round-trip drops raw
    tokens / hashes / arguments / file content / API keys / callables
  - stdlib only; no network, no shell, no database, no provider

Phase: 3A — Dev-only Agent Workflow MVP
Status: workflow state store implemented
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from hermes_cli.dev_web_workflow_schema import (
    STEP_MANUAL_NOTE,
    WORKFLOW_AUDIT_ID_PREFIX,
    WORKFLOW_EXECUTION_ID_PREFIX,
    WORKFLOW_ID_PREFIX,
    WORKFLOW_PLAN_ID_PREFIX,
    WORKFLOW_SAFETY_BOUNDARY,
    WORKFLOW_SCHEMA_VERSION,
    WorkflowAuditLink,
    WorkflowDefinition,
    WorkflowExecutionState,
    WorkflowStep,
    WorkflowTimelineEvent,
    is_allowed_step_type,
    is_valid_workflow_id,
    new_workflow_id,
    sanitize_workflow_value,
)


# ---------------------------------------------------------------------------
# 1. Constants + confinement
# ---------------------------------------------------------------------------

PRODUCTION_HERMES_HOME = "/Users/huangruibang/.hermes"
WORKFLOW_STORE_RELATIVE = "gateway/dev/workflow-store"

#: The repository source root — the workflow store must NEVER live under it.
_REPO_SOURCE_ROOT = Path(__file__).resolve().parents[1]

_ID_FILE_RE = re.compile(r"^[a-z]+_[0-9a-f]{12,64}$")
_MAX_DOCUMENT_BYTES = 256 * 1024  # 256 KiB hard cap per document
_MAX_TIMELINE_EVENTS = 1000
_MAX_LIST_LIMIT = 100

ERROR_HOME_UNSET = "workflow_home_unset"
ERROR_HOME_PRODUCTION = "workflow_home_production"
ERROR_HOME_REPO = "workflow_home_repo"
ERROR_PATH_OUTSIDE = "workflow_path_outside_hermes_home"
ERROR_WRITE_FAILED = "workflow_write_failed"
ERROR_CORRUPT_DOCUMENT = "workflow_corrupt_document"


@dataclass(frozen=True, slots=True)
class WorkflowStoreResult:
    """Outcome of a store read/write call."""

    ok: bool
    error_code: str | None
    error_message: str | None


def _resolve_home(hermes_home: str | os.PathLike[str] | None) -> tuple[Path, str | None]:
    if hermes_home is not None:
        home = Path(hermes_home).resolve()
    else:
        home_str = os.environ.get("HERMES_HOME", "")
        if not home_str:
            return Path(), ERROR_HOME_UNSET
        home = Path(home_str).resolve()
    if home == Path(PRODUCTION_HERMES_HOME).resolve():
        return Path(), ERROR_HOME_PRODUCTION
    if home == _REPO_SOURCE_ROOT.resolve():
        return Path(), ERROR_HOME_REPO
    return home, None


def get_workflow_store_root(
    hermes_home: str | os.PathLike[str] | None = None,
) -> Path:
    """Return the workflow store root (does not validate confinement)."""
    home, _err = _resolve_home(hermes_home)
    if str(home):
        return home / WORKFLOW_STORE_RELATIVE
    return Path(WORKFLOW_STORE_RELATIVE)


def validate_workflow_store_root(root: Path) -> str | None:
    """Return an error code if *root* is outside the dev home / forbidden."""
    try:
        resolved = Path(root).resolve()
    except (OSError, ValueError):
        return ERROR_PATH_OUTSIDE
    if resolved == Path(PRODUCTION_HERMES_HOME).resolve():
        return ERROR_HOME_PRODUCTION
    # Reject the repo source root outright.
    try:
        repo_root = _REPO_SOURCE_ROOT.resolve()
    except (OSError, ValueError):
        repo_root = _REPO_SOURCE_ROOT
    if resolved == repo_root or repo_root in resolved.parents:
        return ERROR_HOME_REPO
    return None


def ensure_workflow_store(
    hermes_home: str | os.PathLike[str] | None = None,
) -> tuple[Path, str | None]:
    """Ensure the workflow store dirs exist under the dev HERMES_HOME."""
    home, err = _resolve_home(hermes_home)
    if err is not None:
        return Path(), err
    root = home / WORKFLOW_STORE_RELATIVE
    confinement = validate_workflow_store_root(root)
    if confinement is not None:
        return Path(), confinement
    try:
        (root / "workflows").mkdir(parents=True, exist_ok=True)
        (root / "executions").mkdir(parents=True, exist_ok=True)
        (root / "timelines").mkdir(parents=True, exist_ok=True)
        (root / "meta").mkdir(parents=True, exist_ok=True)
    except OSError:
        return Path(), ERROR_WRITE_FAILED
    return root, None


# ---------------------------------------------------------------------------
# 2. Atomic write + advisory lock
# ---------------------------------------------------------------------------


class _FileLock:
    """A minimal advisory file lock (``fcntl`` on Unix, no-op fallback)."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._fd: int | None = None
        self._locked = False

    def __enter__(self) -> "_FileLock":
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._fd = os.open(self._path, os.O_RDWR | os.O_CREAT, 0o600)
        except OSError:
            self._fd = None
            return self
        try:
            import fcntl

            fcntl.flock(self._fd, fcntl.LOCK_EX)
            self._locked = True
        except (ImportError, OSError):
            # Non-Unix or unavailable — degrade to no-op (atomic replace still
            # guards the document; the lock only serializes concurrent appends).
            self._locked = False
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        if self._fd is not None:
            try:
                if self._locked:
                    import fcntl

                    fcntl.flock(self._fd, fcntl.LOCK_UN)
            except (ImportError, OSError):
                pass
            finally:
                os.close(self._fd)
                self._fd = None


def _atomic_write(path: Path, blob: str) -> None:
    """Write *blob* to *path* atomically (temp + os.replace)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        delete=False,
        prefix=f".{path.stem}.",
    ) as tmp:
        tmp.write(blob)
        tmp_path = Path(tmp.name)
    try:
        os.replace(tmp_path, path)
    except OSError:
        try:
            tmp_path.unlink()
        except OSError:
            pass
        raise


def _read_text_safe(path: Path) -> str | None:
    """Read a file as UTF-8 text. Returns ``None`` on any error."""
    try:
        if not path.exists() or path.is_symlink():
            return None
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def _serialize(document: Any) -> str | None:
    """Serialize a safe dict to a bounded JSON blob, or ``None`` on failure."""
    try:
        blob = json.dumps(document, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError):
        return None
    if len(blob.encode("utf-8")) > _MAX_DOCUMENT_BYTES:
        return None
    return blob


def _parse_document(blob: str | None) -> dict[str, Any] | None:
    """Parse a JSON document, returning ``None`` on corruption."""
    if not blob:
        return None
    try:
        data = json.loads(blob)
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    return data


# ---------------------------------------------------------------------------
# 3. Round-trip reconstructors (camelCase safe-dict → frozen dataclasses)
# ---------------------------------------------------------------------------


def _audit_link_from_dict(data: Mapping[str, Any]) -> WorkflowAuditLink:
    return WorkflowAuditLink(
        audit_id=str(data.get("auditId", "")),
        audit_kind=str(data.get("auditKind", "internal")),
        label=data.get("label"),
    )


def _step_from_dict(data: Mapping[str, Any]) -> WorkflowStep | None:
    try:
        step_type = str(data.get("stepType", ""))
        if not is_allowed_step_type(step_type):
            return None
        allowed_raw = data.get("allowedToolIds") or []
        allowed = tuple(str(t) for t in allowed_raw if isinstance(t, str))
        audit_links = tuple(
            _audit_link_from_dict(link)
            for link in (data.get("auditLinks") or [])
            if isinstance(link, Mapping)
        )
        return WorkflowStep(
            step_id=str(data.get("stepId", "")),
            step_type=step_type,
            title=str(data.get("title", "")),
            status=str(data.get("status", "planned")),
            description=data.get("description"),
            tool_id=data.get("toolId"),
            provider_mode=data.get("providerMode"),
            allowed_tool_ids=allowed,
            requires_approval=bool(data.get("requiresApproval", True)),
            requires_dry_run=bool(data.get("requiresDryRun", True)),
            requires_confirmation=bool(data.get("requiresConfirmation", False)),
            write_required=bool(data.get("writeRequired", False)),
            read_only=bool(data.get("readOnly", True)),
            local_side_effects=bool(data.get("localSideEffects", False)),
            external_side_effects=bool(data.get("externalSideEffects", False)),
            input=dict(data.get("input") or {}),
            safe_input_summary=dict(data.get("safeInputSummary") or {}),
            preview=dict(data.get("preview")) if isinstance(data.get("preview"), Mapping) else None,
            result=dict(data.get("result")) if isinstance(data.get("result"), Mapping) else None,
            audit_links=audit_links,
            blocked_reason=data.get("blockedReason"),
            approval_id=data.get("approvalId"),
            created_at=str(data.get("createdAt", "")),
            updated_at=str(data.get("updatedAt", "")),
        )
    except (TypeError, ValueError):
        return None


def _timeline_event_from_dict(data: Mapping[str, Any]) -> WorkflowTimelineEvent | None:
    try:
        audit_links = tuple(
            _audit_link_from_dict(link)
            for link in (data.get("auditLinks") or [])
            if isinstance(link, Mapping)
        )
        return WorkflowTimelineEvent(
            event_id=str(data.get("eventId", "")),
            event_type=str(data.get("eventType", "workflow_timeline_updated")),
            created_at=str(data.get("createdAt", "")),
            step_id=data.get("stepId"),
            step_type=data.get("stepType"),
            step_status=data.get("stepStatus"),
            approval_id=data.get("approvalId"),
            tool_id=data.get("toolId"),
            provider_mode=data.get("providerMode"),
            write_preview_id=data.get("writePreviewId"),
            rollback_id=data.get("rollbackId"),
            audit_links=audit_links,
            message=data.get("message"),
            blocked_reason=data.get("blockedReason"),
        )
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# 4. Workflow definition persistence
# ---------------------------------------------------------------------------


def save_workflow_definition(
    definition: WorkflowDefinition,
    *,
    hermes_home: str | os.PathLike[str] | None = None,
) -> WorkflowStoreResult:
    """Persist a workflow definition to the dev store."""
    root, err = ensure_workflow_store(hermes_home)
    if err is not None:
        return WorkflowStoreResult(False, err, _message(err))
    if not is_valid_workflow_id(definition.workflow_id, WORKFLOW_ID_PREFIX):
        return WorkflowStoreResult(False, ERROR_CORRUPT_DOCUMENT, "Invalid workflow id.")
    safe = sanitize_workflow_value(definition.to_safe_dict())
    if not isinstance(safe, dict):
        return WorkflowStoreResult(False, ERROR_CORRUPT_DOCUMENT, "Definition not serializable.")
    safe["schemaVersion"] = WORKFLOW_SCHEMA_VERSION
    blob = _serialize(safe)
    if blob is None:
        return WorkflowStoreResult(False, ERROR_WRITE_FAILED, "Definition too large.")
    path = root / "workflows" / f"{definition.workflow_id}.json"
    try:
        _atomic_write(path, blob)
    except OSError:
        return WorkflowStoreResult(False, ERROR_WRITE_FAILED, _message(ERROR_WRITE_FAILED))
    return WorkflowStoreResult(True, None, None)


def load_workflow_definition(
    workflow_id: str,
    *,
    hermes_home: str | os.PathLike[str] | None = None,
) -> WorkflowDefinition | None:
    """Load a workflow definition by id. Returns ``None`` if missing/corrupt."""
    if not is_valid_workflow_id(workflow_id, WORKFLOW_ID_PREFIX):
        return None
    root, err = ensure_workflow_store(hermes_home)
    if err is not None:
        return None
    path = root / "workflows" / f"{workflow_id}.json"
    data = _parse_document(_read_text_safe(path))
    if data is None:
        return None
    try:
        steps_raw = data.get("steps") or []
        steps = tuple(
            s for s in (_step_from_dict(item) for item in steps_raw if isinstance(item, Mapping))
            if s is not None
        )
        return WorkflowDefinition(
            workflow_id=str(data.get("workflowId", workflow_id)),
            schema_version=str(data.get("schemaVersion", WORKFLOW_SCHEMA_VERSION)),
            title=str(data.get("title", "")),
            description=data.get("description"),
            created_at=str(data.get("createdAt", "")),
            updated_at=str(data.get("updatedAt", "")),
            created_by=str(data.get("createdBy", "dev-webui")),
            phase=str(data.get("phase", "3A")),
            mode=str(data.get("mode", "dev_workflow_mvp")),
            steps=steps,
            safety_boundary=WORKFLOW_SAFETY_BOUNDARY,
            metadata=dict(data.get("metadata") or {}),
        )
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# 5. Execution state persistence
# ---------------------------------------------------------------------------


def save_workflow_execution(
    state: WorkflowExecutionState,
    *,
    hermes_home: str | os.PathLike[str] | None = None,
) -> WorkflowStoreResult:
    """Persist a workflow execution state to the dev store."""
    root, err = ensure_workflow_store(hermes_home)
    if err is not None:
        return WorkflowStoreResult(False, err, _message(err))
    if not is_valid_workflow_id(state.workflow_execution_id, WORKFLOW_EXECUTION_ID_PREFIX):
        return WorkflowStoreResult(False, ERROR_CORRUPT_DOCUMENT, "Invalid execution id.")
    safe = sanitize_workflow_value(state.to_safe_dict())
    if not isinstance(safe, dict):
        return WorkflowStoreResult(False, ERROR_CORRUPT_DOCUMENT, "State not serializable.")
    safe["schemaVersion"] = WORKFLOW_SCHEMA_VERSION
    blob = _serialize(safe)
    if blob is None:
        return WorkflowStoreResult(False, ERROR_WRITE_FAILED, "Execution state too large.")
    path = root / "executions" / f"{state.workflow_execution_id}.json"
    try:
        _atomic_write(path, blob)
    except OSError:
        return WorkflowStoreResult(False, ERROR_WRITE_FAILED, _message(ERROR_WRITE_FAILED))
    return WorkflowStoreResult(True, None, None)


def load_workflow_execution(
    execution_id: str,
    *,
    hermes_home: str | os.PathLike[str] | None = None,
) -> WorkflowExecutionState | None:
    """Load a workflow execution by id. Returns ``None`` if missing/corrupt."""
    if not is_valid_workflow_id(execution_id, WORKFLOW_EXECUTION_ID_PREFIX):
        return None
    root, err = ensure_workflow_store(hermes_home)
    if err is not None:
        return None
    path = root / "executions" / f"{execution_id}.json"
    data = _parse_document(_read_text_safe(path))
    if data is None:
        return None
    state = _execution_state_from_dict(data)
    if state is None:
        return None
    # Merge the timeline JSONL (authoritative append-only log) over the
    # snapshot timeline so the freshest events always win.
    timeline = _load_timeline(root, execution_id)
    if timeline:
        return WorkflowExecutionState(
            workflow_execution_id=state.workflow_execution_id,
            workflow_id=state.workflow_id,
            workflow_plan_id=state.workflow_plan_id,
            schema_version=state.schema_version,
            title=state.title,
            status=state.status,
            steps=state.steps,
            cursor_step_id=state.cursor_step_id,
            safety_boundary=state.safety_boundary,
            created_at=state.created_at,
            updated_at=state.updated_at,
            timeline=timeline,
            completed_step_count=state.completed_step_count,
            total_step_count=state.total_step_count,
        )
    return state


def _execution_state_from_dict(data: Mapping[str, Any]) -> WorkflowExecutionState | None:
    try:
        steps_raw = data.get("steps") or []
        steps = tuple(
            s for s in (_step_from_dict(item) for item in steps_raw if isinstance(item, Mapping))
            if s is not None
        )
        return WorkflowExecutionState(
            workflow_execution_id=str(data.get("workflowExecutionId", "")),
            workflow_id=str(data.get("workflowId", "")),
            workflow_plan_id=str(data.get("workflowPlanId", "")),
            schema_version=str(data.get("schemaVersion", WORKFLOW_SCHEMA_VERSION)),
            title=str(data.get("title", "")),
            status=str(data.get("status", "draft")),
            steps=steps,
            cursor_step_id=data.get("cursorStepId"),
            safety_boundary=WORKFLOW_SAFETY_BOUNDARY,
            created_at=str(data.get("createdAt", "")),
            updated_at=str(data.get("updatedAt", "")),
            completed_step_count=int(data.get("completedStepCount", 0) or 0),
            total_step_count=int(data.get("totalStepCount", len(steps)) or 0),
        )
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# 6. Timeline (append-only JSONL)
# ---------------------------------------------------------------------------


def append_workflow_timeline_event(
    execution_id: str,
    event: WorkflowTimelineEvent,
    *,
    hermes_home: str | os.PathLike[str] | None = None,
) -> WorkflowStoreResult:
    """Append one timeline event to the execution's append-only JSONL log."""
    if not is_valid_workflow_id(execution_id, WORKFLOW_EXECUTION_ID_PREFIX):
        return WorkflowStoreResult(False, ERROR_CORRUPT_DOCUMENT, "Invalid execution id.")
    root, err = ensure_workflow_store(hermes_home)
    if err is not None:
        return WorkflowStoreResult(False, err, _message(err))
    path = root / "timelines" / f"{execution_id}.jsonl"
    safe = sanitize_workflow_value(event.to_safe_dict())
    if not isinstance(safe, dict):
        return WorkflowStoreResult(False, ERROR_CORRUPT_DOCUMENT, "Event not serializable.")
    blob = _serialize(safe)
    if blob is None:
        return WorkflowStoreResult(False, ERROR_WRITE_FAILED, "Event too large.")
    line = blob + "\n"
    lock_path = root / "meta" / ".timelines.lock"
    try:
        with _FileLock(lock_path):
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(line)
    except OSError:
        return WorkflowStoreResult(False, ERROR_WRITE_FAILED, _message(ERROR_WRITE_FAILED))
    return WorkflowStoreResult(True, None, None)


def _load_timeline(root: Path, execution_id: str) -> tuple[WorkflowTimelineEvent, ...]:
    path = root / "timelines" / f"{execution_id}.jsonl"
    text = _read_text_safe(path)
    if not text:
        return ()
    events: list[WorkflowTimelineEvent] = []
    for line in text.splitlines():
        data = _parse_document(line)
        if data is None:
            continue
        event = _timeline_event_from_dict(data)
        if event is not None:
            events.append(event)
        if len(events) >= _MAX_TIMELINE_EVENTS:
            break
    return tuple(events)


# ---------------------------------------------------------------------------
# 7. Listing
# ---------------------------------------------------------------------------


def list_workflow_executions(
    *,
    limit: int = 50,
    hermes_home: str | os.PathLike[str] | None = None,
) -> list[dict[str, Any]]:
    """Return safe summaries of stored executions, newest-first."""
    root, _err = ensure_workflow_store(hermes_home)
    if _err is not None:
        return []
    bounded = max(1, min(int(limit), _MAX_LIST_LIMIT))
    exec_dir = root / "executions"
    try:
        entries = sorted(exec_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    except OSError:
        return []
    out: list[dict[str, Any]] = []
    for entry in entries:
        if len(out) >= bounded:
            break
        if not entry.is_file() or entry.is_symlink() or not entry.name.endswith(".json"):
            continue
        data = _parse_document(_read_text_safe(entry))
        if data is None:
            continue
        out.append(
            {
                "workflowExecutionId": data.get("workflowExecutionId", ""),
                "workflowId": data.get("workflowId", ""),
                "title": data.get("title", ""),
                "status": data.get("status", "draft"),
                "createdAt": data.get("createdAt", ""),
                "updatedAt": data.get("updatedAt", ""),
                "completedStepCount": data.get("completedStepCount", 0),
                "totalStepCount": data.get("totalStepCount", 0),
            }
        )
    return out


# ---------------------------------------------------------------------------
# 8. Errors + helpers
# ---------------------------------------------------------------------------


_ERROR_MESSAGES: dict[str, str] = {
    ERROR_HOME_UNSET: "HERMES_HOME is not set.",
    ERROR_HOME_PRODUCTION: "Workflow store may not use the production HERMES_HOME.",
    ERROR_HOME_REPO: "Workflow store may not live inside the repository.",
    ERROR_PATH_OUTSIDE: "Workflow store path is outside the dev HERMES_HOME.",
    ERROR_WRITE_FAILED: "Workflow store write failed.",
    ERROR_CORRUPT_DOCUMENT: "Workflow document is corrupt.",
}


def _message(code: str | None) -> str:
    if not code:
        return ""
    return _ERROR_MESSAGES.get(code, "Workflow store error.")


__all__ = [
    "WorkflowStoreResult",
    "get_workflow_store_root",
    "validate_workflow_store_root",
    "ensure_workflow_store",
    "save_workflow_definition",
    "load_workflow_definition",
    "save_workflow_execution",
    "load_workflow_execution",
    "append_workflow_timeline_event",
    "list_workflow_executions",
]
