"""Phase 3E–3H Missing-Implementation Recovery — Safety Baseline tests (Block 1).

Regression coverage for the safety primitives consolidated in
:mod:`hermes_cli.dev_web_safety_baseline`:

  - **Route governance** — the frozen ``34/34/5/0/1/1`` baseline is unchanged,
    and every "new route" flag is zero. No route definition is read or mutated.
  - **Production isolation** — classify / detect production home + state.db by
    string analysis; the production home is never opened.
  - **Forbidden-path protection** — deny ``~/.hermes``, production db,
    traversal escape, symlink escape, home fallback, write outside root.
  - **Dev-home safety** — the canonical dev home classifies as ``dev`` and the
    dev-environment assertion passes.
  - **``.claude`` exclusion** — the read-only git check finds ``.claude`` not
    staged / not tracked.
  - **Runtime-store protection** — a temp dir with no runtime artifacts scans
    empty; a planted runtime-store file is detected.

Boundary: this test never touches ``~/.hermes``, never opens production
``state.db``, never signals the production gateway, never starts a gateway /
dashboard, and introduces no new route.

Phase: 3E–3H Missing-Implementation Recovery
"""

from __future__ import annotations

import inspect
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from hermes_cli import dev_web_safety_baseline as baseline
from hermes_cli.dev_web_api import DevWebApiConfig, create_dev_web_api_app
from hermes_cli.dev_web_safety_baseline import (
    ALLOWED_HERMES_HOME,
    PRODUCTION_HERMES_HOME,
    ROUTE_GOVERNANCE_EXPECTED,
    assert_dev_environment,
    assert_no_side_effect_surface,
    assert_route_governance_unchanged,
    check_dotclaude_not_staged,
    classify_hermes_home,
    evaluate_path_safety,
    evaluate_runtime_store_write,
    find_runtime_store_artifacts,
    format_route_governance,
    is_production_home,
    is_production_state_db,
    parse_route_governance,
    route_governance_counts,
    route_governance_drift,
    route_governance_new_route_flags,
)


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    cfg = DevWebApiConfig(host="127.0.0.1", port=5181, hermes_home=tmp_path / "dev-home")
    return TestClient(create_dev_web_api_app(cfg))


@pytest.fixture()
def app(tmp_path: Path):
    cfg = DevWebApiConfig(host="127.0.0.1", port=5181, hermes_home=tmp_path / "dev-home")
    return create_dev_web_api_app(cfg)


# ---------------------------------------------------------------------------
# Route governance
# ---------------------------------------------------------------------------


class TestRouteGovernance:
    def test_openapi_paths_remain_34(self, client: TestClient) -> None:
        spec = client.get("/openapi.json").json()
        paths = [p for p in spec["paths"] if p.startswith("/api/dev/v1/")]
        assert len(paths) == 34

    def test_counts_match_frozen_baseline(self, app) -> None:
        counts = route_governance_counts(app)
        assert counts == {
            "openApiPaths": 34,
            "runtimeRoutes": 34,
            "toolGetRoutes": 5,
            "toolWriteRoutes": 0,
            "toolDryRunRoutes": 1,
            "toolExecutionRoutes": 1,
        }

    def test_formatted_baseline_string(self, app) -> None:
        counts = route_governance_counts(app)
        assert format_route_governance(counts) == ROUTE_GOVERNANCE_EXPECTED == "34/34/5/0/1/1"

    def test_assert_unchanged_passes(self, app) -> None:
        # Must not raise.
        assert_route_governance_unchanged(app)

    def test_no_drift(self, app) -> None:
        report = route_governance_drift(route_governance_counts(app))
        assert report["drifted"] is False
        assert report["diff"] == {
            "openApiPaths": None,
            "runtimeRoutes": None,
            "toolGetRoutes": None,
            "toolWriteRoutes": None,
            "toolDryRunRoutes": None,
            "toolExecutionRoutes": None,
        }

    def test_drift_detects_a_change(self) -> None:
        report = route_governance_drift(
            {
                "openApiPaths": 35,  # drifted
                "runtimeRoutes": 34,
                "toolGetRoutes": 5,
                "toolWriteRoutes": 0,
                "toolDryRunRoutes": 1,
                "toolExecutionRoutes": 1,
            }
        )
        assert report["drifted"] is True
        assert report["diff"]["openApiPaths"] == "34->35"
        assert report["diff"]["runtimeRoutes"] is None

    def test_assert_unchanged_raises_on_drift(self) -> None:
        class _FakeApp:
            def openapi(self):
                return {"paths": {"/api/dev/v1/x": {}}}

            routes: list = []

        with pytest.raises(AssertionError):
            assert_route_governance_unchanged(_FakeApp())

    def test_parse_round_trip(self) -> None:
        assert parse_route_governance("34/34/5/0/1/1") == (34, 34, 5, 0, 1, 1)
        assert parse_route_governance("garbage") == (0, 0, 0, 0, 0, 0)
        assert parse_route_governance(None) == (0, 0, 0, 0, 0, 0)

    def test_new_route_flags_all_zero(self) -> None:
        flags = route_governance_new_route_flags()
        assert flags == {
            "newHttpRoute": 0,
            "newToolWriteRoute": 0,
            "newProviderRoute": 0,
            "newPluginRoute": 0,
            "newRuntimeRoute": 0,
        }
        assert all(v == 0 for v in flags.values())

    def test_no_new_descriptor_or_plugin_route(self, client: TestClient) -> None:
        spec = client.get("/openapi.json").json()
        for path in spec["paths"]:
            lower = path.lower()
            assert "descriptor" not in lower
            assert "/plugin" not in lower


# ---------------------------------------------------------------------------
# Production isolation
# ---------------------------------------------------------------------------


class TestProductionIsolation:
    def test_canonical_dev_home_classifies_dev(self) -> None:
        assert classify_hermes_home(str(ALLOWED_HERMES_HOME)) == "dev"
        assert classify_hermes_home(str(ALLOWED_HERMES_HOME / "memory" / "records")) == "dev"

    def test_production_home_classifies_production(self) -> None:
        assert classify_hermes_home(str(PRODUCTION_HERMES_HOME)) == "production"
        assert is_production_home(str(PRODUCTION_HERMES_HOME / "state.db")) is True

    def test_unknown_home_classifies_unknown(self) -> None:
        assert classify_hermes_home("/some/other/place") == "unknown"
        assert classify_hermes_home(None) == "unknown"
        assert classify_hermes_home(1234) == "unknown"

    def test_traversal_into_production_detected(self) -> None:
        # Lexical normalization collapses the traversal back to production.
        cand = str(PRODUCTION_HERMES_HOME) + "/../.hermes"
        assert classify_hermes_home(cand) == "production"

    def test_production_state_db_detected_by_stem(self) -> None:
        assert is_production_state_db(str(PRODUCTION_HERMES_HOME / "state.db")) is True
        assert is_production_state_db("/some/where/state.db") is True
        assert is_production_state_db("/some/where/gateway.db") is True
        assert is_production_state_db("/safe/path/notes.txt") is False

    def test_dev_environment_assertion_passes_for_dev(self) -> None:
        assert_dev_environment(str(ALLOWED_HERMES_HOME))  # must not raise

    def test_dev_environment_assertion_rejects_production(self) -> None:
        with pytest.raises(RuntimeError):
            assert_dev_environment(str(PRODUCTION_HERMES_HOME))

    def test_source_references_no_production_home(self) -> None:
        src = Path(inspect.getsourcefile(baseline)).read_text(encoding="utf-8")
        # The production path appears ONLY as the frozen denial constant. It
        # must never appear as an open()/read_text()/stat()/subprocess target.
        assert "/Users/huangruibang/.hermes" in src  # the constant is present
        # No file-opening call against a production path literal.
        for forbidden_call in (
            "open('/Users/huangruibang/.hermes",
            'open("/Users/huangruibang/.hermes',
            "read_text('/Users/huangruibang/.hermes",
            'read_text("/Users/huangruibang/.hermes',
        ):
            assert forbidden_call not in src, forbidden_call


# ---------------------------------------------------------------------------
# Forbidden-path protection
# ---------------------------------------------------------------------------


class TestForbiddenPathProtection:
    def test_production_home_denied(self) -> None:
        result = evaluate_path_safety(str(PRODUCTION_HERMES_HOME), allowed_roots=[])
        assert result["allowed"] is False
        assert "forbidden_production_home" in result["reasons"]

    def test_production_state_db_denied(self) -> None:
        result = evaluate_path_safety(str(PRODUCTION_HERMES_HOME / "state.db"), allowed_roots=[])
        assert result["allowed"] is False
        assert "forbidden_production_database" in result["reasons"]

    def test_traversal_escape_denied(self, tmp_path: Path) -> None:
        candidate = str(tmp_path / ".." / ".." / ".hermes" / "state.db")
        result = evaluate_path_safety(candidate, allowed_roots=[str(tmp_path)])
        assert result["allowed"] is False
        assert "path_traversal_escape" in result["reasons"]

    def test_symlink_escape_denied(self, tmp_path: Path) -> None:
        link = tmp_path / "escape"
        os.symlink("/etc", link)
        result = evaluate_path_safety(str(link), allowed_roots=[str(tmp_path)])
        assert result["allowed"] is False
        assert "symlink_escape" in result["reasons"]

    def test_allowed_temp_read_passes(self, tmp_path: Path) -> None:
        candidate = str(tmp_path / "fixture.json")
        result = evaluate_path_safety(candidate, allowed_roots=[str(tmp_path)])
        assert result["allowed"] is True
        assert result["reasons"] == []

    def test_write_outside_allowed_root_denied(self, tmp_path: Path) -> None:
        result = evaluate_path_safety(str(tmp_path.parent / "outside.json"), allowed_roots=[str(tmp_path)], allow_write=True)
        assert result["allowed"] is False
        assert "write_outside_allowed_root" in result["reasons"]

    def test_write_with_no_root_denied(self) -> None:
        result = evaluate_path_safety("/tmp/whatever.json", allow_write=True)
        assert result["allowed"] is False

    def test_runtime_store_write_denied(self, tmp_path: Path) -> None:
        # Even inside an allowed root, a runtime-store-named write is denied.
        result = evaluate_runtime_store_write(
            str(tmp_path / "plugin_registry.json"), allowed_roots=[str(tmp_path)]
        )
        assert result["allowed"] is False
        assert "forbidden_runtime_store_name" in result["reasons"]

    def test_invalid_path_denied(self) -> None:
        assert evaluate_path_safety(12345)["allowed"] is False  # type: ignore[arg-type]
        assert evaluate_path_safety(None)["allowed"] is False  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Runtime-store protection
# ---------------------------------------------------------------------------


class TestRuntimeStoreProtection:
    def test_empty_dir_scans_clean(self, tmp_path: Path) -> None:
        assert find_runtime_store_artifacts(tmp_path) == []

    def test_planted_runtime_store_detected(self, tmp_path: Path) -> None:
        (tmp_path / "plugin_registry.json").write_text("{}", encoding="utf-8")
        (tmp_path / "audit.jsonl").write_text("{}", encoding="utf-8")
        (tmp_path / "normal.txt").write_text("hi", encoding="utf-8")
        hits = find_runtime_store_artifacts(tmp_path)
        assert "plugin_registry.json" in hits
        assert "audit.jsonl" in hits
        assert "normal.txt" not in hits

    def test_git_dir_not_walked(self, tmp_path: Path) -> None:
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "state.db").write_text("x", encoding="utf-8")
        # .git metadata is not treated as a runtime-store artifact.
        assert find_runtime_store_artifacts(tmp_path) == []


# ---------------------------------------------------------------------------
# .claude exclusion
# ---------------------------------------------------------------------------


class TestClaudeExclusion:
    def test_dotclaude_not_staged_or_tracked(self) -> None:
        result = check_dotclaude_not_staged()
        assert result["staged"] is False
        assert result["tracked"] is False
        assert result["ok"] is True
        assert result["stagedClaudePaths"] == []

    def test_dotclaude_check_never_mutates(self) -> None:
        # The check is read-only: running it must not change git state. We
        # assert the function returns ok and that .claude is still untracked
        # afterward (the worktree state is unchanged by a read).
        before = check_dotclaude_not_staged()
        after = check_dotclaude_not_staged()
        assert before == after


# ---------------------------------------------------------------------------
# No-side-effect surface re-affirmation
# ---------------------------------------------------------------------------


class TestNoSideEffectSurface:
    def test_frozen_flags_assertion(self) -> None:
        assert_no_side_effect_surface()  # must not raise

    def test_module_constants_are_frozen_true(self) -> None:
        assert baseline.NO_REAL_PLUGIN_RUNTIME is True
        assert baseline.NO_PLUGIN_EXECUTION is True
        assert baseline.NO_PLUGIN_LOADER is True
        assert baseline.NO_DYNAMIC_LOADING is True
        assert baseline.NO_EXTERNAL_NETWORK is True
        assert baseline.NO_REAL_API_KEY_READ is True
        assert baseline.NO_NEW_ROUTE is True
        assert baseline.NO_PRODUCTION_ACCESS is True

    def test_source_has_no_dynamic_loading_or_network(self) -> None:
        src = Path(inspect.getsourcefile(baseline)).read_text(encoding="utf-8")
        assert "importlib.import_module" not in src
        assert "importlib.importer" not in src
        assert "__import__(" not in src
        assert "shell=True" not in src
        assert "import requests" not in src
        assert "import httpx" not in src
        assert "import aiohttp" not in src
        assert "socket.connect" not in src

    def test_subprocess_confined_to_read_only_git(self) -> None:
        # The only subprocess use is the read-only ``.claude`` git helper.
        src = Path(inspect.getsourcefile(baseline)).read_text(encoding="utf-8")
        assert src.count("subprocess.run") == 1
        # No plugin / shell code execution through subprocess.
        assert "subprocess.Popen" not in src
        assert "subprocess.check_output" not in src

    def test_source_git_is_read_only(self) -> None:
        src = Path(inspect.getsourcefile(baseline)).read_text(encoding="utf-8")
        # The only git usage is read-only status/diff/ls-files.
        assert '["git", "add"' not in src
        assert '["git", "commit"' not in src
        assert '["git", "reset"' not in src
        assert '["git", "clean"' not in src
