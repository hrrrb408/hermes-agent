"""Phase 2C Dev Write Sandbox for the Hermes Dev WebUI.

This module owns the **dev sandbox root** — a directory under the dev
``HERMES_HOME`` (``$HERMES_HOME/gateway/dev/tool-write-sandbox``) — and all
path/IO safety for the Phase 2C controlled write tools.

Guarantees (hard, fail-closed):
  - The sandbox root is ALWAYS under the dev HERMES_HOME.
  - The sandbox root is NEVER ``~/.hermes`` / production state dir / repo root.
  - Writes happen ONLY inside the resolved sandbox root.
  - Path traversal, absolute paths, symlink escape, home references, and
    backslash escapes are rejected.
  - Forbidden targets (``.env``, ``.claude``, ``.git``, ``*.db``, ``*.sqlite*``,
    ``*.jsonl``, ``*.log``, ``test-results``, ``playwright-report``,
    ``node_modules``, ``dist``, ``build``) are rejected.
  - Only allow-listed text file types (``.txt/.md/.json/.yaml/.yml/.csv``) are
    accepted; binary content (NUL / high control-char ratio) is rejected.
  - Size limits are enforced (single write <= 64 KiB; file after write <= 256
    KiB; filename <= 120 chars; path depth <= 5).
  - stdlib only; no shell, no subprocess, no network, no database access.
  - The production home ``/Users/huangruibang/.hermes`` is always rejected.

Phase: 2C — Controlled Tool Write Execution (Dev Sandbox Write MVP)
Status: write sandbox implemented
"""

from __future__ import annotations

import difflib
import hashlib
import os
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# 1. Constants
# ---------------------------------------------------------------------------

ALLOWED_DEV_HERMES_HOME_PREFIX = "/Users/huangruibang/Code/hermes-home-dev"
PRODUCTION_HERMES_HOME = "/Users/huangruibang/.hermes"

SANDBOX_DIR_RELATIVE = "gateway/dev/tool-write-sandbox"

# Size / structure limits.
MAX_SINGLE_WRITE_BYTES = 64 * 1024  # 64 KiB payload
MAX_FILE_AFTER_WRITE_BYTES = 256 * 1024  # 256 KiB resulting file
MAX_FILENAME_LENGTH = 120
MAX_PATH_DEPTH = 5

# Allow-listed text file extensions (lowercase, including dot).
_ALLOWED_EXTENSIONS: frozenset[str] = frozenset(
    {".txt", ".md", ".json", ".yaml", ".yml", ".csv"}
)

# Forbidden path substrings (matched against the lowercased relative path).
# These never appear in a valid sandbox target.
_FORBIDDEN_PATH_SUBSTRINGS: tuple[str, ...] = (
    ".env",
    ".claude",
    ".git",
    ".db",
    ".sqlite",
    ".jsonl",
    ".log",
    "test-results",
    "playwright-report",
    "node_modules",
    "/dist/",
    "/build/",
    "state.db",
)

# Bounded diff preview.
_MAX_DIFF_BYTES = 8 * 1024
_MAX_DIFF_LINES = 200
_READBACK_SNIPPET_BYTES = 2 * 1024

# Error codes.
ERROR_DEV_HOME_UNSET = "write_dev_home_unset"
ERROR_DEV_HOME_PRODUCTION = "write_dev_home_production"
ERROR_PATH_TRAVERSAL = "blocked_write_path_traversal"
ERROR_ABSOLUTE_PATH = "blocked_write_absolute_path"
ERROR_SYMLINK_ESCAPE = "blocked_write_symlink_escape"
ERROR_FORBIDDEN_PATH = "blocked_write_forbidden_path"
ERROR_FILE_TYPE = "blocked_write_file_type"
ERROR_CONTENT_TOO_LARGE = "blocked_write_content_too_large"
ERROR_FILE_TOO_LARGE = "blocked_write_file_too_large"
ERROR_BINARY_CONTENT = "blocked_write_binary_content"
ERROR_FILENAME_TOO_LONG = "blocked_write_filename_too_long"
ERROR_PATH_TOO_DEEP = "blocked_write_path_too_deep"
ERROR_WRITE_FAILED = "blocked_write_io_failed"
ERROR_EMPTY_RELATIVE_PATH = "blocked_write_empty_path"


# ---------------------------------------------------------------------------
# 2. Dev-home resolution + sandbox root
# ---------------------------------------------------------------------------


def _resolve_hermes_home(hermes_home: str | os.PathLike[str] | None) -> tuple[Path, str | None]:
    """Resolve the dev HERMES_HOME. Returns (home, error_code).

    Fail-closed against the production home. Accepts any other non-empty home
    (the real dev home AND test tmp HERMES_HOME dirs). The dev-home *identity*
    is additionally enforced by the Dev WebUI server's environment guard.
    """
    if hermes_home is not None:
        home_raw = str(hermes_home)
    else:
        home_raw = os.environ.get("HERMES_HOME", "")
    if not home_raw or not home_raw.strip():
        return Path(), ERROR_DEV_HOME_UNSET
    home = Path(home_raw).expanduser().resolve()
    prod_home = Path(PRODUCTION_HERMES_HOME).resolve()
    if home == prod_home:
        return Path(), ERROR_DEV_HOME_PRODUCTION
    return home, None


def get_dev_write_sandbox_root(
    hermes_home: str | os.PathLike[str] | None = None,
) -> tuple[Path, str | None]:
    """Return ``(sandbox_root, error_code)``. Does NOT create the directory.

    The sandbox root is always ``home / gateway/dev/tool-write-sandbox``.
    """
    home, err = _resolve_hermes_home(hermes_home)
    if err is not None:
        return Path(), err
    sandbox_root = home / SANDBOX_DIR_RELATIVE
    return sandbox_root, None


def ensure_dev_write_sandbox_root(
    hermes_home: str | os.PathLike[str] | None = None,
) -> tuple[Path, str | None]:
    """Return ``(sandbox_root, error_code)``; create the dir if absent."""
    sandbox_root, err = get_dev_write_sandbox_root(hermes_home)
    if err is not None:
        return Path(), err
    try:
        sandbox_root.mkdir(parents=True, exist_ok=True)
    except OSError:
        return Path(), ERROR_WRITE_FAILED
    return sandbox_root, None


# ---------------------------------------------------------------------------
# 3. Target path validation
# ---------------------------------------------------------------------------


def _path_is_relative_safe(relative_path: str) -> str | None:
    """Return an error code if *relative_path* is unsafe, else ``None``."""
    if not isinstance(relative_path, str):
        return ERROR_EMPTY_RELATIVE_PATH
    candidate = relative_path.strip().replace("\\", "/")
    if not candidate:
        return ERROR_EMPTY_RELATIVE_PATH
    if candidate != relative_path.strip():
        return ERROR_PATH_TRAVERSAL
    if relative_path.startswith(("/", "~", "\\")):
        return ERROR_ABSOLUTE_PATH
    if "\x00" in relative_path:
        return ERROR_PATH_TRAVERSAL
    parts = [p for p in candidate.split("/") if p != ""]
    if any(part == ".." for part in parts):
        return ERROR_PATH_TRAVERSAL
    if any(part == "." for part in parts):
        return ERROR_PATH_TRAVERSAL
    if len(parts) == 0:
        return ERROR_EMPTY_RELATIVE_PATH
    if len(parts) > MAX_PATH_DEPTH:
        return ERROR_PATH_TOO_DEEP
    final_name = parts[-1]
    if len(final_name) > MAX_FILENAME_LENGTH:
        return ERROR_FILENAME_TOO_LONG
    # Reject embedded shell metacharacters.
    if any(ch in relative_path for ch in ("|", ";", "`", "$", ">", "<", "&", "\n", "\r")):
        return ERROR_PATH_TRAVERSAL
    return None


def _relative_path_string(relative_path: str) -> str:
    """Normalize a relative path to forward-slash form (no leading/trailing slash)."""
    candidate = relative_path.strip().replace("\\", "/")
    parts = [p for p in candidate.split("/") if p != ""]
    return "/".join(parts)


def canonicalize_sandbox_target_path(
    relative_path: str,
    hermes_home: str | os.PathLike[str] | None = None,
) -> tuple[Path, str | None]:
    """Return ``(canonical_path, error_code)`` for *relative_path*.

    Does NOT resolve symlinks yet (use :func:`validate_no_symlink_escape`).
    Returns the lexical path under the sandbox root.
    """
    sandbox_root, err = get_dev_write_sandbox_root(hermes_home)
    if err is not None:
        return Path(), err
    path_err = _path_is_relative_safe(relative_path)
    if path_err is not None:
        return Path(), path_err
    rel = _relative_path_string(relative_path)
    return sandbox_root / rel, None


def validate_no_symlink_escape(
    target_path: Path,
    sandbox_root: Path,
) -> tuple[bool, str | None]:
    """Verify *target_path* resolves to a location inside *sandbox_root*.

    Uses :meth:`Path.resolve` which follows symlinks. Any symlink that escapes
    the sandbox makes the resolved path fall outside ``sandbox_root`` and is
    rejected.
    """
    try:
        sandbox_resolved = Path(sandbox_root).resolve()
        target_resolved = Path(target_path).resolve()
    except OSError:
        return False, ERROR_SYMLINK_ESCAPE
    try:
        target_resolved.relative_to(sandbox_resolved)
    except ValueError:
        return False, ERROR_SYMLINK_ESCAPE
    if str(target_resolved) == str(sandbox_resolved):
        # The target must be a file inside the sandbox, not the sandbox root.
        return False, ERROR_FORBIDDEN_PATH
    return True, None


def validate_allowed_file_type(target_path: Path) -> tuple[bool, str | None]:
    """Verify the target has an allow-listed text extension and no forbidden name."""
    rel = target_path.name.lower()
    if not any(rel.endswith(ext) for ext in _ALLOWED_EXTENSIONS):
        return False, ERROR_FILE_TYPE
    # Forbidden substrings anywhere in the full path string (lowercased).
    full = str(target_path).lower()
    for forbidden in _FORBIDDEN_PATH_SUBSTRINGS:
        if forbidden in full:
            return False, ERROR_FORBIDDEN_PATH
    return True, None


def validate_file_size_limits(
    content: str,
    *,
    existing_size: int = 0,
    append: bool = False,
) -> tuple[bool, str | None]:
    """Verify content + resulting file fit the size limits."""
    if not isinstance(content, str):
        return False, ERROR_BINARY_CONTENT
    content_bytes = len(content.encode("utf-8"))
    if content_bytes > MAX_SINGLE_WRITE_BYTES:
        return False, ERROR_CONTENT_TOO_LARGE
    resulting = existing_size + content_bytes if append else content_bytes
    if resulting > MAX_FILE_AFTER_WRITE_BYTES:
        return False, ERROR_FILE_TOO_LARGE
    return True, None


def validate_sandbox_target_path(
    relative_path: str,
    hermes_home: str | os.PathLike[str] | None = None,
) -> tuple[bool, str | None, Path | None]:
    """Full target validation. Returns ``(ok, error_code, canonical_path)``."""
    canonical, cerr = canonicalize_sandbox_target_path(relative_path, hermes_home)
    if cerr is not None:
        return False, cerr, None
    # File type + forbidden-path check.
    type_ok, type_err = validate_allowed_file_type(canonical)
    if not type_ok:
        return False, type_err, None
    # Symlink escape check.
    sandbox_root, _ = get_dev_write_sandbox_root(hermes_home)
    esc_ok, esc_err = validate_no_symlink_escape(canonical, sandbox_root)
    if not esc_ok:
        return False, esc_err, None
    return True, None, canonical


# ---------------------------------------------------------------------------
# 4. Hashing + diff
# ---------------------------------------------------------------------------


def compute_sha256_text(content: str) -> str:
    """Return the SHA-256 hex digest of UTF-8 *content*."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def build_diff_preview(before: str | None, after: str | None) -> str:
    """Return a bounded unified-diff preview string."""
    before_lines = (before or "").splitlines(keepends=False)
    after_lines = (after or "").splitlines(keepends=False)
    diff_lines: list[str] = list(
        difflib.unified_diff(
            before_lines,
            after_lines,
            fromfile="before",
            tofile="after",
            lineterm="",
        )
    )
    bounded: list[str] = []
    total = 0
    for line in diff_lines:
        if len(bounded) >= _MAX_DIFF_LINES:
            bounded.append("... (diff truncated)")
            break
        if total + len(line) > _MAX_DIFF_BYTES:
            bounded.append("... (diff truncated)")
            break
        bounded.append(line)
        total += len(line)
    return "\n".join(bounded)


# ---------------------------------------------------------------------------
# 5. Safe IO primitives
# ---------------------------------------------------------------------------


def _looks_binary(content: str) -> bool:
    if "\x00" in content:
        return True
    sample = content[:1024]
    if not sample:
        return False
    return any(ord(ch) < 32 and ch not in "\n\r\t" for ch in sample)


def safe_read_text(target_path: Path) -> str | None:
    """Read a sandbox file as UTF-8 text. Returns ``None`` if missing/unreadable."""
    try:
        if not target_path.exists():
            return None
        return target_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _atomic_write(target_path: Path, content: str) -> str | None:
    """Write *content* atomically inside the sandbox. Returns error_code or None.

    Writes to a sibling temp file then ``os.replace`` into place. Both the temp
    and final paths are inside the sandbox (validated by the caller).
    """
    import secrets as _secrets

    parent = target_path.parent
    try:
        parent.mkdir(parents=True, exist_ok=True)
        tmp_name = f".{target_path.name}.{_secrets.token_hex(8)}.tmp"
        tmp_path = parent / tmp_name
        with tmp_path.open("w", encoding="utf-8") as fh:
            fh.write(content)
        os.replace(tmp_path, target_path)
        return None
    except OSError:
        return ERROR_WRITE_FAILED


def safe_write_text(
    target_path: Path,
    content: str,
) -> tuple[bool, str | None, str | None]:
    """Create-or-replace *target_path* with *content*.

    Returns ``(ok, error_code, before_content)``. ``before_content`` is the
    prior file content (or ``None`` if it did not exist) for rollback.
    """
    if not isinstance(content, str) or _looks_binary(content):
        return False, ERROR_BINARY_CONTENT, None
    before = safe_read_text(target_path)
    size_ok, size_err = validate_file_size_limits(content)
    if not size_ok:
        return False, size_err, before
    err = _atomic_write(target_path, content)
    if err is not None:
        return False, err, before
    return True, None, before


def safe_append_text(
    target_path: Path,
    content: str,
) -> tuple[bool, str | None, str | None]:
    """Append *content* to *target_path* (creating it if absent).

    Returns ``(ok, error_code, before_content)``.
    """
    if not isinstance(content, str) or _looks_binary(content):
        return False, ERROR_BINARY_CONTENT, None
    before = safe_read_text(target_path)
    existing_size = len(before.encode("utf-8")) if before is not None else 0
    size_ok, size_err = validate_file_size_limits(content, existing_size=existing_size, append=True)
    if not size_ok:
        return False, size_err, before
    merged = (before or "") + content
    err = _atomic_write(target_path, merged)
    if err is not None:
        return False, err, before
    return True, None, before


def safe_apply_patch(
    target_path: Path,
    search: str,
    replace: str,
) -> tuple[bool, str | None, str | None, int]:
    """Apply a single find-and-replace patch to *target_path*.

    ``search`` must occur exactly once. Returns
    ``(ok, error_code, before_content, match_count)``.
    """
    before = safe_read_text(target_path)
    if before is None:
        return False, ERROR_WRITE_FAILED, None, 0
    count = before.count(search)
    if count != 1:
        return False, ERROR_WRITE_FAILED, before, count
    after = before.replace(search, replace, 1)
    if _looks_binary(after):
        return False, ERROR_BINARY_CONTENT, before, count
    size_ok, size_err = validate_file_size_limits(after)
    if not size_ok:
        return False, size_err, before, count
    err = _atomic_write(target_path, after)
    if err is not None:
        return False, err, before, count
    return True, None, before, count


def readback_summary(target_path: Path) -> dict[str, Any]:
    """Return a bounded readback summary for a sandbox file."""
    exists = False
    size = 0
    content_hash: str | None = None
    snippet = ""
    try:
        if target_path.exists():
            content = target_path.read_text(encoding="utf-8")
            exists = True
            size = len(content.encode("utf-8"))
            content_hash = compute_sha256_text(content)
            if len(content) > _READBACK_SNIPPET_BYTES:
                snippet = content[:_READBACK_SNIPPET_BYTES] + "\n... (truncated)"
            else:
                snippet = content
    except (OSError, UnicodeDecodeError):
        exists = False
    return {
        "exists": exists,
        "sizeBytes": size,
        "contentHash": content_hash,
        "snippet": snippet,
    }
