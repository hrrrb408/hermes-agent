"""Audit Segment Rotation Policy for the Hermes Dev WebUI (Phase 2D).

Controls when the append-only audit store rolls over to a new segment file.
Rotation is driven by two thresholds:

  - maximum segment size (bytes)
  - maximum events per segment (line count)

When the active segment crosses either threshold, a new monotonically numbered
segment is created. Old segments are **never** deleted — that is deferred to a
future retention phase. Queries and indexes transparently span all segments.

Hard guarantees:
  - rotation never overwrites or deletes an existing segment
  - segment filenames are monotonically increasing and zero-padded
  - rotation state is persisted (survives restarts)
  - a partial/interrupted rotation is recoverable (the next append picks the
    highest existing segment or creates the next one)

Phase: 2D — Durable Dev Audit Store MVP
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hermes_cli.dev_web_audit_store import (
    _FIRST_SEGMENT_NUMBER,
    _META_SUBDIR,
    _ROTATION_STATE_FILENAME,
    _events_dir,
    _segment_name,
    _segment_path,
    list_audit_segments,
    parse_segment_number,
)

# ---------------------------------------------------------------------------
# 1. Defaults
# ---------------------------------------------------------------------------

#: Default maximum segment size (1 MiB). Tests override this with smaller values.
DEFAULT_MAX_SEGMENT_BYTES = 1 * 1024 * 1024

#: Default maximum events per segment (1000 lines).
DEFAULT_MAX_EVENTS_PER_SEGMENT = 1000


@dataclass(frozen=True, slots=True)
class RotationPolicy:
    """Immutable rotation thresholds."""

    max_segment_bytes: int = DEFAULT_MAX_SEGMENT_BYTES
    max_events_per_segment: int = DEFAULT_MAX_EVENTS_PER_SEGMENT

    def validate(self) -> str | None:
        if self.max_segment_bytes < 1024:
            return "max_segment_bytes must be >= 1024"
        if self.max_events_per_segment < 1:
            return "max_events_per_segment must be >= 1"
        return None


# ---------------------------------------------------------------------------
# 2. Rotation-state persistence
# ---------------------------------------------------------------------------


def _rotation_state_path(root: Path) -> Path:
    return root / _META_SUBDIR / _ROTATION_STATE_FILENAME


def load_rotation_state(root: Path) -> dict[str, Any]:
    path = _rotation_state_path(root)
    if not path.is_file():
        return {
            "activeSegment": _segment_name(_FIRST_SEGMENT_NUMBER),
            "segmentCount": 1,
            "rotatedCount": 0,
        }
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            data.setdefault("activeSegment", _segment_name(_FIRST_SEGMENT_NUMBER))
            data.setdefault("segmentCount", 1)
            data.setdefault("rotatedCount", 0)
            return data
    except (OSError, ValueError):
        pass
    return {
        "activeSegment": _segment_name(_FIRST_SEGMENT_NUMBER),
        "segmentCount": 1,
        "rotatedCount": 0,
    }


def _save_rotation_state(root: Path, state: dict[str, Any]) -> None:
    path = _rotation_state_path(root)
    payload = json.dumps(state, ensure_ascii=False, sort_keys=True)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        with tmp.open("w", encoding="utf-8") as f:
            f.write(payload)
            f.flush()
            try:
                os.fsync(f.fileno())
            except OSError:
                pass
        tmp.replace(path)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# 3. Segment counting helpers
# ---------------------------------------------------------------------------


def _count_segment_lines(segment: Path) -> int:
    """Count non-empty lines in a segment file."""
    if not segment.is_file():
        return 0
    count = 0
    try:
        with segment.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    count += 1
    except OSError:
        return 0
    return count


def _segment_size(segment: Path) -> int:
    if not segment.is_file():
        return 0
    try:
        return segment.stat().st_size
    except OSError:
        return 0


# ---------------------------------------------------------------------------
# 4. Rotation decision
# ---------------------------------------------------------------------------


def should_rotate_audit_segment(
    segment: Path,
    meta: dict[str, Any] | None = None,
    *,
    policy: RotationPolicy | None = None,
) -> bool:
    """Return ``True`` if *segment* should be rotated before the next append.

    Rotation is required when the segment already exists and exceeds either
    the size or the event-count threshold. A missing segment never triggers
    rotation (it will be created fresh).
    """
    pol = policy or RotationPolicy()
    err = pol.validate()
    if err is not None:
        return False
    if not segment.is_file():
        return False
    if _segment_size(segment) >= pol.max_segment_bytes:
        return True
    if _count_segment_lines(segment) >= pol.max_events_per_segment:
        return True
    return False


def get_active_audit_segment(
    root: Path,
    meta: dict[str, Any] | None = None,
) -> Path:
    """Return the active segment path, reconciling meta vs on-disk state.

    If the meta-declared active segment does not exist on disk (e.g. after a
    crash mid-rotation), the highest existing segment is used, or the first
    segment is created lazily on first append.
    """
    state = load_rotation_state(root)
    active_name = state.get("activeSegment") or (
        meta.get("activeSegment") if meta else None
    )
    if isinstance(active_name, str) and parse_segment_number(active_name) is not None:
        candidate = _events_dir(root) / active_name
        return candidate
    segments = list_audit_segments(root)
    if segments:
        return segments[-1]
    return _segment_path(root, _FIRST_SEGMENT_NUMBER)


def get_active_audit_segment_path(root: Path) -> Path:
    """Public alias for the active segment path (used by recovery / status)."""
    return get_active_audit_segment(root)


def get_active_audit_segment_number(root: Path) -> int:
    """Return the active segment number (default 1 when none exist)."""
    seg = get_active_audit_segment(root)
    num = parse_segment_number(seg.name)
    return num if num is not None else _FIRST_SEGMENT_NUMBER


# ---------------------------------------------------------------------------
# 5. Rotation execution
# ---------------------------------------------------------------------------


def rotate_audit_segment(
    root: Path,
    meta: dict[str, Any] | None = None,
    *,
    policy: RotationPolicy | None = None,
) -> tuple[Path, bool]:
    """Rotate to a fresh segment and return ``(new_segment_path, rotated)``.

    - Determines the next segment number (highest existing + 1).
    - Creates the new (empty) segment file so it becomes the append target.
    - Persists updated rotation state.

    Idempotent: calling it twice in a row still yields a valid active segment
    and never overwrites existing segments.
    """
    _ = policy  # policy is consulted by should_rotate; here we just advance.
    segments = list_audit_segments(root)
    if segments:
        last_num = parse_segment_number(segments[-1].name) or _FIRST_SEGMENT_NUMBER
        next_num = last_num + 1
    else:
        next_num = _FIRST_SEGMENT_NUMBER

    new_segment = _segment_path(root, next_num)
    try:
        # Touch the new segment so it exists as the append target.
        new_segment.parent.mkdir(parents=True, exist_ok=True)
        if not new_segment.exists():
            new_segment.touch()
    except OSError:
        # If we cannot create the new segment, fall back to the last existing
        # one so the caller can still append (rotation is best-effort).
        if segments:
            return segments[-1], False
        return new_segment, False

    state = load_rotation_state(root)
    state["activeSegment"] = new_segment.name
    state["segmentCount"] = len(list_audit_segments(root))
    state["rotatedCount"] = int(state.get("rotatedCount", 0) or 0) + 1
    _save_rotation_state(root, state)

    # Keep store meta's activeSegment in sync.
    if meta is not None:
        meta["activeSegment"] = new_segment.name

    return new_segment, True


def list_audit_segments_rotation(root: Path) -> list[Path]:
    """Public alias for listing segments (used by recovery / status)."""
    return list_audit_segments(root)


def validate_audit_segments(root: Path) -> dict[str, Any]:
    """Return a safe summary of segment integrity (counts, ordering)."""
    segments = list_audit_segments(root)
    numbers = [parse_segment_number(p.name) for p in segments]
    numbers = [n for n in numbers if n is not None]
    monotonic = all(
        numbers[i] < numbers[i + 1] for i in range(len(numbers) - 1)
    )
    return {
        "segmentCount": len(segments),
        "segmentNumbers": sorted(n for n in numbers if n is not None),
        "monotonic": monotonic,
        "activeSegment": load_rotation_state(root).get(
            "activeSegment", _segment_name(_FIRST_SEGMENT_NUMBER)
        ),
    }
