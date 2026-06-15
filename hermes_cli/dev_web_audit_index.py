"""Audit Index Builder for the Hermes Dev WebUI (Phase 2D).

Builds and maintains per-field indexes over the durable audit store. The index
accelerates equality lookups (``eventType``, ``toolId``, ``status``,
``auditKind``, ``source``, ``providerMode``, ``readOnly``, ``writeRequired``,
``createdDate``) and exposes a consistency view used by the Audit Viewer.

Design note
-----------
The audit **query engine** treats a full segment scan as the source of truth
(robust to rotation, corruption, and a stale/missing index). The index is an
*accelerator* and a *status signal*: when present and consistent it can short-
circuit equality filters; when missing or stale the engine rebuilds it (or
falls back to a scan) and never returns wrong results. The index stores only
safe correlation data — ``sequence``, ``eventId``, segment name, line number —
never raw arguments, secrets, or full token hashes.

Hard guarantees:
  - index files live only under ``$HERMES_HOME/gateway/dev/audit-store/indexes``
  - a missing index triggers a rebuild on demand
  - a corrupt index is quarantined + rebuilt
  - index update failure never loses a durable event (the event is already on
    disk; the index is marked stale and rebuilt later)
  - index contents are JSON-native and secret-free

Phase: 2D — Durable Dev Audit Store MVP
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from hermes_cli.dev_web_audit_schema import AUDIT_SCHEMA_VERSION
from hermes_cli.dev_web_audit_store import (
    _INDEXES_SUBDIR,
    iter_all_events,
    list_audit_segments,
    parse_segment_number,
)

# ---------------------------------------------------------------------------
# 1. Indexed fields
# ---------------------------------------------------------------------------

#: Fields that get a dedicated ``by-<field>.json`` index file.
INDEXED_FIELDS: tuple[str, ...] = (
    "eventType",
    "toolId",
    "status",
    "auditKind",
    "source",
    "providerMode",
    "readOnly",
    "writeRequired",
    "createdDate",
)

#: The high-water-mark sequence file (index consistency marker).
SEQUENCE_INDEX_FILENAME = "sequence.json"

#: Per-field index filename pattern.
def _field_index_filename(field_name: str) -> str:
    return f"by-{field_name.replace('_', '-')}.json"


# ---------------------------------------------------------------------------
# 2. Index record + view
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class IndexEntry:
    """A single index pointer (no payload, no secrets)."""

    sequence: int
    event_id: str
    segment: str
    line: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "seq": self.sequence,
            "id": self.event_id,
            "seg": self.segment,
            "line": self.line,
        }


@dataclass(frozen=True, slots=True)
class IndexStatus:
    """Safe summary of index health (no paths, no secrets)."""

    present: bool
    consistent: bool
    stale: bool
    last_sequence: int
    event_count: int
    segment_count: int
    fields: tuple[str, ...] = ()
    extra: dict[str, Any] = field(default_factory=dict)

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "present": self.present,
            "consistent": self.consistent,
            "stale": self.stale,
            "lastSequence": self.last_sequence,
            "eventCount": self.event_count,
            "segmentCount": self.segment_count,
            "fields": list(self.fields),
        }


# ---------------------------------------------------------------------------
# 3. Path helpers
# ---------------------------------------------------------------------------


def _indexes_dir(root: Path) -> Path:
    return root / _INDEXES_SUBDIR


def _field_index_path(root: Path, field_name: str) -> Path:
    return _indexes_dir(root) / _field_index_filename(field_name)


def _sequence_index_path(root: Path) -> Path:
    return _indexes_dir(root) / SEQUENCE_INDEX_FILENAME


# ---------------------------------------------------------------------------
# 4. Field value extraction
# ---------------------------------------------------------------------------


def _indexable_value(event: dict[str, Any], field_name: str) -> Any:
    """Extract the indexable scalar value for *field_name*, or ``None``."""
    if field_name == "createdDate":
        created = event.get("createdAt")
        if isinstance(created, str) and len(created) >= 10:
            return created[:10]  # YYYY-MM-DD
        return None
    return event.get(field_name)


def _value_key(value: Any) -> str:
    """Normalize an indexable value into a JSON-key string."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


# ---------------------------------------------------------------------------
# 5. Index build / read / write
# ---------------------------------------------------------------------------


def _write_json_safe(path: Path, payload: Any) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, sort_keys=True)
            f.flush()
            try:
                os.fsync(f.fileno())
            except OSError:
                pass
        tmp.replace(path)
        return True
    except OSError:
        return False


def _read_json_safe(path: Path) -> Any:
    if not path.is_file():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _max_sequence(root: Path) -> int:
    """Return the highest sequence observed across all segments (scan)."""
    highest = 0
    for _seg, _line, event, _raw in iter_all_events(root):
        if event is not None:
            seq = event.get("sequence")
            if isinstance(seq, int) and not isinstance(seq, bool) and seq > highest:
                highest = seq
    return highest


def _event_count(root: Path) -> int:
    return sum(1 for _ in iter_all_events(root))


def rebuild_audit_index(root: Path) -> dict[str, Any]:
    """Rebuild every per-field index + the sequence marker from a full scan.

    Returns a safe summary dict. Never raises; failures are reported in the
    summary. Overwrites stale index files atomically.
    """
    indexes_dir = _indexes_dir(root)
    try:
        indexes_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return {"rebuilt": False, "reason": "cannot create indexes dir"}

    # Collect entries per field in one pass.
    buckets: dict[str, dict[str, list[dict[str, Any]]]] = {
        f: {} for f in INDEXED_FIELDS
    }
    total = 0
    highest = 0
    for segment, line_no, event, _raw in iter_all_events(root):
        if event is None:
            continue
        total += 1
        seq = event.get("sequence")
        if isinstance(seq, int) and not isinstance(seq, bool) and seq > highest:
            highest = seq
        eid = event.get("eventId")
        if not isinstance(eid, str):
            continue
        entry = {
            "seq": seq if isinstance(seq, int) else 0,
            "id": eid,
            "seg": segment.name,
            "line": line_no,
        }
        for field_name in INDEXED_FIELDS:
            value = _indexable_value(event, field_name)
            if value is None:
                continue
            key = _value_key(value)
            buckets[field_name].setdefault(key, []).append(entry)

    segment_count = len(list_audit_segments(root))

    # Write each field index.
    written_fields: list[str] = []
    for field_name, values in buckets.items():
        # Sort each bucket by sequence ascending for deterministic iteration.
        payload_values = {
            key: sorted(entries, key=lambda e: e["seq"])
            for key, entries in values.items()
        }
        payload = {
            "schemaVersion": AUDIT_SCHEMA_VERSION,
            "field": field_name,
            "values": payload_values,
            "lastSequence": highest,
            "eventCount": total,
        }
        if _write_json_safe(_field_index_path(root, field_name), payload):
            written_fields.append(field_name)

    # Write the sequence marker.
    seq_payload = {
        "schemaVersion": AUDIT_SCHEMA_VERSION,
        "lastSequence": highest,
        "eventCount": total,
        "segmentCount": segment_count,
        "fields": written_fields,
    }
    _write_json_safe(_sequence_index_path(root), seq_payload)

    return {
        "rebuilt": True,
        "lastSequence": highest,
        "eventCount": total,
        "segmentCount": segment_count,
        "fields": written_fields,
    }


def update_audit_index_for_event(
    event: dict[str, Any],
    root: Path,
    *,
    segment_name: str,
    line_no: int,
) -> bool:
    """Incrementally update the per-field indexes for one newly-appended event.

    Returns ``True`` on success, ``False`` if the index is missing/stale (the
    caller should rebuild on the next query). Best-effort: a failure here never
    loses the event, which is already durable on disk.
    """
    seq_marker = _read_json_safe(_sequence_index_path(root))
    if not isinstance(seq_marker, dict):
        return False  # index missing → caller rebuilds

    eid = event.get("eventId")
    seq = event.get("sequence")
    if not isinstance(eid, str) or not isinstance(seq, int):
        return False

    entry = {"seq": seq, "id": eid, "seg": segment_name, "line": line_no}
    for field_name in INDEXED_FIELDS:
        value = _indexable_value(event, field_name)
        if value is None:
            continue
        path = _field_index_path(root, field_name)
        payload = _read_json_safe(path)
        if not isinstance(payload, dict):
            # A field index is missing → index is incomplete; mark stale.
            _mark_stale(root)
            return False
        values = payload.get("values")
        if not isinstance(values, dict):
            return False
        key = _value_key(value)
        bucket = values.setdefault(key, [])
        bucket.append(entry)
        bucket.sort(key=lambda e: e["seq"])
        payload["lastSequence"] = max(
            int(payload.get("lastSequence", 0) or 0), seq
        )
        if not _write_json_safe(path, payload):
            return False

    # Advance the sequence marker.
    seq_marker["lastSequence"] = max(
        int(seq_marker.get("lastSequence", 0) or 0), seq
    )
    seq_marker["eventCount"] = int(seq_marker.get("eventCount", 0) or 0) + 1
    seq_marker.pop("stale", None)
    _write_json_safe(_sequence_index_path(root), seq_marker)
    return True


def _mark_stale(root: Path) -> None:
    seq_marker = _read_json_safe(_sequence_index_path(root))
    if isinstance(seq_marker, dict):
        seq_marker["stale"] = True
        _write_json_safe(_sequence_index_path(root), seq_marker)


# ---------------------------------------------------------------------------
# 6. Load + query
# ---------------------------------------------------------------------------


def load_audit_index(root: Path) -> dict[str, Any]:
    """Load the sequence marker (index presence/consistency view)."""
    seq_marker = _read_json_safe(_sequence_index_path(root))
    if not isinstance(seq_marker, dict):
        return {
            "schemaVersion": AUDIT_SCHEMA_VERSION,
            "present": False,
            "lastSequence": 0,
            "eventCount": 0,
            "segmentCount": len(list_audit_segments(root)),
            "fields": [],
        }
    seq_marker["present"] = True
    return seq_marker


def query_audit_index(
    field_name: str,
    value: Any,
    root: Path,
) -> list[dict[str, Any]] | None:
    """Return index entries matching ``field_name == value``.

    Returns ``None`` when the index is missing or corrupt (caller falls back
    to a full scan). Returns the matching entries (each a dict with
    ``seq``/``id``/``seg``/``line``) otherwise — possibly empty.
    """
    if field_name not in INDEXED_FIELDS:
        return None
    payload = _read_json_safe(_field_index_path(root, field_name))
    if not isinstance(payload, dict):
        return None
    values = payload.get("values")
    if not isinstance(values, dict):
        return None
    key = _value_key(value)
    bucket = values.get(key)
    if not isinstance(bucket, list):
        return []
    return list(bucket)


# ---------------------------------------------------------------------------
# 7. Validate + repair
# ---------------------------------------------------------------------------


def validate_audit_index(root: Path) -> IndexStatus:
    """Validate index consistency against the on-disk store (scan)."""
    seq_marker = _read_json_safe(_sequence_index_path(root))
    present = isinstance(seq_marker, dict)
    if not present:
        return IndexStatus(
            present=False,
            consistent=False,
            stale=True,
            last_sequence=0,
            event_count=0,
            segment_count=len(list_audit_segments(root)),
            fields=(),
        )

    on_disk_seq = _max_sequence(root)
    on_disk_count = _event_count(root)
    idx_seq = int(seq_marker.get("lastSequence", 0) or 0)
    idx_count = int(seq_marker.get("eventCount", 0) or 0)
    stale = bool(seq_marker.get("stale", False))
    consistent = (idx_seq == on_disk_seq) and (idx_count == on_disk_count) and not stale
    fields = tuple(seq_marker.get("fields", []) or [])
    return IndexStatus(
        present=True,
        consistent=consistent,
        stale=stale or not consistent,
        last_sequence=idx_seq,
        event_count=idx_count,
        segment_count=len(list_audit_segments(root)),
        fields=fields,
    )


def repair_audit_index_if_needed(root: Path) -> dict[str, Any]:
    """Rebuild the index if it is missing, stale, or inconsistent.

    Returns the rebuild summary (always succeeds in producing an index; if the
    rebuild itself fails the summary reports ``rebuilt=False``).
    """
    status = validate_audit_index(root)
    if status.present and status.consistent:
        return {
            "rebuilt": False,
            "reason": "index already consistent",
            "lastSequence": status.last_sequence,
            "eventCount": status.event_count,
        }
    return rebuild_audit_index(root)
