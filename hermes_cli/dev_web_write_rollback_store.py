"""Phase 2C-H1 Rollback Manifest Store for the Hermes Dev WebUI.

A dev-only, file-backed store for the rollback manifests produced by the
Phase 2C controlled write chain. Each manifest is a JSON file under
``$HERMES_HOME/gateway/dev/tool-write-rollback-manifests/<rollbackId>.json``.

Rollback execution (Phase 2C-H1) loads a manifest by id, verifies the current
sandbox state matches the manifest's ``afterHash``, and either deletes the
created file or restores the previous content (carried internally as
``beforeContent`` — never exposed via API/audit).

Security:

  - ``rollbackId`` is validated (``wrbk_<hex>``, no slash / dot-dot / NUL) and
    used only as a filename inside the dev store dir — no path traversal.
  - The store is under the dev ``HERMES_HOME`` only; never the repo tree,
    ``~/.hermes``, production state dir, ``state.db``, or ``.claude/``.
  - Symlinked manifest files are refused.

Phase: 2C-H1 — Write Execution Hardening
Status: rollback manifest store implemented
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from hermes_cli.dev_web_write_rollback import (
    RESTORE_MODE_DELETE_CREATED_FILE,
    RESTORE_MODE_RESTORE_PREVIOUS_CONTENT,
    RollbackManifest,
)


PRODUCTION_HERMES_HOME = "/Users/huangruibang/.hermes"
ROLLBACK_DIR_RELATIVE = "gateway/dev/tool-write-rollback-manifests"

_ROLLBACK_ID_RE = re.compile(r"^wrbk_[0-9a-f]{12,64}$")
_MAX_LIST = 200
_MAX_BEFORE_CONTENT_BYTES = 256 * 1024  # matches the write file-size cap

ERROR_ROLLBACK_HOME_UNSET = "rollback_store_home_unset"
ERROR_ROLLBACK_HOME_PRODUCTION = "rollback_store_home_production"
ERROR_ROLLBACK_PATH_OUTSIDE = "rollback_store_path_outside_home"
ERROR_ROLLBACK_WRITE_FAILED = "rollback_store_write_failed"
ERROR_ROLLBACK_ID_INVALID = "rollback_store_id_invalid"


# ---------------------------------------------------------------------------
# 1. Path resolution
# ---------------------------------------------------------------------------


def _resolve_dir(
    hermes_home: str | os.PathLike[str] | None = None,
) -> tuple[Path, str | None]:
    if hermes_home is not None:
        home = Path(hermes_home).resolve()
    else:
        home_str = os.environ.get("HERMES_HOME", "")
        if not home_str:
            return Path(), ERROR_ROLLBACK_HOME_UNSET
        home = Path(home_str).resolve()
    if home == Path(PRODUCTION_HERMES_HOME).resolve():
        return Path(), ERROR_ROLLBACK_HOME_PRODUCTION
    rollback_dir = home / ROLLBACK_DIR_RELATIVE
    try:
        rollback_dir.resolve().relative_to(home)
    except ValueError:
        return Path(), ERROR_ROLLBACK_PATH_OUTSIDE
    return rollback_dir, None


def is_valid_rollback_id(rollback_id: str) -> bool:
    if not isinstance(rollback_id, str):
        return False
    # Reject any path-like characters — rollbackId is a bare filename stem.
    if "/" in rollback_id or "\\" in rollback_id or ".." in rollback_id or "\x00" in rollback_id:
        return False
    return bool(_ROLLBACK_ID_RE.match(rollback_id))


# ---------------------------------------------------------------------------
# 2. Save
# ---------------------------------------------------------------------------


def save_rollback_manifest(
    manifest: RollbackManifest | Mapping[str, Any],
    *,
    before_content: str | None,
    write_execution_id: str | None,
    write_plan_id: str | None,
    post_execution_audit_id: str | None,
    canonical_target_path: str | None = None,
    sandbox_root: str | None = None,
    hermes_home: str | os.PathLike[str] | None = None,
) -> str | None:
    """Persist a rollback manifest record. Returns the rollbackId, or None.

    ``before_content`` is stored internally (only when the target previously
    existed) so ``restore_previous_content`` rollback can restore it. It is
    never returned by the public load path's safe view or written to audit.
    """
    data = manifest.to_dict() if isinstance(manifest, RollbackManifest) else dict(manifest)
    rollback_id = str(data.get("rollbackId", ""))
    if not is_valid_rollback_id(rollback_id):
        return None

    record: dict[str, Any] = dict(data)
    record["writeExecutionId"] = write_execution_id
    record["writePlanId"] = write_plan_id
    record["postExecutionAuditId"] = post_execution_audit_id
    record["canonicalTargetPath"] = canonical_target_path
    record["sandboxRoot"] = sandbox_root
    record["executed"] = False
    record["executedAt"] = None
    record["executionId"] = None

    # Store the previous content only when needed for restore, bounded.
    before_exists = bool(data.get("beforeExists"))
    if before_exists and isinstance(before_content, str):
        if len(before_content.encode("utf-8")) <= _MAX_BEFORE_CONTENT_BYTES:
            record["beforeContent"] = before_content

    rollback_dir, err = _resolve_dir(hermes_home)
    if err is not None:
        return None
    manifest_file = rollback_dir / f"{rollback_id}.json"
    try:
        rollback_dir.mkdir(parents=True, exist_ok=True)
        blob = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
        fd = os.open(manifest_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            os.write(fd, blob.encode("utf-8"))
        finally:
            os.close(fd)
    except OSError:
        return None
    return rollback_id


# ---------------------------------------------------------------------------
# 3. Load
# ---------------------------------------------------------------------------


def load_rollback_manifest(
    rollback_id: str,
    *,
    hermes_home: str | os.PathLike[str] | None = None,
) -> dict[str, Any] | None:
    """Load a raw rollback manifest record (internal, includes beforeContent)."""
    if not is_valid_rollback_id(rollback_id):
        return None
    rollback_dir, err = _resolve_dir(hermes_home)
    if err is not None:
        return None
    manifest_file = rollback_dir / f"{rollback_id}.json"
    try:
        if not manifest_file.exists() or manifest_file.is_symlink():
            return None
        blob = manifest_file.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        data = json.loads(blob)
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict) or data.get("rollbackId") != rollback_id:
        return None
    return data


def list_rollback_manifests(
    *,
    limit: int = 50,
    hermes_home: str | os.PathLike[str] | None = None,
) -> list[dict[str, Any]]:
    """Return a bounded list of safe manifest summaries (no beforeContent)."""
    rollback_dir, err = _resolve_dir(hermes_home)
    if err is not None:
        return []
    out: list[dict[str, Any]] = []
    try:
        entries = sorted(rollback_dir.iterdir(), reverse=True)
    except OSError:
        return []
    n = max(1, min(int(limit), _MAX_LIST))
    for entry in entries:
        if len(out) >= n:
            break
        name = entry.name
        if not name.endswith(".json"):
            continue
        rid = name[: -len(".json")]
        if not is_valid_rollback_id(rid):
            continue
        data = load_rollback_manifest(rid, hermes_home=hermes_home)
        if data is None:
            continue
        out.append(_safe_summary(data))
    return out


def _safe_summary(data: Mapping[str, Any]) -> dict[str, Any]:
    """Public-safe summary — never includes beforeContent or canonical path."""
    keys = (
        "rollbackId", "operation", "targetRelativePath", "beforeExists",
        "beforeHash", "afterHash", "restoreMode", "createdAt",
        "writeExecutionId", "writePlanId", "postExecutionAuditId",
        "executed", "executedAt", "executionId",
    )
    return {k: data.get(k) for k in keys}


# ---------------------------------------------------------------------------
# 4. Mark executed
# ---------------------------------------------------------------------------


def mark_rollback_executed(
    rollback_id: str,
    *,
    execution_id: str,
    hermes_home: str | os.PathLike[str] | None = None,
) -> bool:
    if not is_valid_rollback_id(rollback_id):
        return False
    rollback_dir, err = _resolve_dir(hermes_home)
    if err is not None:
        return False
    manifest_file = rollback_dir / f"{rollback_id}.json"
    try:
        if not manifest_file.exists() or manifest_file.is_symlink():
            return False
        data = json.loads(manifest_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    if not isinstance(data, dict) or data.get("rollbackId") != rollback_id:
        return False
    if data.get("executed") is True:
        return True
    data["executed"] = True
    data["executedAt"] = datetime.now(timezone.utc).isoformat()
    data["executionId"] = execution_id
    import tempfile

    try:
        manifest_file.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=manifest_file.parent, delete=False,
            prefix=f".{rollback_id}.",
        ) as tmp:
            tmp.write(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
            tmp_path = Path(tmp.name)
        os.replace(tmp_path, manifest_file)
    except OSError:
        return False

    # Phase 2D: best-effort dual-write to the durable audit store.
    try:
        from hermes_cli.dev_web_audit_bridge import bridge_legacy_audit_to_store

        bridge_legacy_audit_to_store(
            {
                "rollbackId": rollback_id,
                "executionId": execution_id,
                "eventType": "rollback_executed",
                "status": "completed",
                "toolId": data.get("toolId"),
                "writePlanId": data.get("writePlanId"),
                "confirmationTokenId": data.get("confirmationTokenId"),
                "executedSteps": len(data.get("steps") or []),
            },
            audit_kind="rollback",
            hermes_home=hermes_home,
        )
    except Exception:
        pass
    return True


# ---------------------------------------------------------------------------
# 5. Validation + audit redaction
# ---------------------------------------------------------------------------


def validate_rollback_manifest_for_execution(data: Mapping[str, Any]) -> tuple[bool, tuple[str, ...]]:
    """Validate a loaded manifest record is fit for rollback execution."""
    errors: list[str] = []
    required = (
        "rollbackId", "operation", "targetRelativePath", "restoreMode",
        "afterHash", "createdAt",
    )
    for key in required:
        val = data.get(key)
        if not isinstance(val, str) or not val:
            errors.append(f"manifest missing required field: {key}")
            continue
    rid = data.get("rollbackId")
    if not (isinstance(rid, str) and is_valid_rollback_id(rid)):
        errors.append("manifest rollbackId is invalid")
    mode = data.get("restoreMode")
    if mode not in (RESTORE_MODE_DELETE_CREATED_FILE, RESTORE_MODE_RESTORE_PREVIOUS_CONTENT):
        errors.append(f"manifest has invalid restoreMode: {mode!r}")
    if mode == RESTORE_MODE_RESTORE_PREVIOUS_CONTENT:
        if not data.get("beforeHash"):
            errors.append("restore_previous_content manifest missing beforeHash")
        if data.get("beforeContent") is None:
            errors.append("restore_previous_content manifest missing beforeContent")
    if not isinstance(data.get("beforeExists"), bool):
        errors.append("manifest beforeExists must be boolean")
    # Tamper: integrity marker — executed flag must be a boolean.
    if "executed" in data and not isinstance(data.get("executed"), bool):
        errors.append("manifest executed flag is not boolean")
    return (len(errors) == 0, tuple(errors))


def redact_rollback_manifest_for_audit(data: Mapping[str, Any]) -> dict[str, Any]:
    """Redact a manifest for audit persistence. Drops beforeContent/canonical path."""
    safe = _safe_summary(data)
    safe["redactionApplied"] = True
    return safe
