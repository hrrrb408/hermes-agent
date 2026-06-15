"""Phase 2C-H1 File-backed Confirmation Token Store for the Hermes Dev WebUI.

A dev-only, file-backed store for single-use confirmation tokens used by the
controlled write and rollback execution chains. Each token is a JSON file
under ``$HERMES_HOME/gateway/dev/tool-confirmation-tokens/<tokenId>.json``.

Security model:

  - The client receives ``token = "<tokenId>.<secret>"`` where ``tokenId`` is
    public (``cft_<hex>``) and ``secret`` is a random URL-safe string.
  - The store file is named after the **public tokenId**, never the secret.
  - The store records ``tokenHash = sha256(secret + payloadDigest + scope +
    createdAt)`` — it NEVER stores the plain secret. Verification recomputes
    the hash from the submitted secret, proving the caller knows it without the
    server persisting it.
  - Every token carries a scope (``write_execute`` / ``rollback_execute`` /
    ``provider_write_preview_confirm``), a payload digest, an argument digest,
    a TTL, and a single-use flag. Used tokens are marked with ``usedAt``;
    replay is blocked across process restarts.
  - Cleanup deletes only expired token files; it never follows symlinks, never
    deletes non-token files, and never touches production paths.

Architecture constraints:
  - stdlib only; no shell, no subprocess, no database, no network.
  - never accesses ``~/.hermes`` or production ``state.db``.
  - never stores the plain secret, raw arguments, file content, API keys, or
    the full raw provider request.

Phase: 2C-H1 — Write Execution Hardening
Status: file-backed confirmation token store implemented
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


# ---------------------------------------------------------------------------
# 1. Constants
# ---------------------------------------------------------------------------

PRODUCTION_HERMES_HOME = "/Users/huangruibang/.hermes"
TOKEN_DIR_RELATIVE = "gateway/dev/tool-confirmation-tokens"

SCOPE_WRITE_EXECUTE = "write_execute"
SCOPE_ROLLBACK_EXECUTE = "rollback_execute"
SCOPE_PROVIDER_WRITE_PREVIEW_CONFIRM = "provider_write_preview_confirm"
SCOPE_WORKFLOW_STEP_APPROVAL = "workflow_step_approval"
VALID_SCOPES: frozenset[str] = frozenset(
    {
        SCOPE_WRITE_EXECUTE,
        SCOPE_ROLLBACK_EXECUTE,
        SCOPE_PROVIDER_WRITE_PREVIEW_CONFIRM,
        SCOPE_WORKFLOW_STEP_APPROVAL,
    }
)

DEFAULT_TTL_WRITE_SECONDS = 10 * 60  # 10 minutes
DEFAULT_TTL_ROLLBACK_SECONDS = 10 * 60  # 10 minutes
DEFAULT_TTL_PROVIDER_PREVIEW_SECONDS = 5 * 60  # 5 minutes
DEFAULT_TTL_WORKFLOW_APPROVAL_SECONDS = 5 * 60  # 5 minutes (Phase 3A)
MAX_TTL_SECONDS = 30 * 60  # 30 minutes hard cap

_TOKEN_ID_RE = re.compile(r"^cft_[0-9a-f]{12,64}$")
_MAX_PAYLOAD_BYTES = 64 * 1024
_MAX_TOKEN_FILES = 1000  # safety cap for list/cleanup

# Blocked reason codes.
BLOCKED_TOKEN_NOT_FOUND = "blocked_confirmation_token_not_found"
BLOCKED_TOKEN_INVALID = "blocked_confirmation_token_invalid"
BLOCKED_TOKEN_EXPIRED = "blocked_confirmation_token_expired"
BLOCKED_TOKEN_ALREADY_USED = "blocked_confirmation_token_already_used"
BLOCKED_TOKEN_SCOPE_MISMATCH = "blocked_confirmation_token_scope_mismatch"
BLOCKED_TOKEN_DIGEST_MISMATCH = "blocked_confirmation_token_digest_mismatch"

# Store error codes (internal).
ERROR_TOKEN_HOME_UNSET = "confirmation_home_unset"
ERROR_TOKEN_HOME_PRODUCTION = "confirmation_home_production"
ERROR_TOKEN_PATH_OUTSIDE = "confirmation_path_outside_hermes_home"
ERROR_TOKEN_WRITE_FAILED = "confirmation_write_failed"
ERROR_TOKEN_SERIALIZATION_FAILED = "confirmation_serialization_failed"

_REDACTED_VALUE = "[REDACTED]"
_SECRET_VALUE_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_\-]{8,}"),
    re.compile(r"Bearer\s+\S+", re.IGNORECASE),
    re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"),
)


# ---------------------------------------------------------------------------
# 2. Token record
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ConfirmationTokenRecord:
    tokenId: str
    tokenHash: str
    scope: str
    payloadDigest: str
    argumentDigest: str | None
    toolId: str | None
    operation: str | None
    createdAt: str
    expiresAt: str
    usedAt: str | None
    status: str  # "active" | "used"
    metadata: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class ConfirmationTokenIssue:
    token: str  # the full "<tokenId>.<secret>" handed to the client
    tokenId: str
    expiresAt: str
    scope: str


@dataclass(frozen=True, slots=True)
class ConfirmationTokenVerifyResult:
    verified: bool
    blocked_reason: str | None
    record: ConfirmationTokenRecord | None


# ---------------------------------------------------------------------------
# 3. Helpers
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().isoformat()


def _parse_iso(value: str) -> datetime | None:
    try:
        dt = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _resolve_token_dir(
    hermes_home: str | os.PathLike[str] | None = None,
) -> tuple[Path, str | None]:
    if hermes_home is not None:
        home = Path(hermes_home).resolve()
    else:
        home_str = os.environ.get("HERMES_HOME", "")
        if not home_str:
            return Path(), ERROR_TOKEN_HOME_UNSET
        home = Path(home_str).resolve()
    if home == Path(PRODUCTION_HERMES_HOME).resolve():
        return Path(), ERROR_TOKEN_HOME_PRODUCTION
    token_dir = home / TOKEN_DIR_RELATIVE
    try:
        token_dir.resolve().relative_to(home)
    except ValueError:
        return Path(), ERROR_TOKEN_PATH_OUTSIDE
    return token_dir, None


def _is_valid_token_id(token_id: str) -> bool:
    return isinstance(token_id, str) and bool(_TOKEN_ID_RE.match(token_id))


def _redact(value: str) -> str:
    out = value
    for pat in _SECRET_VALUE_PATTERNS:
        out = pat.sub(_REDACTED_VALUE, out)
    return out


def _canonical_payload_digest(payload: Mapping[str, Any]) -> str:
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _compute_token_hash(secret: str, payload_digest: str, scope: str, created_at: str) -> str:
    raw = f"{secret}|{payload_digest}|{scope}|{created_at}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _const_time_eq(a: str, b: str) -> bool:
    import hmac as _hmac

    return _hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


# ---------------------------------------------------------------------------
# 4. Create
# ---------------------------------------------------------------------------


def create_confirmation_token(
    payload: Mapping[str, Any],
    *,
    scope: str,
    argument_digest: str | None = None,
    tool_id: str | None = None,
    operation: str | None = None,
    ttl_seconds: int = DEFAULT_TTL_WRITE_SECONDS,
    metadata: Mapping[str, Any] | None = None,
    hermes_home: str | os.PathLike[str] | None = None,
) -> ConfirmationTokenIssue | None:
    """Create + persist a single-use confirmation token.

    Returns the issue descriptor (token, tokenId, expiresAt, scope), or
    ``None`` on store failure (fail-closed — callers block the operation).
    """
    if scope not in VALID_SCOPES:
        return None
    ttl = max(0, min(int(ttl_seconds), MAX_TTL_SECONDS))

    token_dir, err = _resolve_token_dir(hermes_home)
    if err is not None:
        return None

    payload_digest = _canonical_payload_digest(payload)
    token_id = f"cft_{secrets.token_hex(12)}"
    secret = secrets.token_urlsafe(24)
    created_at = _now_iso()
    try:
        expires_dt = _now() + _timedelta(seconds=ttl)
    except OverflowError:
        return None
    expires_at = expires_dt.isoformat()
    token_hash = _compute_token_hash(secret, payload_digest, scope, created_at)

    # Never persist the secret, raw arguments, or file content.
    safe_metadata: dict[str, Any] = {}
    if metadata:
        for key, value in metadata.items():
            if isinstance(value, str):
                safe_metadata[str(key)] = _redact(value)[:256]
            elif isinstance(value, (int, float, bool)):
                safe_metadata[str(key)] = value
    record = {
        "tokenId": token_id,
        "tokenHash": token_hash,
        "scope": scope,
        "payloadDigest": payload_digest,
        "argumentDigest": argument_digest,
        "toolId": tool_id,
        "operation": operation,
        "createdAt": created_at,
        "expiresAt": expires_at,
        "usedAt": None,
        "status": "active",
        "metadata": safe_metadata,
    }

    blob = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
    if len(blob.encode("utf-8")) > _MAX_PAYLOAD_BYTES:
        return None
    token_file = token_dir / f"{token_id}.json"
    try:
        token_dir.mkdir(parents=True, exist_ok=True)
        # O_EXCL create — refuse to clobber an existing token file.
        fd = os.open(token_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            os.write(fd, blob.encode("utf-8"))
        finally:
            os.close(fd)
    except OSError:
        return None

    return ConfirmationTokenIssue(
        token=f"{token_id}.{secret}",
        tokenId=token_id,
        expiresAt=expires_at,
        scope=scope,
    )


def _timedelta(*, seconds: int):
    from datetime import timedelta as _td

    return _td(seconds=seconds)


# ---------------------------------------------------------------------------
# 5. Load
# ---------------------------------------------------------------------------


def load_confirmation_token(
    token_id: str,
    *,
    hermes_home: str | os.PathLike[str] | None = None,
) -> ConfirmationTokenRecord | None:
    if not _is_valid_token_id(token_id):
        return None
    token_dir, err = _resolve_token_dir(hermes_home)
    if err is not None:
        return None
    token_file = token_dir / f"{token_id}.json"
    try:
        if not token_file.exists():
            return None
        # Refuse to follow a symlinked token file (defense-in-depth).
        if token_file.is_symlink():
            return None
        blob = token_file.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        data = json.loads(blob)
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    # Tamper check: the stored tokenId must match the filename/id.
    if data.get("tokenId") != token_id:
        return None
    try:
        return ConfirmationTokenRecord(
            tokenId=str(data["tokenId"]),
            tokenHash=str(data["tokenHash"]),
            scope=str(data["scope"]),
            payloadDigest=str(data["payloadDigest"]),
            argumentDigest=data.get("argumentDigest"),
            toolId=data.get("toolId"),
            operation=data.get("operation"),
            createdAt=str(data["createdAt"]),
            expiresAt=str(data["expiresAt"]),
            usedAt=data.get("usedAt"),
            status=str(data.get("status", "active")),
            metadata=data.get("metadata") or {},
        )
    except (KeyError, TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# 6. Verify
# ---------------------------------------------------------------------------


def verify_confirmation_token(
    token: str | None,
    *,
    expected_scope: str,
    expected_digest: str | None,
    hermes_home: str | os.PathLike[str] | None = None,
) -> ConfirmationTokenVerifyResult:
    """Verify a confirmation token against an expected scope + digest.

    Returns a result with ``verified`` and a precise ``blocked_reason``. Does
    NOT consume the token — call :func:`mark_confirmation_token_used` after a
    successful operation.
    """
    if not isinstance(token, str) or not token:
        return ConfirmationTokenVerifyResult(False, BLOCKED_TOKEN_INVALID, None)
    if "." not in token:
        return ConfirmationTokenVerifyResult(False, BLOCKED_TOKEN_INVALID, None)
    token_id, _, secret = token.rpartition(".")
    if not _is_valid_token_id(token_id) or not secret:
        return ConfirmationTokenVerifyResult(False, BLOCKED_TOKEN_INVALID, None)

    record = load_confirmation_token(token_id, hermes_home=hermes_home)
    if record is None:
        return ConfirmationTokenVerifyResult(False, BLOCKED_TOKEN_NOT_FOUND, None)

    # Authenticity: recompute the hash from the submitted secret.
    recomputed = _compute_token_hash(secret, record.payloadDigest, record.scope, record.createdAt)
    if not _const_time_eq(recomputed, record.tokenHash):
        return ConfirmationTokenVerifyResult(False, BLOCKED_TOKEN_INVALID, None)

    # Tamper: stored scope/digest must match the record's own hash inputs.
    if record.scope != expected_scope:
        return ConfirmationTokenVerifyResult(False, BLOCKED_TOKEN_SCOPE_MISMATCH, record)

    expires_dt = _parse_iso(record.expiresAt)
    if expires_dt is not None and _now() > expires_dt:
        return ConfirmationTokenVerifyResult(False, BLOCKED_TOKEN_EXPIRED, record)

    if record.status == "used" or record.usedAt is not None:
        return ConfirmationTokenVerifyResult(False, BLOCKED_TOKEN_ALREADY_USED, record)

    if expected_digest is not None and record.argumentDigest is not None:
        if not _const_time_eq(record.argumentDigest, expected_digest):
            return ConfirmationTokenVerifyResult(False, BLOCKED_TOKEN_DIGEST_MISMATCH, record)

    return ConfirmationTokenVerifyResult(True, None, record)


# ---------------------------------------------------------------------------
# 7. Mark used (single-use persistence)
# ---------------------------------------------------------------------------


def mark_confirmation_token_used(
    token_id: str,
    *,
    hermes_home: str | os.PathLike[str] | None = None,
) -> bool:
    if not _is_valid_token_id(token_id):
        return False
    token_dir, err = _resolve_token_dir(hermes_home)
    if err is not None:
        return False
    token_file = token_dir / f"{token_id}.json"
    try:
        if not token_file.exists() or token_file.is_symlink():
            return False
        blob = token_file.read_text(encoding="utf-8")
        data = json.loads(blob)
    except (OSError, ValueError):
        return False
    if not isinstance(data, dict) or data.get("tokenId") != token_id:
        return False
    if data.get("status") == "used":
        return True
    data["status"] = "used"
    data["usedAt"] = _now_iso()
    # Atomic rewrite via temp + replace inside the token dir.
    import tempfile

    try:
        token_file.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=token_file.parent, delete=False, prefix=f".{token_id}."
        ) as tmp:
            tmp.write(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
            tmp_path = Path(tmp.name)
        os.replace(tmp_path, token_file)
    except OSError:
        return False

    # Phase 2D: best-effort dual-write to the durable audit store.
    try:
        from hermes_cli.dev_web_audit_bridge import bridge_legacy_audit_to_store

        bridge_legacy_audit_to_store(
            {
                "tokenId": token_id,
                "eventType": "confirmation_token_used",
                "status": "used",
                "used": True,
                "toolId": data.get("toolId"),
                "writePlanId": data.get("writePlanId"),
            },
            audit_kind="confirmation",
            hermes_home=hermes_home,
        )
    except Exception:
        pass
    return True


# ---------------------------------------------------------------------------
# 8. Cleanup expired tokens
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ConfirmationTokenCleanupResult:
    removed: int
    skipped: int
    error: str | None


def cleanup_expired_confirmation_tokens(
    *,
    now: datetime | None = None,
    hermes_home: str | os.PathLike[str] | None = None,
) -> ConfirmationTokenCleanupResult:
    """Delete expired token files. Safe: no symlink follow, no non-token files."""
    now_dt = now or _now()
    token_dir, err = _resolve_token_dir(hermes_home)
    if err is not None:
        return ConfirmationTokenCleanupResult(0, 0, err)
    removed = 0
    skipped = 0
    try:
        entries = list(token_dir.iterdir())
    except OSError:
        return ConfirmationTokenCleanupResult(0, 0, None)
    for entry in entries[:_MAX_TOKEN_FILES]:
        name = entry.name
        # Only delete files matching the token-id naming convention.
        if not name.endswith(".json"):
            skipped += 1
            continue
        token_id = name[: -len(".json")]
        if not _is_valid_token_id(token_id):
            skipped += 1
            continue
        try:
            if entry.is_symlink() or not entry.is_file():
                skipped += 1
                continue
            blob = entry.read_text(encoding="utf-8")
            data = json.loads(blob)
        except (OSError, ValueError):
            skipped += 1
            continue
        if not isinstance(data, dict) or data.get("tokenId") != token_id:
            skipped += 1
            continue
        expires_dt = _parse_iso(str(data.get("expiresAt", "")))
        if expires_dt is None:
            skipped += 1
            continue
        if now_dt > expires_dt:
            try:
                entry.unlink()
                removed += 1
            except OSError:
                skipped += 1
        else:
            skipped += 1
    return ConfirmationTokenCleanupResult(removed=removed, skipped=skipped, error=None)


# ---------------------------------------------------------------------------
# 9. Audit redaction
# ---------------------------------------------------------------------------


def redact_confirmation_token_for_audit(record: ConfirmationTokenRecord | Mapping[str, Any]) -> dict[str, Any]:
    """Return a safe, redacted view of a token record for audit persistence.

    Never includes the secret, the full tokenHash is shortened to a prefix,
    and any secret value patterns are stripped.
    """
    if isinstance(record, ConfirmationTokenRecord):
        data = {
            "tokenId": record.tokenId,
            "scope": record.scope,
            "payloadDigest": record.payloadDigest,
            "argumentDigest": record.argumentDigest,
            "toolId": record.toolId,
            "operation": record.operation,
            "createdAt": record.createdAt,
            "expiresAt": record.expiresAt,
            "usedAt": record.usedAt,
            "status": record.status,
        }
    else:
        data = dict(record)
    safe: dict[str, Any] = {}
    for key, value in data.items():
        if key in ("tokenHash", "secret", "tokenSecret", "plainToken"):
            # Never expose the hash/secret wholesale; keep only a short prefix.
            if isinstance(value, str) and value:
                safe[key + "Prefix"] = _redact(value[:12])
            continue
        if isinstance(value, str):
            safe[key] = _redact(value)
        else:
            safe[key] = value
    safe["redactionApplied"] = True
    return safe
