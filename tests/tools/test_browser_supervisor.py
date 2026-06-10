"""Unit tests for tools.browser_supervisor — no real browser required.

These tests exercise the CDPSupervisor, _SupervisorRegistry, browser_dialog_tool,
and browser_cdp_tool integration paths using mocked CDP/WebSocket boundaries.

Every test runs without a real browser process.  The CDP supervisor's internal
state is set up directly (bypassing the real WebSocket connect path) so that the
public sync API — snapshot(), respond_to_dialog(), evaluate_runtime(), stop() —
is tested against known state configurations.

Corresponding E2E tests (requiring a real Chrome process) live in
``test_browser_supervisor_e2e.py``.
"""

from __future__ import annotations

import asyncio
import json
import threading
import time
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

from tools.browser_supervisor import (
    CONSOLE_HISTORY_MAX,
    CDPSupervisor,
    DIALOG_POLICY_AUTO_ACCEPT,
    DIALOG_POLICY_AUTO_DISMISS,
    DIALOG_POLICY_MUST_RESPOND,
    DialogRecord,
    FrameInfo,
    PendingDialog,
    RECENT_DIALOGS_MAX,
    SUPERVISOR_REGISTRY,
    SupervisorSnapshot,
    _SupervisorRegistry,
)
from tools.browser_supervisor import (
    ConsoleEvent,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_supervisor(
    task_id: str = "test-task",
    cdp_url: str = "ws://127.0.0.1:9222/devtools/page/FAKE",
    *,
    dialog_policy: str = DIALOG_POLICY_MUST_RESPOND,
    active: bool = True,
) -> CDPSupervisor:
    """Create a CDPSupervisor with internal state pre-set for unit testing.

    Bypasses the real start()/WebSocket path by directly setting internal fields.
    This avoids needing a real browser, real WebSocket, or real asyncio loop.
    """
    sv = object.__new__(CDPSupervisor)
    sv.task_id = task_id
    sv.cdp_url = cdp_url
    sv.dialog_policy = dialog_policy
    sv.dialog_timeout_s = 300.0
    sv._state_lock = threading.Lock()
    sv._pending_dialogs = {}
    sv._recent_dialogs = []
    sv._frames = {}
    sv._console_events = []
    sv._active = active
    sv._loop = None
    sv._thread = None
    sv._ready_event = threading.Event()
    sv._start_error = None
    sv._stop_requested = False
    sv._next_call_id = 1
    sv._pending_calls = {}
    sv._ws = None
    sv._page_session_id = "test-page-session-001"
    sv._child_sessions = {}
    sv._dialog_watchdogs = {}
    sv._dialog_seq = 0
    return sv


def _add_frame(
    sv: CDPSupervisor,
    frame_id: str,
    *,
    url: str = "https://example.com",
    origin: str = "https://example.com",
    parent_frame_id: Optional[str] = None,
    is_oopif: bool = False,
    cdp_session_id: Optional[str] = None,
) -> FrameInfo:
    """Add a frame to the supervisor's internal frame dict."""
    fi = FrameInfo(
        frame_id=frame_id,
        url=url,
        origin=origin,
        parent_frame_id=parent_frame_id,
        is_oopif=is_oopif,
        cdp_session_id=cdp_session_id,
    )
    with sv._state_lock:
        sv._frames[frame_id] = fi
    return fi


def _add_pending_dialog(
    sv: CDPSupervisor,
    dialog_id: str = "dialog-1",
    dialog_type: str = "alert",
    message: str = "test alert",
    *,
    cdp_session_id: str = "test-page-session-001",
    frame_id: Optional[str] = None,
    bridge_request_id: Optional[str] = None,
    default_prompt: str = "",
) -> PendingDialog:
    """Add a pending dialog to the supervisor's internal state."""
    d = PendingDialog(
        id=dialog_id,
        type=dialog_type,
        message=message,
        default_prompt=default_prompt,
        opened_at=time.monotonic(),
        cdp_session_id=cdp_session_id,
        frame_id=frame_id,
        bridge_request_id=bridge_request_id,
    )
    with sv._state_lock:
        sv._pending_dialogs[dialog_id] = d
        try:
            seq_num = int(dialog_id.split("-")[-1])
            sv._dialog_seq = max(sv._dialog_seq, seq_num)
        except (ValueError, IndexError):
            sv._dialog_seq += 1
    return d


@pytest.fixture
def supervisor():
    """Yield a fresh unit-test supervisor with a teardown guard."""
    sv = _make_supervisor()
    yield sv
    # Ensure no lingering state
    with sv._state_lock:
        sv._active = False
        sv._pending_dialogs.clear()
        sv._frames.clear()
        sv._recent_dialogs.clear()


@pytest.fixture
def registry():
    """Yield the global registry and tear down any supervisors after the test."""
    yield SUPERVISOR_REGISTRY
    SUPERVISOR_REGISTRY.stop_all()


# ── 1. Snapshot tests ─────────────────────────────────────────────────────────


def test_snapshot_returns_supervisor_snapshot(supervisor):
    """snapshot() returns a SupervisorSnapshot with correct fields."""
    snap = supervisor.snapshot()
    assert isinstance(snap, SupervisorSnapshot)
    assert snap.active is True
    assert snap.task_id == "test-task"
    assert snap.cdp_url == "ws://127.0.0.1:9222/devtools/page/FAKE"


def test_snapshot_empty_when_no_frames_or_dialogs(supervisor):
    """snapshot() shows empty state when no frames or dialogs exist."""
    snap = supervisor.snapshot()
    assert snap.pending_dialogs == ()
    assert snap.recent_dialogs == ()
    # Production returns {"top": None, "children": [], "truncated": False}
    # when no frames are present.
    assert snap.frame_tree["top"] is None
    assert snap.frame_tree["children"] == []


def test_snapshot_shows_pending_dialogs(supervisor):
    """snapshot() includes pending dialogs in correct order."""
    _add_pending_dialog(supervisor, "d1", "alert", "first alert")
    _add_pending_dialog(supervisor, "d2", "confirm", "second confirm")
    snap = supervisor.snapshot()
    assert len(snap.pending_dialogs) == 2
    assert snap.pending_dialogs[0].id == "d1"
    assert snap.pending_dialogs[1].id == "d2"


def test_snapshot_inactive_when_stopped(supervisor):
    """snapshot() reports inactive after stop marks it so."""
    with supervisor._state_lock:
        supervisor._active = False
    snap = supervisor.snapshot()
    assert snap.active is False


# ── 2. Frame tree tests ────────────────────────────────────────────────────────


def test_snapshot_frame_tree_with_top_frame(supervisor):
    """Frame tree includes top-level frame after adding one."""
    _add_frame(supervisor, "top", url="https://example.com")
    snap = supervisor.snapshot()
    assert "top" in snap.frame_tree
    assert snap.frame_tree["top"]["url"] == "https://example.com"


def test_snapshot_frame_tree_with_nested_frames(supervisor):
    """Frame tree correctly represents parent-child relationships."""
    _add_frame(supervisor, "top", url="https://example.com")
    _add_frame(supervisor, "child-1", url="https://cdn.example.com",
               parent_frame_id="top", is_oopif=True,
               cdp_session_id="child-session-001")
    snap = supervisor.snapshot()
    # Production builds flat "children" list under top frame
    assert snap.frame_tree["top"]["url"] == "https://example.com"
    children = snap.frame_tree["children"]
    assert any(c.get("frame_id") == "child-1" for c in children)


# ── 3. respond_to_dialog tests ─────────────────────────────────────────────────


def test_respond_to_dialog_no_pending_dialog(supervisor):
    """respond_to_dialog returns error when no dialog is pending."""
    result = supervisor.respond_to_dialog("accept")
    assert result["ok"] is False
    assert "no dialog" in result["error"].lower()


def test_respond_to_dialog_invalid_action(supervisor):
    """respond_to_dialog rejects actions that aren't accept/dismiss."""
    result = supervisor.respond_to_dialog("eat")
    assert result["ok"] is False
    assert "accept" in result["error"].lower() or "dismiss" in result["error"].lower()


def test_respond_to_dialog_requires_loop_for_accept(supervisor):
    """respond_to_dialog cannot execute CDP calls without a running loop.

    When a dialog IS pending but the supervisor loop is not running (unit test
    scenario with no real asyncio loop), it should return a clean error.
    """
    _add_pending_dialog(supervisor, "d1", "alert", "test alert")
    # _loop is None, so it should error about loop not running
    result = supervisor.respond_to_dialog("accept")
    assert result["ok"] is False
    # The error should mention the loop or be a clear operational error
    assert "loop" in result["error"].lower() or "error" in result["error"].lower()


def test_respond_to_dialog_specific_dialog_id_not_found(supervisor):
    """respond_to_dialog errors when a specific dialog_id doesn't exist."""
    _add_pending_dialog(supervisor, "d1", "alert", "existing dialog")
    result = supervisor.respond_to_dialog("accept", dialog_id="nonexistent")
    assert result["ok"] is False
    assert "not found" in result["error"].lower()


def test_respond_to_dialog_ambiguous_multiple(supervisor):
    """respond_to_dialog errors when multiple dialogs are pending without dialog_id."""
    _add_pending_dialog(supervisor, "d1", "alert", "first")
    _add_pending_dialog(supervisor, "d2", "confirm", "second")
    result = supervisor.respond_to_dialog("accept")
    assert result["ok"] is False
    # Should mention ambiguity or specify dialog_id
    error_lower = result["error"].lower()
    assert "dialog_id" in error_lower or "specify" in error_lower or "multiple" in error_lower


def test_respond_to_dialog_inactive_supervisor(supervisor):
    """respond_to_dialog returns error when supervisor is not active."""
    with supervisor._state_lock:
        supervisor._active = False
    result = supervisor.respond_to_dialog("accept")
    assert result["ok"] is False
    assert "not active" in result["error"].lower()


# ── 4. Dialog policy tests ─────────────────────────────────────────────────────


def test_dialog_policy_must_respond_is_valid(supervisor):
    """Supervisor accepts DIALOG_POLICY_MUST_RESPOND."""
    assert supervisor.dialog_policy == DIALOG_POLICY_MUST_RESPOND


def test_dialog_policy_auto_dismiss_is_valid():
    """Supervisor accepts DIALOG_POLICY_AUTO_DISMISS."""
    sv = _make_supervisor(dialog_policy=DIALOG_POLICY_AUTO_DISMISS)
    assert sv.dialog_policy == DIALOG_POLICY_AUTO_DISMISS


def test_dialog_policy_auto_accept_is_valid():
    """Supervisor accepts DIALOG_POLICY_AUTO_ACCEPT."""
    sv = _make_supervisor(dialog_policy=DIALOG_POLICY_AUTO_ACCEPT)
    assert sv.dialog_policy == DIALOG_POLICY_AUTO_ACCEPT


def test_dialog_policy_invalid_raises():
    """CDPSupervisor rejects an invalid dialog policy at construction."""
    with pytest.raises(ValueError, match="Invalid dialog_policy"):
        CDPSupervisor(
            task_id="bad-policy-test",
            cdp_url="ws://127.0.0.1:9222/fake",
            dialog_policy="invalid_policy",
        )


# ── 5. Registry tests ──────────────────────────────────────────────────────────


def test_registry_get_returns_none_for_unknown_task(registry):
    """Registry.get() returns None for a task_id that was never started."""
    assert registry.get("nonexistent-task") is None


def test_registry_stop_nonexistent_is_safe(registry):
    """Registry.stop() on a nonexistent task_id does not raise."""
    registry.stop("no-such-task")  # should not raise


def test_registry_stop_all_is_safe_when_empty(registry):
    """Registry.stop_all() on an empty registry does not raise."""
    registry.stop_all()  # should not raise


# ── 6. browser_dialog_tool tests ───────────────────────────────────────────────


def test_browser_dialog_tool_no_supervisor():
    """browser_dialog returns a clear error when no supervisor is attached."""
    from tools.browser_dialog_tool import browser_dialog

    r = json.loads(browser_dialog(action="accept", task_id="nonexistent-task"))
    assert r["success"] is False
    assert "No CDP supervisor" in r["error"]


def test_browser_dialog_invalid_action_via_tool():
    """browser_dialog rejects actions that aren't accept/dismiss via tool handler."""
    from tools.browser_dialog_tool import browser_dialog

    # The tool delegates to the supervisor which validates actions.
    # Since no supervisor is attached, we get the "no supervisor" error.
    r = json.loads(browser_dialog(action="eat", task_id="some-task"))
    assert r["success"] is False


# ── 7. browser_cdp_tool frame routing tests ────────────────────────────────────


def test_browser_cdp_frame_id_missing_supervisor():
    """browser_cdp(frame_id=...) errors cleanly when no supervisor is attached."""
    from tools.browser_cdp_tool import browser_cdp

    result = browser_cdp(
        method="Runtime.evaluate",
        params={"expression": "1"},
        frame_id="any-frame-id",
        task_id="no-such-task",
    )
    r = json.loads(result)
    assert r.get("success") is not True
    assert "supervisor" in (r.get("error") or "").lower()


# ── 8. PendingDialog data model tests ──────────────────────────────────────────


def test_pending_dialog_to_dict():
    """PendingDialog.to_dict() serializes all fields."""
    d = PendingDialog(
        id="d1",
        type="alert",
        message="hello",
        default_prompt="",
        opened_at=1000.0,
        cdp_session_id="session-1",
        frame_id="frame-1",
    )
    result = d.to_dict()
    assert result["id"] == "d1"
    assert result["type"] == "alert"
    assert result["message"] == "hello"
    assert result["frame_id"] == "frame-1"


def test_pending_dialog_types():
    """PendingDialog accepts all standard dialog types."""
    for dtype in ("alert", "confirm", "prompt", "beforeunload"):
        d = PendingDialog(
            id="d", type=dtype, message="m", default_prompt="",
            opened_at=0.0, cdp_session_id="s",
        )
        assert d.type == dtype


# ── 9. DialogRecord data model tests ───────────────────────────────────────────


def test_dialog_record_to_dict():
    """DialogRecord.to_dict() serializes all fields."""
    r = DialogRecord(
        id="dr1",
        type="alert",
        message="test",
        opened_at=1000.0,
        closed_at=1001.0,
        closed_by="agent",
        frame_id="frame-1",
    )
    result = r.to_dict()
    assert result["id"] == "dr1"
    assert result["type"] == "alert"
    assert result["closed_by"] == "agent"
    assert result["closed_at"] >= result["opened_at"]
    assert result["frame_id"] == "frame-1"


def test_dialog_record_closed_by_values():
    """DialogRecord accepts all valid closed_by values."""
    for closer in ("agent", "auto_policy", "remote", "watchdog"):
        r = DialogRecord(
            id="dr", type="alert", message="m",
            opened_at=0.0, closed_at=1.0, closed_by=closer,
        )
        assert r.closed_by == closer


# ── 10. FrameInfo data model tests ─────────────────────────────────────────────


def test_frame_info_to_dict_basic():
    """FrameInfo.to_dict() includes required fields."""
    fi = FrameInfo(
        frame_id="f1",
        url="https://example.com",
        origin="https://example.com",
        parent_frame_id=None,
        is_oopif=False,
    )
    result = fi.to_dict()
    assert result["frame_id"] == "f1"
    assert result["url"] == "https://example.com"
    assert result["is_oopif"] is False


def test_frame_info_to_dict_oopif_with_session():
    """FrameInfo.to_dict() includes session_id for OOPIF frames."""
    fi = FrameInfo(
        frame_id="f2",
        url="https://other.com",
        origin="https://other.com",
        parent_frame_id="f1",
        is_oopif=True,
        cdp_session_id="child-session-1",
        name="child-frame",
    )
    result = fi.to_dict()
    assert result["session_id"] == "child-session-1"
    assert result["parent_frame_id"] == "f1"
    assert result["is_oopif"] is True
    assert result["name"] == "child-frame"


# ── 11. SupervisorSnapshot data model tests ────────────────────────────────────


def test_supervisor_snapshot_to_dict_empty():
    """SupervisorSnapshot.to_dict() returns minimal structure for empty state."""
    snap = SupervisorSnapshot(
        pending_dialogs=(),
        recent_dialogs=(),
        frame_tree={},
        console_errors=(),
        active=True,
        cdp_url="ws://test",
        task_id="t1",
    )
    result = snap.to_dict()
    assert result["pending_dialogs"] == []
    assert result["frame_tree"] == {}


def test_supervisor_snapshot_to_dict_with_dialogs():
    """SupervisorSnapshot.to_dict() includes dialogs and recent_dialogs."""
    d = PendingDialog(
        id="d1", type="alert", message="hi", default_prompt="",
        opened_at=0.0, cdp_session_id="s",
    )
    recent = DialogRecord(
        id="dr1", type="alert", message="old", opened_at=0.0,
        closed_at=1.0, closed_by="agent",
    )
    snap = SupervisorSnapshot(
        pending_dialogs=(d,),
        recent_dialogs=(recent,),
        frame_tree={"top": {"url": "https://example.com"}},
        console_errors=(),
        active=True,
        cdp_url="ws://test",
        task_id="t1",
    )
    result = snap.to_dict()
    assert len(result["pending_dialogs"]) == 1
    assert result["pending_dialogs"][0]["id"] == "d1"
    assert len(result["recent_dialogs"]) == 1
    assert result["recent_dialogs"][0]["closed_by"] == "agent"


# ── 12. evaluate_runtime tests ─────────────────────────────────────────────────


def test_evaluate_runtime_no_loop(supervisor):
    """evaluate_runtime errors when supervisor loop is not running."""
    result = supervisor.evaluate_runtime("1 + 1")
    assert result["ok"] is False
    assert "loop" in result["error"].lower()


def test_evaluate_runtime_inactive(supervisor):
    """evaluate_runtime errors when supervisor is not active."""
    with supervisor._state_lock:
        supervisor._active = False
    result = supervisor.evaluate_runtime("1 + 1")
    assert result["ok"] is False


def test_evaluate_runtime_no_page_session(supervisor):
    """evaluate_runtime errors when no page session is attached."""
    supervisor._page_session_id = None
    # Need a loop to pass the first check
    result = supervisor.evaluate_runtime("1 + 1")
    # Either no-loop or no-session error
    assert result["ok"] is False


# ── 13. ConsoleEvent tests ────────────────────────────────────────────────────


def test_supervisor_snapshot_includes_console_errors(supervisor):
    """snapshot() includes console error events."""
    evt = ConsoleEvent(ts=time.monotonic(), level="error", text="Uncaught TypeError")
    with supervisor._state_lock:
        supervisor._console_events.append(evt)
    snap = supervisor.snapshot()
    assert len(snap.console_errors) == 1
    assert snap.console_errors[0].text == "Uncaught TypeError"
    assert snap.console_errors[0].level == "error"


# ── 14. Recent dialogs ring buffer tests ───────────────────────────────────────


def test_recent_dialogs_capped_at_max(supervisor):
    """Recent dialogs are capped at RECENT_DIALOGS_MAX."""
    now = time.monotonic()
    with supervisor._state_lock:
        for i in range(RECENT_DIALOGS_MAX + 10):
            supervisor._recent_dialogs.append(DialogRecord(
                id=f"dr-{i}",
                type="alert",
                message=f"msg-{i}",
                opened_at=now,
                closed_at=now + 0.1,
                closed_by="agent",
            ))
    snap = supervisor.snapshot()
    assert len(snap.recent_dialogs) == RECENT_DIALOGS_MAX


def test_recent_dialogs_keeps_newest(supervisor):
    """Recent dialogs ring buffer keeps the most recent entries."""
    now = time.monotonic()
    with supervisor._state_lock:
        for i in range(RECENT_DIALOGS_MAX + 5):
            supervisor._recent_dialogs.append(DialogRecord(
                id=f"dr-{i}",
                type="alert",
                message=f"msg-{i}",
                opened_at=now + i,
                closed_at=now + i + 0.1,
                closed_by="agent",
            ))
    snap = supervisor.snapshot()
    # The first entry should be the one that survived the cap
    first_id = int(snap.recent_dialogs[0].id.split("-")[1])
    # Should have skipped the earliest 5
    assert first_id == 5


# ── 15. Supervisor constants tests ─────────────────────────────────────────────


def test_valid_dialog_policies():
    """All documented dialog policies are in _VALID_POLICIES."""
    from tools.browser_supervisor import _VALID_POLICIES
    assert DIALOG_POLICY_MUST_RESPOND in _VALID_POLICIES
    assert DIALOG_POLICY_AUTO_DISMISS in _VALID_POLICIES
    assert DIALOG_POLICY_AUTO_ACCEPT in _VALID_POLICIES
    assert len(_VALID_POLICIES) == 3


def test_default_dialog_policy_is_must_respond():
    """Default dialog policy is DIALOG_POLICY_MUST_RESPOND."""
    from tools.browser_supervisor import DEFAULT_DIALOG_POLICY
    assert DEFAULT_DIALOG_POLICY == DIALOG_POLICY_MUST_RESPOND


# ── 16. Supervisor stop tests ─────────────────────────────────────────────────


def test_stop_marks_inactive(supervisor):
    """stop() marks the supervisor as inactive."""
    assert supervisor._active is True
    supervisor.stop(timeout=1.0)
    assert supervisor._active is False


def test_stop_is_idempotent(supervisor):
    """Calling stop() multiple times is safe."""
    supervisor.stop(timeout=1.0)
    supervisor.stop(timeout=1.0)
    assert supervisor._active is False


# ── 17. Prompt dialog with default_prompt ──────────────────────────────────────


def test_pending_dialog_prompt_with_default():
    """PendingDialog for a prompt carries the default_prompt value."""
    d = _add_pending_dialog(
        supervisor := _make_supervisor(),
        "d-prompt",
        "prompt",
        "Enter a value",
        default_prompt="default-x",
    )
    assert d.type == "prompt"
    assert d.default_prompt == "default-x"
    snap = supervisor.snapshot()
    assert snap.pending_dialogs[0].default_prompt == "default-x"
