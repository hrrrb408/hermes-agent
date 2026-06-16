"""Phase 3A-H1 — Workflow store hardening (Lens 2: State Persistence Boundary).

Adversarial boundary tests for the dev-only file-backed store: it is confined
to the dev HERMES_HOME (never the repo / ``~/.hermes`` / production), writes are
atomic, the timeline is append-only and corruption-safe, oversized and malformed
documents are rejected, the listing is bounded and skips corrupt entries, and
no persisted document ever carries a raw token / hash / secret / file content /
callable repr / absolute path.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hermes_cli.dev_web_workflow_schema import (
    STEP_READ_ONLY_TOOL,
    WORKFLOW_SAFETY_BOUNDARY,
    WORKFLOW_SCHEMA_VERSION,
    WorkflowDefinition,
    WorkflowExecutionState,
    WorkflowStep,
    WorkflowTimelineEvent,
    new_workflow_id,
)
from hermes_cli.dev_web_workflow_store import (
    ERROR_CORRUPT_DOCUMENT,
    ERROR_HOME_PRODUCTION,
    ERROR_HOME_REPO,
    ERROR_HOME_UNSET,
    append_workflow_timeline_event,
    ensure_workflow_store,
    get_workflow_store_root,
    list_workflow_executions,
    load_workflow_definition,
    load_workflow_execution,
    save_workflow_definition,
    save_workflow_execution,
    validate_workflow_store_root,
)


@pytest.fixture
def dev_home(tmp_path: Path) -> str:
    home = tmp_path / "hermes-home-dev"
    home.mkdir()
    return str(home)


def _step(step_type: str = STEP_READ_ONLY_TOOL) -> WorkflowStep:
    return WorkflowStep(
        step_id=new_workflow_id("wfs_"),
        step_type=step_type,
        title="Read env",
        tool_id="dev_environment_read",
    )


def _definition(dev_home: str, **overrides: object) -> WorkflowDefinition:
    base: dict[str, object] = {
        "workflow_id": new_workflow_id("wf_"),
        "schema_version": WORKFLOW_SCHEMA_VERSION,
        "title": "Demo",
        "description": None,
        "created_at": "2026-06-16T00:00:00+00:00",
        "updated_at": "2026-06-16T00:00:00+00:00",
        "created_by": "dev-webui",
        "phase": "3A",
        "mode": "dev_workflow_mvp",
        "steps": (_step(),),
        "safety_boundary": WORKFLOW_SAFETY_BOUNDARY,
    }
    base.update(overrides)
    return WorkflowDefinition(**base)  # type: ignore[arg-type]


def _execution(dev_home: str, steps: tuple[WorkflowStep, ...] | None = None) -> WorkflowExecutionState:
    return WorkflowExecutionState(
        workflow_execution_id=new_workflow_id("wfx_"),
        workflow_id=new_workflow_id("wf_"),
        workflow_plan_id=new_workflow_id("wfp_"),
        schema_version=WORKFLOW_SCHEMA_VERSION,
        title="Demo",
        status="running",
        steps=steps or (_step(),),
        cursor_step_id=(steps or (_step(),))[0].step_id,
        safety_boundary=WORKFLOW_SAFETY_BOUNDARY,
        created_at="2026-06-16T00:00:00+00:00",
        updated_at="2026-06-16T00:00:00+00:00",
        total_step_count=len(steps or (_step(),)),
    )


# ---------------------------------------------------------------------------
# 1. Confinement boundary
# ---------------------------------------------------------------------------


class TestConfinement:
    def test_store_root_is_under_dev_home_with_four_subdirs(self, dev_home: str) -> None:
        root, err = ensure_workflow_store(dev_home)
        assert err is None
        assert str(root).startswith(dev_home)
        assert "workflow-store" in str(root)
        for sub in ("workflows", "executions", "timelines", "meta"):
            assert (root / sub).is_dir()

    def test_get_root_does_not_create_dirs(self, dev_home: str) -> None:
        root = get_workflow_store_root(dev_home)
        assert str(root).startswith(dev_home)
        assert not root.exists()  # get_workflow_store_root is non-mutating.

    def test_store_rejects_repo_root(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        assert validate_workflow_store_root(repo_root) == ERROR_HOME_REPO
        # A path *inside* the repo is also rejected.
        assert validate_workflow_store_root(repo_root / "subdir") == ERROR_HOME_REPO

    def test_store_rejects_production_home(self) -> None:
        assert validate_workflow_store_root(Path("/Users/huangruibang/.hermes")) == ERROR_HOME_PRODUCTION

    def test_store_rejects_unset_home(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("HERMES_HOME", raising=False)
        root, err = ensure_workflow_store(None)
        assert err == ERROR_HOME_UNSET
        assert root == Path()

    def test_store_rejects_production_home_on_ensure(self) -> None:
        root, err = ensure_workflow_store("/Users/huangruibang/.hermes")
        assert err == ERROR_HOME_PRODUCTION
        assert root == Path()


# ---------------------------------------------------------------------------
# 2. Atomic write + round-trip
# ---------------------------------------------------------------------------


class TestAtomicWriteAndRoundTrip:
    def test_definition_round_trips(self, dev_home: str) -> None:
        d = _definition(dev_home, description="d")
        assert save_workflow_definition(d, hermes_home=dev_home).ok
        loaded = load_workflow_definition(d.workflow_id, hermes_home=dev_home)
        assert loaded is not None
        assert loaded.title == "Demo"
        assert loaded.description == "d"
        assert len(loaded.steps) == 1

    def test_definition_overwrite_is_atomic(self, dev_home: str) -> None:
        d = _definition(dev_home, title="First")
        save_workflow_definition(d, hermes_home=dev_home)
        d2 = _definition(
            dev_home, workflow_id=d.workflow_id, title="Second"
        )
        save_workflow_definition(d2, hermes_home=dev_home)
        loaded = load_workflow_definition(d.workflow_id, hermes_home=dev_home)
        assert loaded is not None
        assert loaded.title == "Second"

    def test_execution_round_trips_with_merged_timeline(self, dev_home: str) -> None:
        st = _execution(dev_home)
        save_workflow_execution(st, hermes_home=dev_home)
        for kind in ("workflow_step_started", "workflow_step_completed"):
            ev = WorkflowTimelineEvent(
                event_id=new_workflow_id("wfa_"),
                event_type=kind,
                created_at="2026-06-16T00:00:00+00:00",
                step_id=st.steps[0].step_id,
                step_type=STEP_READ_ONLY_TOOL,
                message=kind,
            )
            append_workflow_timeline_event(st.workflow_execution_id, ev, hermes_home=dev_home)
        loaded = load_workflow_execution(st.workflow_execution_id, hermes_home=dev_home)
        assert loaded is not None
        assert [e.event_type for e in loaded.timeline] == [
            "workflow_step_started",
            "workflow_step_completed",
        ]

    def test_missing_definition_returns_none(self, dev_home: str) -> None:
        assert load_workflow_definition("wf_" + "0" * 20, hermes_home=dev_home) is None

    def test_missing_execution_returns_none(self, dev_home: str) -> None:
        assert load_workflow_execution("wfx_" + "0" * 20, hermes_home=dev_home) is None


# ---------------------------------------------------------------------------
# 3. Corruption safety
# ---------------------------------------------------------------------------


class TestCorruptionSafety:
    def test_corrupt_definition_json_returns_none(self, dev_home: str) -> None:
        d = _definition(dev_home)
        save_workflow_definition(d, hermes_home=dev_home)
        path = get_workflow_store_root(dev_home) / "workflows" / f"{d.workflow_id}.json"
        path.write_text("{ not valid json", encoding="utf-8")
        assert load_workflow_definition(d.workflow_id, hermes_home=dev_home) is None

    def test_corrupt_execution_json_returns_none(self, dev_home: str) -> None:
        st = _execution(dev_home)
        save_workflow_execution(st, hermes_home=dev_home)
        path = get_workflow_store_root(dev_home) / "executions" / f"{st.workflow_execution_id}.json"
        path.write_text("}}}} not json {{{", encoding="utf-8")
        assert load_workflow_execution(st.workflow_execution_id, hermes_home=dev_home) is None

    def test_non_object_json_returns_none(self, dev_home: str) -> None:
        st = _execution(dev_home)
        save_workflow_execution(st, hermes_home=dev_home)
        path = get_workflow_store_root(dev_home) / "executions" / f"{st.workflow_execution_id}.json"
        path.write_text("[1, 2, 3]", encoding="utf-8")
        assert load_workflow_execution(st.workflow_execution_id, hermes_home=dev_home) is None

    def test_corrupt_timeline_line_is_skipped(self, dev_home: str) -> None:
        st = _execution(dev_home)
        save_workflow_execution(st, hermes_home=dev_home)
        path = get_workflow_store_root(dev_home) / "timelines" / f"{st.workflow_execution_id}.jsonl"
        # One good line, one corrupt line, one good line.
        good = WorkflowTimelineEvent(
            event_id=new_workflow_id("wfa_"), event_type="workflow_step_started",
            created_at="2026-06-16T00:00:00+00:00", message="a",
        )
        append_workflow_timeline_event(st.workflow_execution_id, good, hermes_home=dev_home)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write("{ this line is corrupt }\n")
        good2 = WorkflowTimelineEvent(
            event_id=new_workflow_id("wfa_"), event_type="workflow_step_completed",
            created_at="2026-06-16T00:00:00+00:00", message="b",
        )
        append_workflow_timeline_event(st.workflow_execution_id, good2, hermes_home=dev_home)
        loaded = load_workflow_execution(st.workflow_execution_id, hermes_home=dev_home)
        assert loaded is not None
        # Two good events survive; the corrupt line is skipped, not fatal.
        assert [e.message for e in loaded.timeline] == ["a", "b"]

    def test_symlinked_document_refused(self, dev_home: str) -> None:
        st = _execution(dev_home)
        save_workflow_execution(st, hermes_home=dev_home)
        path = get_workflow_store_root(dev_home) / "executions" / f"{st.workflow_execution_id}.json"
        target = dev_home + "/evil.json"
        Path(target).write_text('{"workflowExecutionId": "evil"}', encoding="utf-8")
        path.unlink()
        try:
            path.symlink_to(target)
        except OSError:
            pytest.skip("symlink creation not supported on this platform")
        # A symlinked document is treated as unreadable → None.
        assert load_workflow_execution(st.workflow_execution_id, hermes_home=dev_home) is None


# ---------------------------------------------------------------------------
# 4. Input rejection (bad ids / oversized documents)
# ---------------------------------------------------------------------------


class TestInputRejection:
    def test_save_rejects_invalid_workflow_id(self, dev_home: str) -> None:
        d = _definition(dev_home, workflow_id="bad_id")
        r = save_workflow_definition(d, hermes_home=dev_home)
        assert not r.ok
        assert r.error_code == ERROR_CORRUPT_DOCUMENT

    def test_save_rejects_invalid_execution_id(self, dev_home: str) -> None:
        st = _execution(dev_home)
        bad = WorkflowExecutionState(
            workflow_execution_id="bad_id",
            workflow_id=st.workflow_id, workflow_plan_id=st.workflow_plan_id,
            schema_version=st.schema_version, title=st.title, status=st.status,
            steps=st.steps, cursor_step_id=st.cursor_step_id,
            safety_boundary=st.safety_boundary, created_at=st.created_at,
            updated_at=st.updated_at, total_step_count=st.total_step_count,
        )
        r = save_workflow_execution(bad, hermes_home=dev_home)
        assert not r.ok

    def test_oversized_definition_rejected(self, dev_home: str) -> None:
        # A pathologically long title would exceed the 256 KiB document cap if
        # it survived sanitization. We inject a huge metadata value instead.
        huge = {"k" + str(i): "v" * 4000 for i in range(400)}
        d = _definition(
            dev_home, description=None,
        )
        # Bypass the description bound via metadata (the store round-trips it).
        from hermes_cli.dev_web_workflow_schema import WorkflowDefinition as WD

        d2 = WD(
            workflow_id=d.workflow_id, schema_version=d.schema_version,
            title=d.title, description=None, created_at=d.created_at,
            updated_at=d.updated_at, created_by=d.created_by, phase=d.phase,
            mode=d.mode, steps=d.steps, safety_boundary=d.safety_boundary,
            metadata=huge,
        )
        r = save_workflow_definition(d2, hermes_home=dev_home)
        assert not r.ok  # the 256 KiB cap rejects the oversized document


# ---------------------------------------------------------------------------
# 5. Listing bounds + corrupt-skip
# ---------------------------------------------------------------------------


class TestListing:
    def test_list_bounds_limit_to_max(self, dev_home: str) -> None:
        for _ in range(3):
            save_workflow_execution(_execution(dev_home), hermes_home=dev_home)
        items = list_workflow_executions(limit=500, hermes_home=dev_home)
        assert len(items) <= 100  # _MAX_LIST_LIMIT cap
        assert len(items) == 3

    def test_list_clamps_invalid_limit(self, dev_home: str) -> None:
        save_workflow_execution(_execution(dev_home), hermes_home=dev_home)
        # 0 and negative limits clamp to >=1 (the API guards None upstream).
        for bad in (0, -1):
            items = list_workflow_executions(limit=bad, hermes_home=dev_home)
            assert isinstance(items, list)
            assert len(items) == 1

    def test_list_skips_corrupt_documents(self, dev_home: str) -> None:
        st = _execution(dev_home)
        save_workflow_execution(st, hermes_home=dev_home)
        root = get_workflow_store_root(dev_home)
        # Drop a corrupt .json file next to the good one.
        (root / "executions" / "wfx_corrupt000000000000000.json").write_text(
            "{ broken", encoding="utf-8"
        )
        items = list_workflow_executions(limit=50, hermes_home=dev_home)
        ids = [i["workflowExecutionId"] for i in items]
        assert st.workflow_execution_id in ids
        # The corrupt entry is skipped, not surfaced.
        assert "wfx_corrupt000000000000000" not in ids


# ---------------------------------------------------------------------------
# 6. No-leak on persisted documents
# ---------------------------------------------------------------------------


FORBIDDEN_CARRIERS = (
    "rawArguments", "rawArgs", "fullTokenHash", "tokenSecret",
    "plainToken", "rawToken", "apiKey", "fileContent", "absolutePath",
    "<function", "object at 0x",
)


class TestNoLeakOnDisk:
    def test_persisted_definition_has_no_secret_carriers(self, dev_home: str) -> None:
        d = _definition(dev_home, description="d")
        save_workflow_definition(d, hermes_home=dev_home)
        blob = (get_workflow_store_root(dev_home) / "workflows" / f"{d.workflow_id}.json").read_text("utf-8")
        for carrier in FORBIDDEN_CARRIERS:
            assert carrier not in blob, carrier

    def test_persisted_execution_has_no_secret_carriers(self, dev_home: str) -> None:
        st = _execution(dev_home)
        save_workflow_execution(st, hermes_home=dev_home)
        blob = (get_workflow_store_root(dev_home) / "executions" / f"{st.workflow_execution_id}.json").read_text("utf-8")
        for carrier in FORBIDDEN_CARRIERS:
            assert carrier not in blob, carrier

    def test_timeline_jsonl_has_no_secret_carriers(self, dev_home: str) -> None:
        st = _execution(dev_home)
        save_workflow_execution(st, hermes_home=dev_home)
        ev = WorkflowTimelineEvent(
            event_id=new_workflow_id("wfa_"), event_type="workflow_step_started",
            created_at="2026-06-16T00:00:00+00:00", message="started",
        )
        append_workflow_timeline_event(st.workflow_execution_id, ev, hermes_home=dev_home)
        blob = (get_workflow_store_root(dev_home) / "timelines" / f"{st.workflow_execution_id}.jsonl").read_text("utf-8")
        for carrier in FORBIDDEN_CARRIERS:
            assert carrier not in blob, carrier

    def test_no_production_path_persisted(self, dev_home: str) -> None:
        st = _execution(dev_home)
        save_workflow_execution(st, hermes_home=dev_home)
        blob = (get_workflow_store_root(dev_home) / "executions" / f"{st.workflow_execution_id}.json").read_text("utf-8")
        assert "/Users/huangruibang/.hermes" not in blob
        assert "state.db" not in blob

    def test_documents_are_valid_json(self, dev_home: str) -> None:
        d = _definition(dev_home)
        save_workflow_definition(d, hermes_home=dev_home)
        st = _execution(dev_home)
        save_workflow_execution(st, hermes_home=dev_home)
        root = get_workflow_store_root(dev_home)
        def_blob = (root / "workflows" / f"{d.workflow_id}.json").read_text("utf-8")
        exec_blob = (root / "executions" / f"{st.workflow_execution_id}.json").read_text("utf-8")
        # Both round-trip through the real JSON parser.
        assert isinstance(json.loads(def_blob), dict)
        assert isinstance(json.loads(exec_blob), dict)
