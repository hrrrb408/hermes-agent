"""Durable Dev Audit Store Writer for the Hermes Dev WebUI (Phase 2D).

A dev-only append-only JSONL audit store living under the dev ``HERMES_HOME``.
This is the canonical durable sink for every audit event produced by the Dev
WebUI (dry-run, pre/post execution, provider, write, rollback, confirmation).

Layout (all under ``$HERMES_HOME/gateway/dev/audit-store``)::

    events/
      audit-000001.jsonl   # monotonically numbered segments
      audit-000002.jsonl
    indexes/               # built by dev_web_audit_index
    quarantine/            # corrupt records, moved by dev_web_audit_recovery
    meta/
      store-meta.json      # authoritative sequence counter + store status
      rotation-state.json  # active segment + rotation bookkeeping

Hard guarantees:
  - append-only: events are only ever appended, never rewritten in place
  - one canonical JSON-native event per line
  - monotonic, non-negative, gap-free ``sequence``
  - unique ``eventId`` (duplicate appends are rejected, not silently dropped)
  - safe flush (``flush`` + best-effort ``fsync``) on every append
  - cross-process file lock via ``fcntl.flock`` (stdlib only); an in-process
    threading lock backs it when ``fcntl`` is unavailable
  - the store root is always under the dev ``HERMES_HOME`` and is never under
    the repository, ``~/.hermes``, or any production state location

Phase: 2D — Durable Dev Audit Store MVP
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from hermes_cli.dev_web_audit_schema import (
    AUDIT_SCHEMA_VERSION,
    MAX_EVENT_BYTES,
    validate_canonical_event,
)
from hermes_cli.dev_web_audit_sanitizer import sanitize_audit_event

# ---------------------------------------------------------------------------
# 1. Constants
# ---------------------------------------------------------------------------

_AUDIT_STORE_RELATIVE = "gateway/dev/audit-store"
_EVENTS_SUBDIR = "events"
_INDEXES_SUBDIR = "indexes"
_QUARANTINE_SUBDIR = "quarantine"
_META_SUBDIR = "meta"

_STORE_META_FILENAME = "store-meta.json"
_ROTATION_STATE_FILENAME = "rotation-state.json"

_SEGMENT_PREFIX = "audit-"
_SEGMENT_SUFFIX = ".jsonl"
_SEGMENT_NUMBER_WIDTH = 6  # audit-000001.jsonl

#: First segment number when the store is initialized.
_FIRST_SEGMENT_NUMBER = 1

# Forbidden production locations.
_PRODUCTION_HERMES_HOME = "/Users/huangruibang/.hermes"
_REPO_SOURCE_ROOT = "/Users/huangruibang/Code/hermes-agent-dev"

# Error codes.
ERROR_HERMES_HOME_MISSING = "audit_store_hermes_home_missing"
ERROR_STORE_ROOT_FORBIDDEN = "audit_store_root_forbidden"
ERROR_EVENT_INVALID = "audit_store_event_invalid"
ERROR_EVENT_TOO_LARGE = "audit_store_event_too_large"
ERROR_DUPLICATE_EVENT_ID = "audit_store_duplicate_event_id"
ERROR_WRITE_FAILED = "audit_store_write_failed"

# ---------------------------------------------------------------------------
# 2. Process-wide write lock
# ---------------------------------------------------------------------------

#: In-process serialization for appends. ``fcntl.flock`` serializes across
#: processes; this serializes threads within this process.
_WRITE_LOCK = threading.RLock()

#: Best-effort cross-process lock availability flag.
try:  # pragma: no cover - platform dependent
    import fcntl as _fcntl  # type: ignore[import-not-found]
    _HAS_FCNTL = True
except ImportError:  # pragma: no cover - non-POSIX
    _HAS_FCNTL = False


# ---------------------------------------------------------------------------
# 3. Result dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AuditStoreWriteResult:
    """Immutable result of an append attempt."""

    written: bool
    event_id: str | None
    sequence: int | None
    segment: str | None
    rotated: bool
    error_code: str | None
    error_message: str | None


@dataclass(frozen=True, slots=True)
class AuditStoreMeta:
    """Snapshot of the store metadata (no secrets, no absolute paths)."""

    schema_version: str
    last_sequence: int
    last_event_id: str | None
    event_count: int
    active_segment: str
    segment_count: int
    initialized: bool
    quarantined_count: int = 0
    extra: dict[str, Any] = field(default_factory=dict)

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": self.schema_version,
            "lastSequence": self.last_sequence,
            "lastEventId": self.last_event_id,
            "eventCount": self.event_count,
            "activeSegment": self.active_segment,
            "segmentCount": self.segment_count,
            "initialized": self.initialized,
            "quarantinedCount": self.quarantined_count,
        }


# ---------------------------------------------------------------------------
# 4. Path resolution and validation
# ---------------------------------------------------------------------------


def _is_relative_to(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def _resolve_hermes_home(
    hermes_home: str | os.PathLike[str] | None,
) -> tuple[Path, str | None]:
    """Resolve and validate HERMES_HOME. Returns ``(home, error_or_none)``."""
    if hermes_home is not None:
        home = Path(hermes_home).resolve()
    else:
        home_str = os.environ.get("HERMES_HOME", "")
        if not home_str:
            return Path(), ERROR_HERMES_HOME_MISSING
        home = Path(home_str).resolve()

    prod_home = Path(_PRODUCTION_HERMES_HOME).resolve()
    repo_root = Path(_REPO_SOURCE_ROOT).resolve()

    # Block exact production home, production subtree, and the repository.
    if home == prod_home or _is_relative_to(home, prod_home):
        return Path(), ERROR_STORE_ROOT_FORBIDDEN
    if home == repo_root or _is_relative_to(home, repo_root):
        return Path(), ERROR_STORE_ROOT_FORBIDDEN
    return home, None


def get_audit_store_root(
    hermes_home: str | os.PathLike[str] | None = None,
) -> tuple[Path, str | None]:
    """Resolve the audit-store root under the dev HERMES_HOME.

    Returns ``(root_path, error_or_none)``. Validates containment against the
    production home and the repository. Does not create any directories.
    """
    home, err = _resolve_hermes_home(hermes_home)
    if err is not None:
        return Path(), err
    root = (home / _AUDIT_STORE_RELATIVE).resolve()

    prod_home = Path(_PRODUCTION_HERMES_HOME).resolve()
    repo_root = Path(_REPO_SOURCE_ROOT).resolve()

    if not _is_relative_to(root, home):
        return Path(), ERROR_STORE_ROOT_FORBIDDEN
    if root == prod_home or _is_relative_to(root, prod_home):
        return Path(), ERROR_STORE_ROOT_FORBIDDEN
    if root == repo_root or _is_relative_to(root, repo_root):
        return Path(), ERROR_STORE_ROOT_FORBIDDEN
    if root.name == "state.db" or str(root).endswith("state.db"):
        return Path(), ERROR_STORE_ROOT_FORBIDDEN
    return root, None


def validate_audit_store_root(root: Path) -> str | None:
    """Validate an already-resolved audit-store root.

    Returns an error code string if invalid, else ``None``.
    """
    if not isinstance(root, Path):
        return ERROR_STORE_ROOT_FORBIDDEN
    resolved = root.resolve()
    prod_home = Path(_PRODUCTION_HERMES_HOME).resolve()
    repo_root = Path(_REPO_SOURCE_ROOT).resolve()
    if resolved == prod_home or _is_relative_to(resolved, prod_home):
        return ERROR_STORE_ROOT_FORBIDDEN
    if resolved == repo_root or _is_relative_to(resolved, repo_root):
        return ERROR_STORE_ROOT_FORBIDDEN
    if not resolved.name or resolved.name == "state.db":
        return ERROR_STORE_ROOT_FORBIDDEN
    return None


def ensure_audit_store(
    hermes_home: str | os.PathLike[str] | None = None,
) -> tuple[Path, str | None]:
    """Ensure the audit-store directory tree exists under dev HERMES_HOME.

    Creates ``events/``, ``indexes/``, ``quarantine/``, ``meta/`` and stamps
    the initial ``store-meta.json`` if missing. Idempotent. Returns
    ``(root_path, error_or_none)``.
    """
    root, err = get_audit_store_root(hermes_home)
    if err is not None:
        return Path(), err

    try:
        for sub in (_EVENTS_SUBDIR, _INDEXES_SUBDIR, _QUARANTINE_SUBDIR, _META_SUBDIR):
            (root / sub).mkdir(parents=True, exist_ok=True)
        _ensure_store_meta(root)
        _ensure_rotation_state(root)
    except OSError:
        return Path(), ERROR_WRITE_FAILED
    return root, None


def _events_dir(root: Path) -> Path:
    return root / _EVENTS_SUBDIR


def _meta_path(root: Path) -> Path:
    return root / _META_SUBDIR / _STORE_META_FILENAME


def _rotation_state_path(root: Path) -> Path:
    return root / _META_SUBDIR / _ROTATION_STATE_FILENAME


def _segment_path(root: Path, number: int) -> Path:
    return _events_dir(root) / f"{_SEGMENT_PREFIX}{number:0{_SEGMENT_NUMBER_WIDTH}d}{_SEGMENT_SUFFIX}"


def _segment_name(number: int) -> str:
    return f"{_SEGMENT_PREFIX}{number:0{_SEGMENT_NUMBER_WIDTH}d}{_SEGMENT_SUFFIX}"


def parse_segment_number(name: str) -> int | None:
    """Parse a segment filename into its integer number, or ``None``."""
    if not name.startswith(_SEGMENT_PREFIX) or not name.endswith(_SEGMENT_SUFFIX):
        return None
    core = name[len(_SEGMENT_PREFIX) : -len(_SEGMENT_SUFFIX)]
    try:
        return int(core)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# 5. Store metadata (sequence counter)
# ---------------------------------------------------------------------------


def _read_store_meta(root: Path) -> dict[str, Any]:
    path = _meta_path(root)
    if not path.is_file():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except (OSError, ValueError):
        pass
    return {}


def _write_store_meta(root: Path, meta: dict[str, Any]) -> None:
    path = _meta_path(root)
    payload = json.dumps(meta, ensure_ascii=False, sort_keys=True)
    # Unique tmp name per call so concurrent writers do not collide.
    tmp = path.with_name(
        f".{path.name}.{os.getpid()}.{uuid.uuid4().hex[:8]}.tmp"
    )
    with tmp.open("w", encoding="utf-8") as f:
        f.write(payload)
        f.flush()
        try:
            os.fsync(f.fileno())
        except OSError:
            pass
    tmp.replace(path)


def _ensure_store_meta(root: Path) -> None:
    meta = _read_store_meta(root)
    meta.setdefault("schemaVersion", AUDIT_SCHEMA_VERSION)
    meta.setdefault("lastSequence", 0)
    meta.setdefault("lastEventId", None)
    meta.setdefault("eventCount", 0)
    meta.setdefault("activeSegment", _segment_name(_FIRST_SEGMENT_NUMBER))
    meta.setdefault("initialized", True)
    _write_store_meta(root, meta)


def _ensure_rotation_state(root: Path) -> None:
    path = _rotation_state_path(root)
    if path.is_file():
        return
    state = {
        "activeSegment": _segment_name(_FIRST_SEGMENT_NUMBER),
        "segmentCount": 1,
        "rotatedCount": 0,
    }
    payload = json.dumps(state, ensure_ascii=False, sort_keys=True)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            f.write(payload)
    except OSError:
        pass


def get_audit_store_meta(
    hermes_home: str | os.PathLike[str] | None = None,
) -> tuple[AuditStoreMeta | None, str | None]:
    """Return a safe snapshot of the store metadata.

    Does not mutate anything. Returns ``(meta, error_or_none)``.
    """
    root, err = get_audit_store_root(hermes_home)
    if err is not None:
        return None, err
    if not root.is_dir():
        return (
            AuditStoreMeta(
                schema_version=AUDIT_SCHEMA_VERSION,
                last_sequence=0,
                last_event_id=None,
                event_count=0,
                active_segment=_segment_name(_FIRST_SEGMENT_NUMBER),
                segment_count=0,
                initialized=False,
            ),
            None,
        )
    raw = _read_store_meta(root)
    segments = list_audit_segment_numbers(root)
    quarantined = _count_quarantined(root)
    return (
        AuditStoreMeta(
            schema_version=raw.get("schemaVersion", AUDIT_SCHEMA_VERSION),
            last_sequence=int(raw.get("lastSequence", 0) or 0),
            last_event_id=raw.get("lastEventId"),
            event_count=int(raw.get("eventCount", 0) or 0),
            active_segment=raw.get(
                "activeSegment", _segment_name(_FIRST_SEGMENT_NUMBER)
            ),
            segment_count=len(segments),
            initialized=bool(raw.get("initialized", False)),
            quarantined_count=quarantined,
        ),
        None,
    )


def _count_quarantined(root: Path) -> int:
    qdir = root / _QUARANTINE_SUBDIR
    if not qdir.is_dir():
        return 0
    try:
        return sum(1 for _ in qdir.iterdir() if _.is_file())
    except OSError:
        return 0


# ---------------------------------------------------------------------------
# 6. Segment listing
# ---------------------------------------------------------------------------


def list_audit_segments(root: Path) -> list[Path]:
    """List event segment files in ascending segment-number order."""
    edir = _events_dir(root)
    if not edir.is_dir():
        return []
    found: list[tuple[int, Path]] = []
    try:
        for entry in edir.iterdir():
            if not entry.is_file():
                continue
            num = parse_segment_number(entry.name)
            if num is not None:
                found.append((num, entry))
    except OSError:
        return []
    found.sort(key=lambda pair: pair[0])
    return [path for _, path in found]


def list_audit_segment_numbers(root: Path) -> list[int]:
    """List segment numbers in ascending order."""
    return [parse_segment_number(p.name) or 0 for p in list_audit_segments(root)]


def get_active_audit_segment_path(root: Path) -> Path:
    """Return the path of the currently active segment.

    Falls back to the highest-numbered existing segment, or the first segment
    if none exist yet.
    """
    meta = _read_store_meta(root)
    active_name = meta.get("activeSegment")
    if isinstance(active_name, str):
        candidate = _events_dir(root) / active_name
        if parse_segment_number(active_name) is not None:
            return candidate
    segments = list_audit_segments(root)
    if segments:
        return segments[-1]
    return _segment_path(root, _FIRST_SEGMENT_NUMBER)


# ---------------------------------------------------------------------------
# 7. Cross-process file lock
# ---------------------------------------------------------------------------


class _FileLock:
    """Best-effort cross-process advisory lock using ``fcntl.flock``.

    Falls back to a no-op (in-process lock still applies) on platforms without
    ``fcntl``. The lock file lives next to the store meta under the dev home.
    """

    def __init__(self, lock_path: Path) -> None:
        self._lock_path = lock_path
        self._fh: Any = None

    def __enter__(self) -> "_FileLock":
        if not _HAS_FCNTL:
            return self
        try:
            self._lock_path.parent.mkdir(parents=True, exist_ok=True)
            self._fh = open(self._lock_path, "a+", encoding="utf-8")
            _fcntl.flock(self._fh.fileno(), _fcntl.LOCK_EX)
        except OSError:
            # If we cannot acquire the OS lock, fall back to the in-process
            # lock only. The store remains safe within this process.
            self._fh = None
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self._fh is None:
            return
        try:
            _fcntl.flock(self._fh.fileno(), _fcntl.LOCK_UN)
        except OSError:
            pass
        finally:
            try:
                self._fh.close()
            except OSError:
                pass
            self._fh = None


def _store_lock_path(root: Path) -> Path:
    return root / _META_SUBDIR / "store.lock"


# ---------------------------------------------------------------------------
# 8. Low-level segment iteration (used by index / query / recovery)
# ---------------------------------------------------------------------------


def iter_segment_lines(segment: Path) -> Iterator[tuple[int, str]]:
    """Yield ``(line_number, raw_line)`` for a segment, 1-based line numbers."""
    if not segment.is_file():
        return
    try:
        with segment.open("r", encoding="utf-8") as f:
            for idx, raw in enumerate(f, start=1):
                yield idx, raw
    except OSError:
        return


def iter_all_events(
    root: Path,
    *,
    include_corrupt: bool = False,
) -> Iterator[tuple[Path, int, dict[str, Any] | None, str]]:
    """Iterate every line across every segment.

    Yields ``(segment, line_number, parsed_event_or_None, raw_line)``.
    ``parsed_event`` is ``None`` when the line is corrupt (invalid JSON or not
    a dict); the raw line is always yielded so callers (recovery) can
    quarantine it. When ``include_corrupt`` is ``False`` corrupt lines are
    skipped silently.
    """
    for segment in list_audit_segments(root):
        for line_no, raw in iter_segment_lines(segment):
            stripped = raw.strip()
            if not stripped:
                continue
            parsed: dict[str, Any] | None = None
            try:
                obj = json.loads(stripped)
                if isinstance(obj, dict):
                    parsed = obj
            except (ValueError, TypeError):
                parsed = None
            if parsed is None and not include_corrupt:
                continue
            yield segment, line_no, parsed, stripped


# ---------------------------------------------------------------------------
# 9. Single-event lookup
# ---------------------------------------------------------------------------


def get_audit_event(
    event_id: str,
    *,
    hermes_home: str | os.PathLike[str] | None = None,
) -> tuple[dict[str, Any] | None, str | None]:
    """Fetch a single canonical event by ``eventId``.

    Returns ``(event_or_None, error_or_none)``. A missing event yields
    ``(None, None)`` (not an error).
    """
    if not isinstance(event_id, str) or not event_id:
        return None, ERROR_EVENT_INVALID
    root, err = get_audit_store_root(hermes_home)
    if err is not None:
        return None, err
    if not root.is_dir():
        return None, None
    for _seg, _line, event, _raw in iter_all_events(root):
        if event is not None and event.get("eventId") == event_id:
            return event, None
    return None, None


# ---------------------------------------------------------------------------
# 10. Append
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _next_sequence(meta: dict[str, Any]) -> int:
    return int(meta.get("lastSequence", 0) or 0) + 1


def _scan_existing(root: Path) -> tuple[set[str], int]:
    """Scan the store for known eventIds and the highest on-disk sequence.

    Returns ``(ids, max_sequence)``. Used as a correctness floor: even if the
    store-meta ``lastSequence`` is stale (e.g. a prior meta write failed after
    the event line was durable), the next sequence is floored against the real
    on-disk maximum so sequences never collide or gap.
    """
    ids: set[str] = set()
    max_seq = 0
    for _seg, _line, event, _raw in iter_all_events(root):
        if event is None:
            continue
        eid = event.get("eventId")
        if isinstance(eid, str):
            ids.add(eid)
        seq = event.get("sequence")
        if isinstance(seq, int) and not isinstance(seq, bool) and seq > max_seq:
            max_seq = seq
    return ids, max_seq


def _known_event_ids(root: Path) -> set[str]:
    """Backward-compatible alias returning only the id set."""
    return _scan_existing(root)[0]


def _serialize_event_line(event: dict[str, Any]) -> tuple[str | None, str | None]:
    """Serialize an event to a JSONL line. Returns ``(line, error_or_none)``."""
    try:
        line = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError):
        return None, ERROR_EVENT_INVALID
    if (len(line) + 1) > MAX_EVENT_BYTES:
        return None, ERROR_EVENT_TOO_LARGE
    return line, None


def _append_line_atomic(segment: Path, line: str) -> None:
    """Append a single line to *segment* with a safe flush + best-effort fsync."""
    segment.parent.mkdir(parents=True, exist_ok=True)
    # O_APPEND open guarantees atomic appends for small writes on POSIX.
    with open(segment, "a", encoding="utf-8") as f:
        f.write(line)
        f.write("\n")
        f.flush()
        try:
            os.fsync(f.fileno())
        except OSError:
            pass


def append_audit_event(
    event: dict[str, Any],
    *,
    hermes_home: str | os.PathLike[str] | None = None,
    stamp_sequence: bool = True,
) -> AuditStoreWriteResult:
    """Append a single canonical audit event to the durable store.

    The event is sanitized, validated, stamped with a monotonic ``sequence``
    (unless ``stamp_sequence=False``), and appended to the active segment.

    Returns an :class:`AuditStoreWriteResult`. Failures are reported via the
    ``error_code`` / ``error_message`` fields and never raise.
    """
    return append_audit_events(
        [event] if isinstance(event, dict) else [],
        hermes_home=hermes_home,
        stamp_sequence=stamp_sequence,
    )


def append_audit_events(
    events: list[dict[str, Any]],
    *,
    hermes_home: str | os.PathLike[str] | None = None,
    stamp_sequence: bool = True,
) -> AuditStoreWriteResult:
    """Append a batch of canonical audit events atomically under the store lock.

    All-or-nothing per batch from the caller's perspective: if any event in
    the batch fails validation, the whole batch is rejected (no partial
    append). Sequence numbers are assigned contiguously under the lock.
    """
    if not isinstance(events, list) or not events:
        return AuditStoreWriteResult(
            written=False,
            event_id=None,
            sequence=None,
            segment=None,
            rotated=False,
            error_code=ERROR_EVENT_INVALID,
            error_message="No events provided.",
        )

    root, err = ensure_audit_store(hermes_home)
    if err is not None:
        return AuditStoreWriteResult(
            written=False,
            event_id=None,
            sequence=None,
            segment=None,
            rotated=False,
            error_code=err,
            error_message=_error_message_for_code(err),
        )

    # Sanitize + validate every event up front (no partial batch).
    sanitized: list[dict[str, Any]] = []
    for raw in events:
        if not isinstance(raw, dict):
            return AuditStoreWriteResult(
                written=False, event_id=None, sequence=None, segment=None,
                rotated=False, error_code=ERROR_EVENT_INVALID,
                error_message="Event is not a JSON object.",
            )
        clean = sanitize_audit_event(raw)
        ok, reason = validate_canonical_event(clean)
        if not ok:
            return AuditStoreWriteResult(
                written=False, event_id=raw.get("eventId"),
                sequence=None, segment=None, rotated=False,
                error_code=ERROR_EVENT_INVALID,
                error_message=reason or "Invalid canonical event.",
            )
        sanitized.append(clean)

    with _WRITE_LOCK, _FileLock(_store_lock_path(root)):
        # Re-read meta under the lock to get an authoritative sequence.
        meta = _read_store_meta(root)
        meta.setdefault("schemaVersion", AUDIT_SCHEMA_VERSION)
        meta.setdefault("lastSequence", 0)
        meta.setdefault("lastEventId", None)
        meta.setdefault("eventCount", 0)
        meta.setdefault("activeSegment", _segment_name(_FIRST_SEGMENT_NUMBER))

        # Duplicate eventId guard + on-disk sequence floor.
        last_seq = int(meta.get("lastSequence", 0) or 0)
        existing_count = int(meta.get("eventCount", 0) or 0)
        existing_ids: set[str] = set()
        if stamp_sequence:
            existing_ids, disk_max = _scan_existing(root)
            # Floor against the real on-disk maximum so a stale meta (e.g. a
            # prior meta write that failed after the line was durable) can
            # never cause a colliding or gapped sequence.
            last_seq = max(last_seq, disk_max)

        next_seq = last_seq
        to_write: list[tuple[dict[str, Any], str]] = []
        for ev in sanitized:
            eid = ev.get("eventId")
            if stamp_sequence:
                if eid in existing_ids:
                    return AuditStoreWriteResult(
                        written=False, event_id=eid, sequence=None,
                        segment=None, rotated=False,
                        error_code=ERROR_DUPLICATE_EVENT_ID,
                        error_message="Duplicate eventId rejected.",
                    )
                next_seq = _next_sequence_given(next_seq)
                ev = {**ev, "sequence": next_seq}
                existing_ids.add(eid)  # type: ignore[arg-type]
            else:
                next_seq = max(next_seq, int(ev.get("sequence", next_seq) or next_seq))
            line, lerr = _serialize_event_line(ev)
            if lerr is not None or line is None:
                return AuditStoreWriteResult(
                    written=False, event_id=eid, sequence=ev.get("sequence"),
                    segment=None, rotated=False, error_code=lerr,
                    error_message=_error_message_for_code(lerr or ""),
                )
            to_write.append((ev, line))

        # Rotation: decide the active segment under the lock.
        rotated = False
        # Lazy import avoids a circular module dependency at load time.
        from hermes_cli.dev_web_audit_rotation import (
            get_active_audit_segment,
            should_rotate_audit_segment,
        )

        segment_path = get_active_audit_segment(root, meta)
        if should_rotate_audit_segment(segment_path, meta):
            from hermes_cli.dev_web_audit_rotation import rotate_audit_segment
            segment_path, rotated = rotate_audit_segment(root, meta)

        # Append all lines.
        try:
            for _ev, line in to_write:
                _append_line_atomic(segment_path, line)
        except OSError as exc:
            return AuditStoreWriteResult(
                written=False, event_id=sanitized[-1].get("eventId"),
                sequence=next_seq, segment=segment_path.name, rotated=rotated,
                error_code=ERROR_WRITE_FAILED,
                error_message=f"Append failed: {exc!s}",
            )

        # Update meta: last sequence, last event id, count, active segment.
        # Best-effort: the event is already durable on disk; a meta-write
        # failure is recovered by the on-disk sequence floor on the next
        # append and by an index rebuild. Never let it raise here.
        meta["lastSequence"] = next_seq
        meta["lastEventId"] = sanitized[-1].get("eventId")
        meta["eventCount"] = existing_count + len(to_write)
        meta["activeSegment"] = segment_path.name
        meta["schemaVersion"] = AUDIT_SCHEMA_VERSION
        try:
            _write_store_meta(root, meta)
        except OSError:
            pass

        return AuditStoreWriteResult(
            written=True,
            event_id=sanitized[-1].get("eventId"),
            sequence=next_seq,
            segment=segment_path.name,
            rotated=rotated,
            error_code=None,
            error_message=None,
        )


def _next_sequence_given(current: int) -> int:
    return int(current) + 1


# ---------------------------------------------------------------------------
# 11. Build helper
# ---------------------------------------------------------------------------


def build_audit_event(
    *,
    event_type: str,
    audit_kind: str,
    event_id: str | None = None,
    source: str | None = None,
    tool_id: str | None = None,
    tool_category: str | None = None,
    mode: str | None = None,
    status: str | None = None,
    blocked_reason: str | None = None,
    read_only: bool | None = None,
    write_required: bool | None = None,
    provider_mode: str | None = None,
    provider_schema_sent: bool | None = None,
    provider_api_called: bool | None = None,
    external_network_called: bool | None = None,
    local_side_effects: bool | None = None,
    external_side_effects: bool | None = None,
    redaction_applied: bool = False,
    execution_id: str | None = None,
    dry_run_id: str | None = None,
    dispatch_id: str | None = None,
    handler_call_id: str | None = None,
    pre_execution_audit_id: str | None = None,
    post_execution_audit_id: str | None = None,
    provider_request_id: str | None = None,
    provider_response_id: str | None = None,
    write_plan_id: str | None = None,
    write_preview_id: str | None = None,
    rollback_id: str | None = None,
    confirmation_token_id: str | None = None,
    summary: dict[str, Any] | None = None,
    safe_metadata: dict[str, Any] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """Build a canonical audit event dict ready for ``append_audit_event``.

    Stamps ``eventId`` (unless supplied) and ``createdAt``; ``sequence`` is
    assigned by the store writer. Explicit canonical params map to their
    canonical fields; any unrecognized keyword is forwarded into
    ``safeMetadata`` after sanitization so callers cannot accidentally persist
    a raw field.
    """
    event: dict[str, Any] = {
        "eventId": event_id if isinstance(event_id, str) and event_id else str(uuid.uuid4()),
        "sequence": 0,  # placeholder; store writer assigns the real value
        "createdAt": _now_iso(),
        "eventType": event_type,
        "auditKind": audit_kind,
        "schemaVersion": AUDIT_SCHEMA_VERSION,
        "summary": dict(summary) if summary else {},
        "safeMetadata": dict(safe_metadata) if safe_metadata else {},
        "redactionApplied": bool(redaction_applied),
    }
    # Map explicit canonical params → canonical (camelCase) fields.
    _optional = {
        "source": source, "toolId": tool_id, "toolCategory": tool_category,
        "mode": mode, "status": status, "blockedReason": blocked_reason,
        "readOnly": read_only, "writeRequired": write_required,
        "providerMode": provider_mode,
        "providerSchemaSent": provider_schema_sent,
        "providerApiCalled": provider_api_called,
        "externalNetworkCalled": external_network_called,
        "localSideEffects": local_side_effects,
        "externalSideEffects": external_side_effects,
        "executionId": execution_id, "dryRunId": dry_run_id,
        "dispatchId": dispatch_id, "handlerCallId": handler_call_id,
        "preExecutionAuditId": pre_execution_audit_id,
        "postExecutionAuditId": post_execution_audit_id,
        "providerRequestId": provider_request_id,
        "providerResponseId": provider_response_id,
        "writePlanId": write_plan_id, "writePreviewId": write_preview_id,
        "rollbackId": rollback_id,
        "confirmationTokenId": confirmation_token_id,
    }
    for key, value in _optional.items():
        if value is not None:
            event[key] = value
    # Unrecognized kwargs → canonical camelCase fields are mapped directly;
    # anything else is forwarded into safeMetadata (sanitized later).
    canonical_camel = {
        "source", "phase", "toolId", "toolCategory", "mode", "blockedReason",
        "readOnly", "writeRequired", "providerMode", "providerSchemaSent",
        "providerApiCalled", "externalNetworkCalled", "localSideEffects",
        "externalSideEffects", "executionId", "dryRunId", "dispatchId",
        "handlerCallId", "preExecutionAuditId", "postExecutionAuditId",
        "providerRequestId", "providerResponseId", "writePlanId",
        "writePreviewId", "rollbackId", "confirmationTokenId", "eventId",
    }
    for key, value in extra.items():
        if key in canonical_camel and value is not None:
            event[key] = value
        else:
            event["safeMetadata"][key] = value
    return event


# ---------------------------------------------------------------------------
# 12. Error messages
# ---------------------------------------------------------------------------


_ERROR_MESSAGES: dict[str, str] = {
    ERROR_HERMES_HOME_MISSING: "HERMES_HOME is not set.",
    ERROR_STORE_ROOT_FORBIDDEN: (
        "Audit store root is outside the dev HERMES_HOME or points to a "
        "forbidden location (production home, repository, or state.db)."
    ),
    ERROR_EVENT_INVALID: "Invalid canonical audit event.",
    ERROR_EVENT_TOO_LARGE: "Audit event exceeds maximum size.",
    ERROR_DUPLICATE_EVENT_ID: "Duplicate eventId.",
    ERROR_WRITE_FAILED: "Audit store write failed.",
}


def _error_message_for_code(code: str) -> str:
    return _ERROR_MESSAGES.get(code, "Unknown audit store error.")
