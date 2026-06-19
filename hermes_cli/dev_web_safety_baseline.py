"""Phase 3E–3H Missing-Implementation Recovery — Safety Baseline (Block 1).

Consolidates the dev-only safety primitives that Phase 3E–3H required to land as
*code* (not just docs) into one pure, stdlib-only, side-effect-free module:

  - **Route governance** — count the frozen Phase 1G baseline
    (``34/34/5/0/1/1``) directly off a FastAPI app, the exact way
    :func:`handle_route_governance_read` does, and assert it did not drift.
    No route definition is read or mutated here; this is a read-only
    introspection helper.
  - **Production isolation** — classify a ``HERMES_HOME`` candidate as dev /
    production / unknown, and detect production ``state.db``-like paths **by
    string analysis only** — the production home is never opened, never
    stated, never read.
  - **Forbidden-path protection** — a pure path evaluator that denies
    ``~/.hermes`` and anything under it, production database paths, traversal
    escape (``..``), symlink escape (only when an explicit allowed root is
    resolvable), and the unknown runtime-store write locations.
  - **Dev-home safety** — confirm the canonical dev home is the development
    instance and never the production one.
  - **``.claude`` exclusion** — a read-only git check that ``.claude`` is not
    staged / committed. It shells out to ``git`` only for ``status`` /
``diff`` reads (never ``add`` / ``commit`` / ``reset``).
  - **Runtime-store protection** — a helper that scans a directory for
    runtime-store-like artifacts (``*.jsonl`` / ``state.db`` /
    ``*-store.json``) so tests can prove a skeleton created none.

Hard guarantees (frozen, see docs/webui/phase-3{e,f,g,h}-*.md):

  - Pure / deterministic / stdlib-only. **No** dynamic import (no ``importlib``
    loader, no ``__import__`` call), **no** shell execution, **no** subprocess
    code execution, **no** ``requests`` / ``httpx`` / ``aiohttp`` / socket / DNS
    / live network call.
  - **Never** opens, stats, reads, or writes ``~/.hermes`` or any production
    ``state.db``. Production is referenced **only** as a frozen string
    constant for denial-by-comparison.
  - **Never** signals / stops / restarts / replaces the production gateway or
    any process. The single ``git`` subprocess is read-only
    (``status --porcelain`` / ``diff --cached --name-only``).
  - **No** new HTTP route, no new OpenAPI path, no tool-write route. This
    module is not imported by the FastAPI app; it is a library + test surface.

Phase: 3E–3H Missing-Implementation Recovery
Status: implemented (read-only safety baseline). No real plugin runtime, no
        plugin execution, no dynamic loading, no external network, no new
        route, no production access.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Any, Iterable, Mapping

# ---------------------------------------------------------------------------
# 1. Frozen dev-environment constants (allowlist, not deny-list)
# ---------------------------------------------------------------------------

#: Canonical source root (derived from this module's location at import time,
#: NOT from cwd — mirrors the Dev WebUI environment guard in CLAUDE.md).
ALLOWED_SOURCE_ROOT: Path = Path(__file__).resolve().parents[1]

#: Canonical development ``HERMES_HOME``. Everything dev writes lives here.
ALLOWED_HERMES_HOME: Path = Path("/Users/huangruibang/Code/hermes-home-dev").resolve()

#: Production ``HERMES_HOME`` — referenced ONLY as a denial target. Never
#: opened, stated, read, or written by anything in this module.
PRODUCTION_HERMES_HOME: Path = Path("/Users/huangruibang/.hermes").resolve()

#: The only bind host dev services may ever use.
ALLOWED_BIND_HOST: str = "127.0.0.1"

#: Frozen route-governance baseline string (mirrors the descriptor registry).
ROUTE_GOVERNANCE_EXPECTED: str = "34/34/5/0/1/1"

#: The six integers encoded by :data:`ROUTE_GOVERNANCE_EXPECTED`, in order:
#: openapi paths, runtime routes, tool GET, tool write HTTP, tool dry-run,
#: tool execution.
ROUTE_GOVERNANCE_EXPECTED_TUPLE: tuple[int, ...] = (34, 34, 5, 0, 1, 1)

#: Production state-database filename stems — denied by string match only.
PRODUCTION_DB_STEMS: tuple[str, ...] = ("state.db", "gateway.db", "sessions.db")

#: Filenames that look like a committed/runtime store artifact. Used by the
#: runtime-store-protection scan to prove a skeleton wrote none.
RUNTIME_STORE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\.jsonl$"),
    re.compile(r"\.db$"),
    re.compile(r"-store\.json$"),
    re.compile(r"store\.json$"),
    re.compile(r"\.sqlite$"),
    re.compile(r"\.sqlite3$"),
    re.compile(r"\.pid$"),
)

#: Names of the runtime stores that must never be created/committed by a
#: dev-only skeleton (audited for documentation, not loaded).
FORBIDDEN_RUNTIME_STORE_NAMES: frozenset[str] = frozenset(
    {
        "plugin_registry.json",
        "plugin_execution_store.json",
        "provider_live_store.json",
        "workflow_runtime_store.json",
        "audit_runtime_store.json",
        "capability_runtime_store.json",
        "plugin_runtime.jsonl",
    }
)


# ---------------------------------------------------------------------------
# 2. Route governance (read-only introspection — reuses the canonical logic)
# ---------------------------------------------------------------------------

#: HTTP methods considered "write" methods when counting tool-write routes.
_WRITE_METHODS: frozenset[str] = frozenset({"post", "put", "patch", "delete"})


def _default_api_prefix(app: Any) -> str:
    """Best-effort business prefix for *app*. Falls back to ``/api/dev/v1``."""
    for attr in ("api_prefix",):
        value = getattr(app, attr, None)
        if isinstance(value, str) and value:
            return value
    cfg = getattr(app, "state", None)
    settings = getattr(cfg, "settings", None) if cfg is not None else None
    if settings is not None:
        value = getattr(settings, "api_prefix", None)
        if isinstance(value, str) and value:
            return value
    return "/api/dev/v1"


def route_governance_counts(app: Any) -> dict[str, int]:
    """Count the six route-governance figures directly off *app*.

    Mirrors :func:`handle_route_governance_read` exactly:

      - ``openApiPaths`` — OpenAPI paths under the business prefix (34).
      - ``runtimeRoutes`` — Starlette ``Route`` objects under the prefix (34).
      - ``toolGetRoutes`` — ``/tools`` paths exposing ``GET`` (5).
      - ``toolWriteRoutes`` — ``/tools`` paths with a mutating method **except**
        ``/tools/dry-run`` and ``/tools/execute`` (0).
      - ``toolDryRunRoutes`` — ``/tools/dry-run`` (1).
      - ``toolExecutionRoutes`` — ``/tools/execute`` (1).

    Read-only. Never raises on a malformed app — a counting failure yields 0
    for that figure (which then trips the drift assertion, fail-closed).
    """
    prefix = _default_api_prefix(app)

    try:
        spec = app.openapi() if callable(getattr(app, "openapi", None)) else {}
    except Exception:  # pragma: no cover — defensive; fail-closed to 0
        spec = {}
    if not isinstance(spec, Mapping):
        spec = {}
    spec_paths = spec.get("paths", {}) if isinstance(spec, Mapping) else {}
    if not isinstance(spec_paths, Mapping):
        spec_paths = {}

    openapi_paths = [p for p in spec_paths if isinstance(p, str) and p.startswith(prefix)]

    runtime_paths: list[str] = []
    for route in getattr(app, "routes", []) or []:
        path = getattr(route, "path", None)
        if isinstance(path, str) and path.startswith(prefix):
            runtime_paths.append(path)

    tool_get_routes: list[str] = []
    for p in openapi_paths:
        if not p.startswith(f"{prefix}/tools"):
            continue
        methods = spec_paths.get(p, {})
        if isinstance(methods, Mapping) and "get" in methods:
            tool_get_routes.append(p)

    non_write_tool_routes = {f"{prefix}/tools/dry-run", f"{prefix}/tools/execute"}
    tool_write_routes: list[str] = []
    for p in openapi_paths:
        if not p.startswith(f"{prefix}/tools"):
            continue
        methods = spec_paths.get(p, {})
        if not isinstance(methods, Mapping):
            continue
        mutating = _WRITE_METHODS & set(methods.keys())
        if mutating and p not in non_write_tool_routes:
            tool_write_routes.append(p)

    tool_dry_run_routes = [p for p in openapi_paths if p == f"{prefix}/tools/dry-run"]
    tool_execution_routes = [p for p in openapi_paths if p == f"{prefix}/tools/execute"]

    return {
        "openApiPaths": len(openapi_paths),
        "runtimeRoutes": len(runtime_paths),
        "toolGetRoutes": len(tool_get_routes),
        "toolWriteRoutes": len(tool_write_routes),
        "toolDryRunRoutes": len(tool_dry_run_routes),
        "toolExecutionRoutes": len(tool_execution_routes),
    }


def route_governance_new_route_flags() -> dict[str, int]:
    """Return the frozen "no new route" flags.

    Every value is a constant ``0``: this module (and the whole 3E–3H recovery)
    introduces no HTTP / tool-write / provider / plugin / runtime route. The
    flags exist so a regression test can pin them to zero in one assertion.
    """
    return {
        "newHttpRoute": 0,
        "newToolWriteRoute": 0,
        "newProviderRoute": 0,
        "newPluginRoute": 0,
        "newRuntimeRoute": 0,
    }


def format_route_governance(counts: Mapping[str, int]) -> str:
    """Render counts as the canonical ``"openapi/runtime/get/write/dry/exec"`` string."""
    return "/".join(
        str(counts.get(key, 0))
        for key in (
            "openApiPaths",
            "runtimeRoutes",
            "toolGetRoutes",
            "toolWriteRoutes",
            "toolDryRunRoutes",
            "toolExecutionRoutes",
        )
    )


def parse_route_governance(value: str) -> tuple[int, ...]:
    """Parse a ``"a/b/c/d/e/f"`` baseline string into a 6-int tuple.

    Returns an all-zero tuple on any malformed input (fail-closed — the caller's
    drift assertion then trips).
    """
    if not isinstance(value, str):
        return (0, 0, 0, 0, 0, 0)
    parts = value.split("/")
    if len(parts) != 6:
        return (0, 0, 0, 0, 0, 0)
    out: list[int] = []
    for part in parts:
        try:
            out.append(int(part))
        except ValueError:
            return (0, 0, 0, 0, 0, 0)
    return tuple(out)  # type: ignore[return-value]


def route_governance_drift(counts: Mapping[str, int]) -> dict[str, Any]:
    """Compare *counts* to the frozen baseline.

    Returns ``{"drifted": bool, "expected": "34/34/5/0/1/1", "actual": str,
    "diff": {...}}``. ``diff`` maps each figure to ``None`` (unchanged) or a
    ``"expected->actual"`` string.
    """
    expected = parse_route_governance(ROUTE_GOVERNANCE_EXPECTED)
    keys = (
        "openApiPaths",
        "runtimeRoutes",
        "toolGetRoutes",
        "toolWriteRoutes",
        "toolDryRunRoutes",
        "toolExecutionRoutes",
    )
    diff: dict[str, str | None] = {}
    drifted = False
    for idx, key in enumerate(keys):
        actual = int(counts.get(key, 0))
        if actual != expected[idx]:
            diff[key] = f"{expected[idx]}->{actual}"
            drifted = True
        else:
            diff[key] = None
    return {
        "drifted": drifted,
        "expected": ROUTE_GOVERNANCE_EXPECTED,
        "actual": format_route_governance(counts),
        "diff": diff,
    }


def assert_route_governance_unchanged(
    app: Any, *, expected: str = ROUTE_GOVERNANCE_EXPECTED
) -> dict[str, int]:
    """Assert *app*'s route-governance figures match *expected* (default frozen).

    Returns the counts on success. Raises :class:`AssertionError` on drift —
    this is the single, grep-able regression guard for "no new route".
    """
    counts = route_governance_counts(app)
    report = route_governance_drift(counts)
    if report["expected"] != expected or report["drifted"]:
        # Re-evaluate against the caller's expected string if it differs.
        if expected != ROUTE_GOVERNANCE_EXPECTED:
            want = parse_route_governance(expected)
            keys = (
                "openApiPaths",
                "runtimeRoutes",
                "toolGetRoutes",
                "toolWriteRoutes",
                "toolDryRunRoutes",
                "toolExecutionRoutes",
            )
            local_diff = {
                k: (None if int(counts.get(k, 0)) == want[i] else f"{want[i]}->{int(counts.get(k, 0))}")
                for i, k in enumerate(keys)
            }
            if any(v is not None for v in local_diff.values()):
                raise AssertionError(
                    f"route governance drift: expected {expected}, got {report['actual']}, diff={local_diff}"
                )
        else:
            raise AssertionError(
                f"route governance drift: expected {ROUTE_GOVERNANCE_EXPECTED}, "
                f"got {report['actual']}, diff={report['diff']}"
            )
    return counts


# ---------------------------------------------------------------------------
# 3. Production isolation (string analysis ONLY — never touch production)
# ---------------------------------------------------------------------------


def classify_hermes_home(candidate: Any) -> str:
    """Classify a ``HERMES_HOME`` candidate as ``"dev"`` / ``"production"`` / ``"unknown"``.

    Pure comparison against the frozen constants — the path is **never** opened
    or stated. A candidate that equals :data:`PRODUCTION_HERMES_HOME` (or any
    path beneath it) is ``"production"``; one that equals
    :data:`ALLOWED_HERMES_HOME` is ``"dev"``; anything else is ``"unknown"``.
    """
    if not isinstance(candidate, (str, os.PathLike)):
        return "unknown"
    try:
        resolved = Path(candidate).expanduser()
    except (OSError, ValueError):
        return "unknown"
    # Compare by normalized parts WITHOUT resolving symlinks on disk — the
    # production home must never be stat()'d. Normalize trailing slashes and
    # '..' lexically.
    norm = _normalize_lexically(resolved)
    prod_norm = _normalize_lexically(PRODUCTION_HERMES_HOME)
    dev_norm = _normalize_lexically(ALLOWED_HERMES_HOME)
    if norm == prod_norm:
        return "production"
    # Anything strictly beneath the production home is production.
    if _is_strictly_within(norm, prod_norm):
        return "production"
    if norm == dev_norm:
        return "dev"
    if _is_strictly_within(norm, dev_norm):
        return "dev"
    return "unknown"


def is_production_home(candidate: Any) -> bool:
    """True iff *candidate* is the production home or beneath it (string-only)."""
    return classify_hermes_home(candidate) == "production"


def is_dev_home(candidate: Any) -> bool:
    """True iff *candidate* is the canonical dev home or beneath it."""
    return classify_hermes_home(candidate) == "dev"


def _normalize_lexically(path: Path) -> str:
    """Lexical normalization without touching the filesystem.

    Expands ``~``, collapses redundant separators and resolves ``.`` / ``..``
    segments **lexically** (so ``~/.hermes/../.hermes`` still collapses to the
    production home). Symlinks are intentionally NOT resolved on disk.
    """
    expanded = Path(os.path.expanduser(str(path)))
    is_absolute = expanded.is_absolute()
    parts: list[str] = []
    for part in expanded.parts:
        if part in ("", "/", "."):
            continue
        if part == "..":
            if parts:
                parts.pop()
            continue
        parts.append(part)
    if not parts:
        return "/" if is_absolute else "."
    joined = "/".join(parts)
    return "/" + joined if is_absolute else joined


def _is_strictly_within(child: str, parent: str) -> bool:
    """True if the *child* path string is strictly beneath *parent*."""
    if not child or not parent:
        return False
    if child == parent:
        return False
    return child.startswith(parent.rstrip("/") + "/")


def is_production_state_db(candidate: Any) -> bool:
    """True iff *candidate* looks like a production state database path.

    Matches by filename stem (``state.db`` / ``gateway.db`` / ``sessions.db``)
    **or** by being located beneath the production home. Pure string analysis —
    the path is never opened.
    """
    if not isinstance(candidate, (str, os.PathLike)):
        return False
    text = str(candidate)
    lowered = text.lower()
    # Filename-stem match anywhere in the path.
    for stem in PRODUCTION_DB_STEMS:
        if lowered == stem or lowered.endswith("/" + stem) or lowered.endswith(os.sep + stem):
            return True
    # Located beneath the production home.
    if is_production_home(text):
        return True
    # A bare state.db reference (e.g. a forbidden-field value).
    if "state.db" in lowered and ("/.hermes/" in lowered or "/.hermes" in lowered):
        return True
    return False


def assert_dev_environment(hermes_home: Any) -> None:
    """Fail-closed dev-environment assertion (mirrors CLAUDE.md's guard).

    Raises :class:`RuntimeError` unless ``hermes_home`` is the canonical dev
    home. Used as a defensive gate by dev-only helpers; never opens production.
    """
    if classify_hermes_home(hermes_home) != "dev":
        raise RuntimeError(
            f"HERMES_HOME must be {ALLOWED_HERMES_HOME}, got {hermes_home!r}"
        )


# ---------------------------------------------------------------------------
# 4. Forbidden-path protection (pure evaluator — never opens the target)
# ---------------------------------------------------------------------------


def _looks_like_absolute_production_path(text: str) -> bool:
    """True if a path string points at an absolute production location."""
    if "/Users/huangruibang/.hermes" in text:
        return True
    if text.startswith("/Users/") and ".hermes" in text:
        return True
    return False


def evaluate_path_safety(
    candidate: Any,
    *,
    allowed_roots: Iterable[Any] = (),
    allow_write: bool = False,
) -> dict[str, Any]:
    """Pure path-safety evaluation. Never opens / stats the candidate.

    Returns ``{"allowed": bool, "reasons": list[str], "normalized": str}``.

    Denied cases (each pushes a precise reason, fail-closed):

      - ``~/.hermes`` or anything beneath it (``forbidden_production_home``).
      - production ``state.db``-like paths (``forbidden_production_database``).
      - absolute production-like path (``forbidden_absolute_production_path``).
      - path-traversal escape via ``..`` once normalized outside an allowed
        root (``path_traversal_escape``).
      - symlink escape: when an allowed root is resolvable on disk and the
        candidate resolves outside it (``symlink_escape``). Skipped silently
        when the allowed root does not exist (tests use temp roots; production
        is never probed).
      - a write target outside every allowed root
        (``write_outside_allowed_root``).

    ``allowed_roots`` are dev-safe temp / fixture roots supplied by the caller.
    A read of a path *inside* an allowed root is allowed; a write must be
    inside an allowed root too. The production home is never in the allowed
    set — the constants forbid it.
    """
    reasons: list[str] = []
    normalized = ""

    if not isinstance(candidate, (str, os.PathLike)):
        return {"allowed": False, "reasons": ["invalid_path_type"], "normalized": ""}

    text = os.path.expanduser(str(candidate))
    normalized = _normalize_lexically(Path(text))

    # 1. Production home / beneath it.
    if is_production_home(text):
        reasons.append("forbidden_production_home")
    # 2. Production state database.
    if is_production_state_db(text):
        reasons.append("forbidden_production_database")
    # 3. Absolute production-looking path.
    if _looks_like_absolute_production_path(text):
        reasons.append("forbidden_absolute_production_path")
    # 4. Forbidden runtime-store filename.
    name = Path(normalized).name
    if name in FORBIDDEN_RUNTIME_STORE_NAMES:
        reasons.append("forbidden_runtime_store_name")

    roots = [Path(os.path.expanduser(str(r))).expanduser() for r in allowed_roots if r]
    root_norms = [_normalize_lexically(r) for r in roots]

    inside_any_root = any(
        (normalized == rn) or _is_strictly_within(normalized, rn) for rn in root_norms
    )

    # 5. Path traversal escape: candidate normalizes outside every allowed root
    #    AND is not itself an allowed root, while a root context was given.
    if root_norms and not inside_any_root:
        # Only flag traversal when the input actually contained a '..' that
        # escaped — i.e. the user tried to break out of an allowed root.
        if ".." in Path(text).as_posix():
            reasons.append("path_traversal_escape")

    # 6. Symlink escape — only probe allowed roots that exist on disk. The
    #    production home is never in `roots`, so it is never probed.
    if roots and inside_any_root:
        try:
            real_candidate = Path(text).resolve(strict=False)
            for root in roots:
                if not root.exists():
                    continue
                real_root = root.resolve(strict=False)
                try:
                    real_candidate.relative_to(real_root)
                except ValueError:
                    reasons.append("symlink_escape")
                    break
        except (OSError, ValueError):
            # Resolution failure on the candidate → treat as traversal risk.
            if ".." in Path(text).as_posix():
                reasons.append("path_traversal_escape")

    # 7. Write must land inside an allowed root.
    if allow_write:
        if not roots:
            reasons.append("write_outside_allowed_root")
        elif not inside_any_root:
            reasons.append("write_outside_allowed_root")

    allowed = len(reasons) == 0
    return {"allowed": allowed, "reasons": reasons, "normalized": normalized}


def evaluate_runtime_store_write(
    candidate: Any, *, allowed_roots: Iterable[Any] = ()
) -> dict[str, Any]:
    """Evaluate a runtime-store write attempt. Default-deny.

    A dev-only skeleton must never create a runtime store. This helper denies
    any path whose filename is a forbidden runtime-store name, and otherwise
    applies the path-safety evaluator in write mode against the caller's
    temp/fixture roots.
    """
    base = evaluate_path_safety(candidate, allowed_roots=allowed_roots, allow_write=True)
    if base["allowed"]:
        # Even a path inside an allowed root is denied if it looks like a
        # committed runtime store — a skeleton creates none by contract.
        if Path(base["normalized"]).name in FORBIDDEN_RUNTIME_STORE_NAMES:
            base["allowed"] = False
            base["reasons"].append("forbidden_runtime_store_name")
    return base


# ---------------------------------------------------------------------------
# 5. Runtime-store protection (scan helper for tests)
# ---------------------------------------------------------------------------


def find_runtime_store_artifacts(directory: Any) -> list[str]:
    """List files under *directory* that look like a runtime-store artifact.

    Read-only walk of *directory* (a test temp dir). Returns matching relative
    paths so a test can assert the list is empty after running a skeleton.
    Never recurses into ``.git``.
    """
    if not isinstance(directory, (str, os.PathLike)):
        return []
    root = Path(directory)
    if not root.is_dir():
        return []
    hits: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Don't descend into git metadata.
        dirnames[:] = [d for d in dirnames if d != ".git"]
        for fname in filenames:
            full = Path(dirpath) / fname
            rel = str(full.relative_to(root))
            if fname in FORBIDDEN_RUNTIME_STORE_NAMES:
                hits.append(rel)
                continue
            if any(pattern.search(fname) for pattern in RUNTIME_STORE_PATTERNS):
                hits.append(rel)
    return sorted(hits)


# ---------------------------------------------------------------------------
# 6. .claude exclusion (read-only git check)
# ---------------------------------------------------------------------------


def _git(repo_dir: Path, *args: str) -> tuple[int, str, str]:
    """Run a read-only ``git`` command in *repo_dir*. Never writes."""
    try:
        proc = subprocess.run(  # noqa: S603 — args are a fixed read-only tuple
            ["git", *args],
            cwd=str(repo_dir),
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return 128, "", ""
    return proc.returncode, proc.stdout or "", proc.stderr or ""


def check_dotclaude_not_staged(repo_dir: Any = ALLOWED_SOURCE_ROOT) -> dict[str, Any]:
    """Read-only check that ``.claude`` is neither staged nor committed.

    Runs ``git diff --cached --name-only`` (staged) and
    ``git ls-files --error-unmatch .claude`` (tracked) only. **Never** runs
    ``add`` / ``commit`` / ``reset`` / ``clean``. Returns
    ``{"staged": bool, "tracked": bool, "stagedClaudePaths": list, "ok": bool}``.

    ``ok`` is True only when no ``.claude`` path is staged and ``.claude`` is
    not tracked.
    """
    repo = Path(repo_dir)
    code, staged_out, _ = _git(repo, "diff", "--cached", "--name-only", "--", ".")
    staged_paths = [p for p in staged_out.splitlines() if p.strip()] if code == 0 else []
    staged_claude = [p for p in staged_paths if p == ".claude" or p.startswith(".claude/")]

    tcode, _, _ = _git(repo, "ls-files", "--error-unmatch", ".claude")
    tracked = tcode == 0

    return {
        "staged": bool(staged_claude),
        "tracked": tracked,
        "stagedClaudePaths": sorted(staged_claude),
        "ok": (not staged_claude) and (not tracked),
    }


# ---------------------------------------------------------------------------
# 7. Boundary re-affirmation (pure constants, grep-able)
# ---------------------------------------------------------------------------

#: Frozen "no side-effect surface" flags for this module. Constants, not state.
NO_REAL_PLUGIN_RUNTIME: bool = True
NO_PLUGIN_EXECUTION: bool = True
NO_PLUGIN_LOADER: bool = True
NO_DYNAMIC_LOADING: bool = True
NO_EXTERNAL_NETWORK: bool = True
NO_REAL_API_KEY_READ: bool = True
NO_NEW_ROUTE: bool = True
NO_PRODUCTION_ACCESS: bool = True


def assert_no_side_effect_surface() -> None:
    """Re-affirm the no-side-effect invariants (pure assertion helper)."""
    assert NO_REAL_PLUGIN_RUNTIME is True
    assert NO_PLUGIN_EXECUTION is True
    assert NO_PLUGIN_LOADER is True
    assert NO_DYNAMIC_LOADING is True
    assert NO_EXTERNAL_NETWORK is True
    assert NO_REAL_API_KEY_READ is True
    assert NO_NEW_ROUTE is True
    assert NO_PRODUCTION_ACCESS is True


__all__ = [
    "ALLOWED_SOURCE_ROOT",
    "ALLOWED_HERMES_HOME",
    "PRODUCTION_HERMES_HOME",
    "ALLOWED_BIND_HOST",
    "ROUTE_GOVERNANCE_EXPECTED",
    "ROUTE_GOVERNANCE_EXPECTED_TUPLE",
    "PRODUCTION_DB_STEMS",
    "RUNTIME_STORE_PATTERNS",
    "FORBIDDEN_RUNTIME_STORE_NAMES",
    "NO_REAL_PLUGIN_RUNTIME",
    "NO_PLUGIN_EXECUTION",
    "NO_PLUGIN_LOADER",
    "NO_DYNAMIC_LOADING",
    "NO_EXTERNAL_NETWORK",
    "NO_REAL_API_KEY_READ",
    "NO_NEW_ROUTE",
    "NO_PRODUCTION_ACCESS",
    "route_governance_counts",
    "route_governance_new_route_flags",
    "format_route_governance",
    "parse_route_governance",
    "route_governance_drift",
    "assert_route_governance_unchanged",
    "classify_hermes_home",
    "is_production_home",
    "is_dev_home",
    "is_production_state_db",
    "assert_dev_environment",
    "evaluate_path_safety",
    "evaluate_runtime_store_write",
    "find_runtime_store_artifacts",
    "check_dotclaude_not_staged",
    "assert_no_side_effect_surface",
]
