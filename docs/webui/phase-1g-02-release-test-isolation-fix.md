# Phase 1G-02 Release Test Isolation and Stale Assertion Fix

## Status: Completed

This document records the test isolation fixes applied to close the two blocking items for Phase 1G-02 release.

## Problem Background

Phase 1G-02 Release Baseline Verification identified two blocking items:

1. **Browser Guard log non-empty**: XAI OAuth tests triggered `webbrowser.get`/`webbrowser.open` calls, and Browser Supervisor tests triggered `subprocess.Popen(google-chrome)` calls through the Guard shim.
2. **3 stale route count failures**: `test_dev_web_messages.py` and `test_dev_web_sessions.py` asserted `len(business) == 11` but the actual count was 29 (routes added across Phases 1A–1G).

## Triggering Test Inventory

### XAI OAuth

| Node ID | Trigger | URL / Call |
|---|---|---|
| `test_xai_loopback_login_manual_paste_skips_http_server` | `webbrowser.get` → `webbrowser.open` | `https://auth.x.ai/oauth2/authorize?...` |
| `test_xai_loopback_login_manual_paste_state_mismatch_raises` | `webbrowser.get` → `webbrowser.open` | `https://auth.x.ai/oauth2/authorize?...` |

Root cause: Tests call `_xai_oauth_loopback_login(manual_paste=True)` which internally calls `_can_open_graphical_browser()` (triggering `webbrowser.get`) and then `webbrowser.open(authorize_url)`. The production code catches the RuntimeError from the Guard, but the Guard log records the attempts.

### Browser Supervisor

| Test pattern | Trigger |
|---|---|
| 20 tests using `chrome_cdp` fixture | `subprocess.Popen([google-chrome, ...])` via `_find_chrome()` |

Root cause: `pytestmark` only checked `shutil.which("google-chrome")`. The Guard's fake `google-chrome` shim was found by `shutil.which`, so the skipif didn't trigger, and the `chrome_cdp` fixture attempted to launch Chrome through the shim.

## Fixes Applied

### 1. Browser Supervisor E2E Gating

**File:** `tests/tools/test_browser_supervisor.py`

**Change:** Added `HERMES_E2E_BROWSER=1` env var check to `pytestmark` skipif.

```python
pytestmark = pytest.mark.skipif(
    not os.environ.get("HERMES_E2E_BROWSER")
    or (not shutil.which("google-chrome") and not shutil.which("chromium")),
    reason="E2E browser tests require HERMES_E2E_BROWSER=1 and Chrome/Chromium installed",
)
```

This aligns with the existing docstring: "Automated: skipped in CI unless `HERMES_E2E_BROWSER=1` is set." Without the env var, tests are skipped immediately — no Chrome launch is attempted.

### 2. XAI OAuth webbrowser Isolation

**File:** `tests/hermes_cli/test_auth_manual_paste.py`

**Change:** Added `autouse` fixture that mocks `_can_open_graphical_browser` to return `False`.

```python
@pytest.fixture(autouse=True)
def _block_real_browser(monkeypatch):
    monkeypatch.setattr(auth_mod, "_can_open_graphical_browser", lambda: False)
```

This prevents any test in the file from reaching the `webbrowser.get`/`webbrowser.open` code path. The `_can_open_graphical_browser` guard is checked before `webbrowser.open` in the production code (`hermes_cli/auth.py:6647`), so short-circuiting it prevents all browser calls.

### 3. Stale Route Count Assertions

**Files:** `tests/test_dev_web_messages.py`, `tests/test_dev_web_sessions.py`

**Changes:**
- `test_business_routes_count` (messages): Changed from `assert len(business) == 11` to `assert len(business) >= 11` with a check that the messages route exists.
- `test_openapi_has_eleven_business_paths` (sessions): Renamed to `test_openapi_has_minimum_business_paths`, changed to `assert len(business) >= 11` with explicit checks for core session routes.
- `test_no_forbidden_routes` (messages): Removed `/reviews` assertion since review routes were legitimately added in Phase 1F. Only truly dangerous routes (`/send`, `/upload`, `/delete`) remain forbidden.
- Central route governance (`test_dev_web_0c06_closure.py`) remains the single owner of the exact 29-path count.

## Test Results

### Directed Tests

| Suite | Collected | Passed | Failed | Guard Log |
|---|---|---|---|---|
| Browser Supervisor | 22 | 0 | 0 (22 skipped) | Empty ✅ |
| XAI OAuth (auth_manual_paste) | 29 | 29 | 0 | Empty ✅ |
| Messages | 65 | 65 | 0 | Empty ✅ |
| Sessions | 106 | 106 | 0 | Empty ✅ |
| Route Governance | 295 | 295 | 0 | Empty ✅ |
| Combined Isolation Gate | 348 | 326 | 0 (22 skipped) | Empty ✅ |

### Phase 1G-02 Scoped Regression Suite

| Metric | Value |
|---|---|
| Files | 11 |
| Collected | 788 |
| Passed | 788 |
| Failed | **0** |
| Guard Log | Empty ✅ |

Previous 3 stale-assertion failures closed.

### Authoritative Current Backend Suite

| Metric | Value |
|---|---|
| Files collected | 1,357 |
| Tests | 30,294 |
| Passed | 30,202 |
| Failed | 92 |
| Guard Log | Empty ✅ |

- All 4 modified test files: **0 failures**
- No new failures introduced by this fix
- 92 failures are pre-existing historical issues (proxy timeouts, AF_UNIX path length, file write guard, etc.)

## Quality Gates

| Gate | Result |
|---|---|
| `python -m compileall` | PASS |
| `python -m py_compile toolsets.py` | PASS |
| `ruff check` (modified files) | PASS |
| `memory-check` | PASS |
| `dev-check` | PASS (WARN: dirty worktree — expected) |
| OpenAPI paths | 29 |
| Runtime paths | 29 |
| Tool GET routes | 2 |
| Tool write routes | 0 |

## Formal Dev-Home Validation

| Artifact | Before | After | Match |
|---|---|---|---|
| state.db SHA-256 | `b1911d16...` | `b1911d16...` | ✅ |
| Sessions count | 417 | 417 | ✅ |
| Messages count | 22,552 | 22,552 | ✅ |
| MEMORY.md SHA-256 | `44be12a0...` | `44be12a0...` | ✅ |
| memory/events.jsonl SHA-256 | `3df1fc83...` | `3df1fc83...` | ✅ |
| reviews/events.jsonl SHA-256 | `05b8e7b8...` | `05b8e7b8...` | ✅ |
| state.db-wal | absent | absent | ✅ |
| state.db-shm | absent | absent | ✅ |

**Persistent side effects: 0**

## Production Code Changes

None. All changes are test-only.

## Commits

1. `test(webui): isolate external auth and browser supervisor tests` — Browser Supervisor E2E gating + XAI OAuth webbrowser mock
2. `test(webui): refresh message and session route assertions` — Stale route count fix + forbidden-routes update
3. `docs(webui): document phase 1g-02 release test isolation closure` — This document

## Risks

### P0
None identified. No production code changed. Guard log empty. Zero side effects.

### P1
None identified. All modified files pass. Scoped suite zero failures.

### P2
- The proxy-based network isolation (`HTTP_PROXY=http://127.0.0.1:9`) caused additional test timeouts in the Authoritative Suite. These are not new failures — the tests would have failed differently without the proxy (real network connection refused). Previous baseline: 92 failed; current: 92 failed. No regression.
- `test_xai_provider_labels.py::test_xai_oauth_provider_label_is_not_collapsed_to_api_key_label` fails with `assert 'xai' == 'xAI'` — this is a pre-existing issue unrelated to this fix.

## Next Steps

This task closes the two blocking items for Phase 1G-02 release. It does NOT approve the release and does NOT authorize push.

**Phase 1G-02-Release**: Re-run final release verification.
**Phase 1G-03**: Not started.
