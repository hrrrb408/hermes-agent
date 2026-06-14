"""Phase 2C — Write sandbox security + IO tests.

Verifies the dev sandbox root resolution, path validation (traversal /
absolute / symlink escape / forbidden targets / file type), size limits,
binary rejection, and the safe IO primitives (write / append / patch /
readback). All writes must occur ONLY inside the sandbox root.

Phase: 2C — Controlled Tool Write Execution (Dev Sandbox Write MVP)
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from hermes_cli.dev_web_write_sandbox import (
    PRODUCTION_HERMES_HOME,
    SANDBOX_DIR_RELATIVE,
    ERROR_ABSOLUTE_PATH,
    ERROR_BINARY_CONTENT,
    ERROR_CONTENT_TOO_LARGE,
    ERROR_DEV_HOME_PRODUCTION,
    ERROR_DEV_HOME_UNSET,
    ERROR_FILE_TOO_LARGE,
    ERROR_FILENAME_TOO_LONG,
    ERROR_FILE_TYPE,
    ERROR_FORBIDDEN_PATH,
    ERROR_PATH_TOO_DEEP,
    ERROR_PATH_TRAVERSAL,
    ERROR_SYMLINK_ESCAPE,
    MAX_FILE_AFTER_WRITE_BYTES,
    MAX_FILENAME_LENGTH,
    MAX_PATH_DEPTH,
    MAX_SINGLE_WRITE_BYTES,
    build_diff_preview,
    canonicalize_sandbox_target_path,
    compute_sha256_text,
    ensure_dev_write_sandbox_root,
    get_dev_write_sandbox_root,
    readback_summary,
    safe_append_text,
    safe_apply_patch,
    safe_read_text,
    safe_write_text,
    validate_allowed_file_type,
    validate_file_size_limits,
    validate_no_symlink_escape,
    validate_sandbox_target_path,
)


@pytest.fixture
def dev_home(tmp_path: Path, monkeypatch) -> str:
    home = tmp_path / "hermes-home-dev"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    return str(home)


# ---------------------------------------------------------------------------
# 1. Sandbox root resolution
# ---------------------------------------------------------------------------


class TestSandboxRoot:
    def test_root_under_hermes_home(self, dev_home: str) -> None:
        root, err = get_dev_write_sandbox_root(dev_home)
        assert err is None
        assert str(root).endswith(SANDBOX_DIR_RELATIVE.replace("/", os.sep))
        assert str(root).startswith(dev_home)

    def test_root_uses_env_when_arg_none(self, dev_home: str) -> None:
        root, err = get_dev_write_sandbox_root(None)
        assert err is None
        assert str(root).startswith(dev_home)

    def test_production_home_blocked(self) -> None:
        root, err = get_dev_write_sandbox_root(PRODUCTION_HERMES_HOME)
        assert err == ERROR_DEV_HOME_PRODUCTION
        assert root == Path()

    def test_unset_home_blocked(self, monkeypatch) -> None:
        monkeypatch.delenv("HERMES_HOME", raising=False)
        root, err = get_dev_write_sandbox_root(None)
        assert err == ERROR_DEV_HOME_UNSET

    def test_ensure_creates_root(self, dev_home: str) -> None:
        root, err = ensure_dev_write_sandbox_root(dev_home)
        assert err is None
        assert root.exists()
        assert root.is_dir()


# ---------------------------------------------------------------------------
# 2. Target path validation
# ---------------------------------------------------------------------------


class TestPathValidation:
    @pytest.mark.parametrize(
        "rel,expected_err",
        [
            ("../escape.md", ERROR_PATH_TRAVERSAL),
            ("notes/../../escape.md", ERROR_PATH_TRAVERSAL),
            ("/etc/passwd", ERROR_ABSOLUTE_PATH),
            ("~/secret.md", ERROR_ABSOLUTE_PATH),
            ("back\\slash.md", ERROR_PATH_TRAVERSAL),
        ],
    )
    def test_unsafe_paths_blocked(self, dev_home: str, rel: str, expected_err: str) -> None:
        ok, err, _ = validate_sandbox_target_path(rel, dev_home)
        assert ok is False
        assert err == expected_err

    @pytest.mark.parametrize(
        "rel",
        [
            "bad/.env",
            "secret.db",
            "data/state.sqlite",
            "a/x.jsonl",
            "logs/run.log",
            "nested/.claude/notes.md",
            "repo/.git/config",
            "out/test-results/x.md",
            "out/playwright-report/x.md",
            "deps/node_modules/x.md",
            "build/x.md",
        ],
    )
    def test_forbidden_paths_blocked(self, dev_home: str, rel: str) -> None:
        ok, err, _ = validate_sandbox_target_path(rel, dev_home)
        assert ok is False
        assert err in (ERROR_FORBIDDEN_PATH, ERROR_FILE_TYPE)

    @pytest.mark.parametrize("ext", [".sh", ".py", ".exe", ".bin", ".js", ".html"])
    def test_disallowed_file_type_blocked(self, dev_home: str, ext: str) -> None:
        ok, err, _ = validate_sandbox_target_path(f"a/file{ext}", dev_home)
        assert ok is False
        assert err == ERROR_FILE_TYPE

    @pytest.mark.parametrize("ext", [".txt", ".md", ".json", ".yaml", ".yml", ".csv"])
    def test_allowed_file_types_pass(self, dev_home: str, ext: str) -> None:
        ok, err, canonical = validate_sandbox_target_path(f"notes/file{ext}", dev_home)
        assert ok is True
        assert err is None
        assert canonical is not None

    def test_path_too_deep_blocked(self, dev_home: str) -> None:
        deep = "/".join(["d"] * (MAX_PATH_DEPTH + 1)) + "/f.md"
        ok, err, _ = validate_sandbox_target_path(deep, dev_home)
        assert ok is False
        assert err == ERROR_PATH_TOO_DEEP

    def test_filename_too_long_blocked(self, dev_home: str) -> None:
        name = "a" * (MAX_FILENAME_LENGTH + 1) + ".md"
        ok, err, _ = validate_sandbox_target_path(name, dev_home)
        assert ok is False
        assert err == ERROR_FILENAME_TOO_LONG

    def test_valid_path_canonicalizes_under_root(self, dev_home: str) -> None:
        canonical, err = canonicalize_sandbox_target_path("notes/hello.md", dev_home)
        assert err is None
        assert str(canonical).startswith(dev_home)
        assert str(canonical).endswith("notes/hello.md")


# ---------------------------------------------------------------------------
# 3. Symlink escape
# ---------------------------------------------------------------------------


class TestSymlinkEscape:
    def test_symlink_escape_blocked(self, dev_home: str) -> None:
        root, _ = ensure_dev_write_sandbox_root(dev_home)
        # Create a symlink inside the sandbox pointing outside.
        outside = Path(dev_home).parent / "outside-secret.md"
        outside.write_text("secret", encoding="utf-8")
        link = root / "escape-link.md"
        try:
            os.symlink(outside, link)
        except OSError:
            pytest.skip("symlink creation not supported on this platform")
        ok, err = validate_no_symlink_escape(link, root)
        assert ok is False
        assert err == ERROR_SYMLINK_ESCAPE

    def test_normal_path_passes_symlink_check(self, dev_home: str) -> None:
        root, _ = ensure_dev_write_sandbox_root(dev_home)
        ok, err = validate_no_symlink_escape(root / "a.md", root)
        assert ok is True
        assert err is None


# ---------------------------------------------------------------------------
# 4. Size limits + binary
# ---------------------------------------------------------------------------


class TestSizeAndBinary:
    def test_content_too_large(self) -> None:
        ok, err = validate_file_size_limits("x" * (MAX_SINGLE_WRITE_BYTES + 1))
        assert ok is False
        assert err == ERROR_CONTENT_TOO_LARGE

    def test_file_too_large_on_append(self) -> None:
        # Existing file near the cap + append pushes over the file-size limit.
        existing_size = MAX_FILE_AFTER_WRITE_BYTES - 1
        ok, err = validate_file_size_limits(
            "yyy", existing_size=existing_size, append=True
        )
        assert ok is False
        assert err == ERROR_FILE_TOO_LARGE

    def test_binary_content_rejected_by_write(self, dev_home: str) -> None:
        root, _ = ensure_dev_write_sandbox_root(dev_home)
        target = root / "bin.md"
        ok, err, before = safe_write_text(target, "".join(chr(i) for i in range(1, 200)))
        assert ok is False
        assert err == ERROR_BINARY_CONTENT

    def test_nul_content_rejected(self, dev_home: str) -> None:
        root, _ = ensure_dev_write_sandbox_root(dev_home)
        target = root / "nul.md"
        ok, err, _ = safe_write_text(target, "a\x00b")
        assert ok is False
        assert err == ERROR_BINARY_CONTENT


# ---------------------------------------------------------------------------
# 5. Safe IO round-trips (write only inside sandbox)
# ---------------------------------------------------------------------------


class TestSafeIO:
    def test_write_creates_file(self, dev_home: str) -> None:
        root, _ = ensure_dev_write_sandbox_root(dev_home)
        target = root / "notes" / "a.md"
        ok, err, before = safe_write_text(target, "hello world")
        assert ok is True and err is None
        assert before is None
        assert target.read_text(encoding="utf-8") == "hello world"

    def test_write_replaces_existing(self, dev_home: str) -> None:
        root, _ = ensure_dev_write_sandbox_root(dev_home)
        target = root / "a.md"
        safe_write_text(target, "old")
        ok, err, before = safe_write_text(target, "new")
        assert ok is True
        assert before == "old"
        assert target.read_text(encoding="utf-8") == "new"

    def test_append_creates_then_appends(self, dev_home: str) -> None:
        root, _ = ensure_dev_write_sandbox_root(dev_home)
        target = root / "log.md"
        ok1, _, before1 = safe_append_text(target, "line1\n")
        assert ok1 is True and before1 is None
        ok2, _, before2 = safe_append_text(target, "line2\n")
        assert ok2 is True and before2 == "line1\n"
        assert target.read_text(encoding="utf-8") == "line1\nline2\n"

    def test_patch_requires_unique_match(self, dev_home: str) -> None:
        root, _ = ensure_dev_write_sandbox_root(dev_home)
        target = root / "p.md"
        safe_write_text(target, "foo bar foo")
        # Two matches -> blocked.
        ok, err, _, count = safe_apply_patch(target, "foo", "baz")
        assert ok is False
        assert count == 2
        # Unique match -> applied.
        safe_write_text(target, "alpha beta")
        ok2, err2, _, count2 = safe_apply_patch(target, "beta", "gamma")
        assert ok2 is True and count2 == 1
        assert target.read_text(encoding="utf-8") == "alpha gamma"

    def test_patch_missing_target_blocked(self, dev_home: str) -> None:
        root, _ = ensure_dev_write_sandbox_root(dev_home)
        ok, err, _, count = safe_apply_patch(root / "missing.md", "x", "y")
        assert ok is False

    def test_readback_summary(self, dev_home: str) -> None:
        root, _ = ensure_dev_write_sandbox_root(dev_home)
        target = root / "rb.md"
        safe_write_text(target, "content here")
        summary = readback_summary(target)
        assert summary["exists"] is True
        assert summary["sizeBytes"] == len("content here")
        assert summary["contentHash"] == compute_sha256_text("content here")
        assert "content here" in summary["snippet"]

    def test_readback_missing_file(self, dev_home: str) -> None:
        root, _ = ensure_dev_write_sandbox_root(dev_home)
        summary = readback_summary(root / "nope.md")
        assert summary["exists"] is False


class TestHashAndDiff:
    def test_sha256_stable(self) -> None:
        assert compute_sha256_text("abc") == compute_sha256_text("abc")
        assert compute_sha256_text("abc") != compute_sha256_text("abd")

    def test_diff_preview_shows_changes(self) -> None:
        diff = build_diff_preview("a\nb\n", "a\nc\n")
        assert "b" in diff and "c" in diff

    def test_diff_empty_when_unchanged(self) -> None:
        diff = build_diff_preview("same\n", "same\n")
        assert diff.strip() == ""


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
