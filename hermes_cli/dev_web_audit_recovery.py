"""Audit Corruption Detection + Quarantine for the Hermes Dev WebUI (Phase 2D).

Scans the durable audit store for corrupt records and quarantines them so
queries never crash on a bad line. This is non-destructive in Phase 2D: corrupt
lines are copied to ``quarantine/`` and skipped during query; the original
segment is left intact unless an explicit clean-segment repair is requested.

Detected corruption classes:
  - invalid JSON line (unparseable)
  - line is valid JSON but not an object
  - missing required canonical field
  - ``schemaVersion`` mismatch
  - non-JSON-native value present in the record
  - unsafe secret-like value present in the record
  - duplicate ``sequence``
  - duplicate ``eventId``
  - partial write line (no trailing newline / truncated)

Hard guarantees:
  - quarantine files live only under the dev audit store
  - the original segment is never deleted by quarantine
  - quarantine never prints or persists secrets (corrupt payloads are copied
    verbatim only into the dev-local quarantine directory)
  - query path skips quarantined corrupt lines safely (see query engine)

Phase: 2D — Durable Dev Audit Store MVP
"""

from __future__ import annotations

import json
import os
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from hermes_cli.dev_web_audit_schema import (
    AUDIT_SCHEMA_VERSION,
    REQUIRED_EVENT_FIELDS,
    validate_canonical_event,
)
from hermes_cli.dev_web_audit_sanitizer import (
    REDACTED_SENTINEL,
    _is_forbidden_field,
    _SECRET_VALUE_PATTERNS,
)
from hermes_cli.dev_web_audit_store import (
    _QUARANTINE_SUBDIR,
    iter_segment_lines,
    list_audit_segments,
    parse_segment_number,
)
from hermes_cli.dev_web_audit_index import rebuild_audit_index

# ---------------------------------------------------------------------------
# 1. Corruption reason codes
# ---------------------------------------------------------------------------

CORRUPT_INVALID_JSON = "invalid_json"
CORRUPT_NOT_OBJECT = "not_object"
CORRUPT_MISSING_FIELD = "missing_required_field"
CORRUPT_SCHEMA_VERSION = "schema_version_mismatch"
CORRUPT_NON_JSON_NATIVE = "non_json_native_value"
CORRUPT_UNSAFE_SECRET = "unsafe_secret_value"
CORRUPT_DUPLICATE_SEQUENCE = "duplicate_sequence"
CORRUPT_DUPLICATE_EVENT_ID = "duplicate_event_id"
CORRUPT_PARTIAL_WRITE = "partial_write_line"


@dataclass(frozen=True, slots=True)
class CorruptRecord:
    """A single detected corrupt record (no secret payload in fields)."""

    segment: str
    line: int
    reason: str
    detail: str
    raw: str = field(default="", repr=False)


@dataclass(frozen=True, slots=True)
class ScanReport:
    """Safe summary of a corruption scan (no payloads, no secrets)."""

    segments_scanned: int
    lines_scanned: int
    corrupt_count: int
    reasons: dict[str, int]
    records: tuple[CorruptRecord, ...]
    duplicates: dict[str, int]

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "segmentsScanned": self.segments_scanned,
            "linesScanned": self.lines_scanned,
            "corruptCount": self.corrupt_count,
            "reasons": dict(self.reasons),
            "records": [
                {
                    "segment": r.segment,
                    "line": r.line,
                    "reason": r.reason,
                    "detail": r.detail,
                }
                for r in self.records
            ],
            "duplicates": dict(self.duplicates),
        }


# ---------------------------------------------------------------------------
# 2. Per-line corruption detection
# ---------------------------------------------------------------------------


def _has_non_json_native(value: Any) -> bool:
    """Return ``True`` if *value* contains a non-JSON-native leaf."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return False
    if isinstance(value, dict):
        return any(_has_non_json_native(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return any(_has_non_json_native(v) for v in value)
    # bytes, callable, object, etc.
    return True


def _has_unsafe_secret(value: Any) -> bool:
    """Return ``True`` if *value* carries a secret-like string."""
    if isinstance(value, str):
        for pattern in _SECRET_VALUE_PATTERNS:
            if pattern.search(value):
                return True
        return False
    if isinstance(value, dict):
        return any(_has_unsafe_secret(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return any(_has_unsafe_secret(v) for v in value)
    return False


def _has_forbidden_field(value: Any) -> bool:
    """Return ``True`` if *value* (dict) contains a forbidden secret field."""
    if isinstance(value, dict):
        for k, v in value.items():
            if _is_forbidden_field(k) and v not in (None, REDACTED_SENTINEL):
                return True
            if _has_forbidden_field(v):
                return True
    if isinstance(value, (list, tuple)):
        return any(_has_forbidden_field(v) for v in value)
    return False


def _classify_line(
    raw_line: str,
    *,
    has_trailing_newline: bool,
) -> tuple[dict[str, Any] | None, CorruptRecord | None]:
    """Classify a single segment line.

    Returns ``(parsed_event_or_None, corrupt_or_None)``.
    """
    stripped = raw_line.strip()
    if not stripped:
        return None, None

    # Partial-write detection: a non-empty final line without a trailing
    # newline strongly suggests a truncated/crashed write.
    if not has_trailing_newline and raw_line:
        return None, CorruptRecord(
            segment="",
            line=0,
            reason=CORRUPT_PARTIAL_WRITE,
            detail="line lacks a trailing newline (possible truncated write)",
            raw=raw_line,
        )

    try:
        obj = json.loads(stripped)
    except (ValueError, TypeError):
        return None, CorruptRecord(
            segment="",
            line=0,
            reason=CORRUPT_INVALID_JSON,
            detail="line is not valid JSON",
            raw=raw_line,
        )
    if not isinstance(obj, dict):
        return None, CorruptRecord(
            segment="",
            line=0,
            reason=CORRUPT_NOT_OBJECT,
            detail="line is JSON but not an object",
            raw=raw_line,
        )

    if obj.get("schemaVersion") != AUDIT_SCHEMA_VERSION:
        return obj, CorruptRecord(
            segment="",
            line=0,
            reason=CORRUPT_SCHEMA_VERSION,
            detail=f"schemaVersion is not {AUDIT_SCHEMA_VERSION}",
            raw=raw_line,
        )

    ok, reason = validate_canonical_event(obj)
    if not ok:
        # Distinguish missing-field from other validation failures.
        if reason and reason.startswith("missing required field"):
            code = CORRUPT_MISSING_FIELD
        else:
            code = CORRUPT_MISSING_FIELD
        return obj, CorruptRecord(
            segment="", line=0, reason=code, detail=reason or "invalid", raw=raw_line
        )

    if _has_non_json_native(obj):
        return obj, CorruptRecord(
            segment="",
            line=0,
            reason=CORRUPT_NON_JSON_NATIVE,
            detail="record contains a non-JSON-native value",
            raw=raw_line,
        )
    if _has_unsafe_secret(obj) or _has_forbidden_field(obj):
        return obj, CorruptRecord(
            segment="",
            line=0,
            reason=CORRUPT_UNSAFE_SECRET,
            detail="record contains an unsafe secret-like value",
            raw=raw_line,
        )
    return obj, None


# ---------------------------------------------------------------------------
# 3. Scan
# ---------------------------------------------------------------------------


def scan_audit_segments(root: Path) -> ScanReport:
    """Scan every segment for corrupt records. Returns a safe report."""
    records: list[CorruptRecord] = []
    reasons: dict[str, int] = {}
    seen_sequences: dict[int, str] = {}
    seen_event_ids: dict[str, str] = {}
    duplicate_seqs: dict[int, int] = {}
    duplicate_ids: dict[str, int] = {}
    lines_scanned = 0
    segments_scanned = 0

    for segment in list_audit_segments(root):
        segments_scanned += 1
        seg_name = segment.name
        # Read all lines once so we can detect a missing final newline.
        try:
            with segment.open("r", encoding="utf-8") as f:
                raw_lines = f.readlines()
        except OSError:
            continue
        for idx, raw in enumerate(raw_lines, start=1):
            lines_scanned += 1
            has_newline = raw.endswith("\n")
            parsed, corrupt = _classify_line(raw, has_trailing_newline=has_newline)
            if corrupt is not None:
                rec = CorruptRecord(
                    segment=seg_name,
                    line=idx,
                    reason=corrupt.reason,
                    detail=corrupt.detail,
                    raw=corrupt.raw,
                )
                records.append(rec)
                reasons[rec.reason] = reasons.get(rec.reason, 0) + 1
                continue
            if parsed is None:
                continue
            seq = parsed.get("sequence")
            eid = parsed.get("eventId")
            if isinstance(seq, int) and not isinstance(seq, bool):
                if seq in seen_sequences:
                    duplicate_seqs[seq] = duplicate_seqs.get(seq, 1) + 1
                    records.append(CorruptRecord(
                        segment=seg_name, line=idx,
                        reason=CORRUPT_DUPLICATE_SEQUENCE,
                        detail=f"duplicate sequence {seq}",
                        raw=raw,
                    ))
                    reasons[CORRUPT_DUPLICATE_SEQUENCE] = reasons.get(
                        CORRUPT_DUPLICATE_SEQUENCE, 0
                    ) + 1
                else:
                    seen_sequences[seq] = seg_name
            if isinstance(eid, str):
                if eid in seen_event_ids:
                    duplicate_ids[eid] = duplicate_ids.get(eid, 1) + 1
                    records.append(CorruptRecord(
                        segment=seg_name, line=idx,
                        reason=CORRUPT_DUPLICATE_EVENT_ID,
                        detail="duplicate eventId",
                        raw=raw,
                    ))
                    reasons[CORRUPT_DUPLICATE_EVENT_ID] = reasons.get(
                        CORRUPT_DUPLICATE_EVENT_ID, 0
                    ) + 1
                else:
                    seen_event_ids[eid] = seg_name

    duplicates = {str(k): v for k, v in duplicate_seqs.items()}
    duplicates.update(duplicate_ids)
    return ScanReport(
        segments_scanned=segments_scanned,
        lines_scanned=lines_scanned,
        corrupt_count=len(records),
        reasons=reasons,
        records=tuple(records),
        duplicates=duplicates,
    )


def detect_corrupt_audit_records(root: Path) -> list[CorruptRecord]:
    """Return the list of corrupt records (convenience wrapper)."""
    return list(scan_audit_segments(root).records)


# ---------------------------------------------------------------------------
# 4. Quarantine
# ---------------------------------------------------------------------------


def _quarantine_dir(root: Path) -> Path:
    return root / _QUARANTINE_SUBDIR


def quarantine_corrupt_records(
    root: Path,
    records: list[CorruptRecord] | None = None,
) -> dict[str, Any]:
    """Copy corrupt record lines into ``quarantine/``.

    Non-destructive: the original segment is left intact. Each batch of corrupt
    lines for a given source segment is written to a single quarantine file
    named ``corrupt-<token>-<segment-stem>.jsonl``. Returns a safe summary.
    """
    if records is None:
        records = list(scan_audit_segments(root).records)
    qdir = _quarantine_dir(root)
    try:
        qdir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return {"quarantined": 0, "reason": "cannot create quarantine dir"}

    by_source: dict[str, list[CorruptRecord]] = {}
    for rec in records:
        by_source.setdefault(rec.segment, []).append(rec)

    token = uuid.uuid4().hex[:8]
    quarantined = 0
    files_written: list[str] = []
    for source_seg, recs in by_source.items():
        stem = re.sub(r"[^A-Za-z0-9_.-]", "_", source_seg or "unknown")
        qpath = qdir / f"corrupt-{token}-{stem}.jsonl"
        try:
            with qpath.open("w", encoding="utf-8") as f:
                for rec in recs:
                    # Write the raw line verbatim (dev-local only) plus a
                    # safe JSON header comment line with the reason.
                    header = json.dumps(
                        {
                            "segment": rec.segment,
                            "line": rec.line,
                            "reason": rec.reason,
                            "detail": rec.detail,
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                    f.write("# " + header + "\n")
                    f.write((rec.raw.rstrip("\n") + "\n"))
                    quarantined += 1
            files_written.append(qpath.name)
        except OSError:
            continue

    return {
        "quarantined": quarantined,
        "files": files_written,
        "nonDestructive": True,
    }


# ---------------------------------------------------------------------------
# 5. Repair
# ---------------------------------------------------------------------------


def repair_audit_store(
    root: Path,
    *,
    create_clean_segment: bool = False,
) -> dict[str, Any]:
    """Repair the audit store after corruption.

    Phase 2D repair is non-destructive:
      1. Scan for corrupt records.
      2. Quarantine them (copy only).
      3. Rebuild the index so queries skip corrupt lines via the scan path.

    If ``create_clean_segment`` is ``True``, a fresh "clean" segment is written
    containing only the valid records (old segments are still kept). This is
    opt-in and not used by the default query path.
    """
    report = scan_audit_segments(root)
    qsummary = {"quarantined": 0, "files": []}
    if report.corrupt_count > 0:
        qsummary = quarantine_corrupt_records(root, list(report.records))

    index_summary = rebuild_audit_index(root)

    clean_summary: dict[str, Any] = {}
    if create_clean_segment:
        clean_summary = _write_clean_segment(root, report)

    return {
        "scanned": report.to_safe_dict(),
        "quarantine": qsummary,
        "index": index_summary,
        "cleanSegment": clean_summary,
        "nonDestructive": True,
    }


def _write_clean_segment(root: Path, report: ScanReport) -> dict[str, Any]:
    """Write a fresh segment containing only valid records (opt-in)."""
    from hermes_cli.dev_web_audit_store import _segment_path

    corrupt_lines = {
        (rec.segment, rec.line) for rec in report.records
    }
    valid: list[dict[str, Any]] = []
    for segment in list_audit_segments(root):
        try:
            with segment.open("r", encoding="utf-8") as f:
                raw_lines = f.readlines()
        except OSError:
            continue
        for idx, raw in enumerate(raw_lines, start=1):
            if (segment.name, idx) in corrupt_lines:
                continue
            stripped = raw.strip()
            if not stripped:
                continue
            try:
                obj = json.loads(stripped)
            except (ValueError, TypeError):
                continue
            if isinstance(obj, dict) and validate_canonical_event(obj)[0]:
                valid.append(obj)

    if not valid:
        return {"written": False, "reason": "no valid records"}

    # Number the clean segment well beyond existing segments.
    existing = list_audit_segments(root)
    next_num = 9_999_000
    if existing:
        nums = [parse_segment_number(p.name) or 0 for p in existing]
        next_num = max(nums) + 1
    clean_path = _segment_path(root, next_num)
    try:
        clean_path.parent.mkdir(parents=True, exist_ok=True)
        with clean_path.open("w", encoding="utf-8") as f:
            for obj in valid:
                f.write(
                    json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n"
                )
        return {"written": True, "segment": clean_path.name, "records": len(valid)}
    except OSError:
        return {"written": False, "reason": "write failed"}
