# ADR-WEBUI-001: Dev WebUI Read-Only API Boundary

**Status:** Accepted
**Date:** 2026-06-07
**Decision Scope:** Hermes Dev WebUI Phase 0C
**Supersedes:** None
**Superseded by:** None

---

## Context

The Hermes Dev WebUI (Vue 3 frontend at `apps/hermes-dev-webui/`) needs to display real session data, memory state, context preview, and agent status from the Hermes development instance. Currently (Phase 0B), all content is static mock data.

We must decide:
1. Where to host the Dev WebUI API server
2. How to connect it to Hermes backend services
3. What isolation guarantees to enforce

---

## Decision

### 1. Use an independent FastAPI Dev API server (Option B)

The Dev WebUI API will be a **new, independent FastAPI application** running on `127.0.0.1:5181`, separate from both the production gateway and the existing web dashboard.

### 2. Directly import and call Hermes Python service functions

The API will import `SessionDB`, `memory_router`, `runtime_memory`, and `memory_review_queue` directly as Python modules. It will NOT use subprocess CLI calls.

### 3. Enforce read-only at multiple layers

- `SessionDB(read_only=True)`
- Only call read-only functions from `memory_router`
- DTO whitelist prevents sensitive field leakage
- Startup validation rejects non-development HERMES_HOME
- CORS restricted to `http://127.0.0.1:5180`

---

## Candidates Considered

### Option A: Add Dev API routes to existing Gateway

| Aspect | Assessment |
|--------|-----------|
| Process isolation | ❌ Shares process with production gateway |
| Port conflict | ❌ Would need gateway restart to add routes |
| Risk to production | ❌ A bug in dev API could crash the gateway |
| Lifecycle coupling | ❌ Dev API lifecycle tied to gateway lifecycle |
| Code separation | ❌ Mixes dev and production code paths |
| **Recommendation** | **Rejected** |

**Reason:** The production gateway (PID 1717) is a long-running, stable process. Adding experimental dev API routes to it creates unnecessary risk. A gateway crash would disrupt all messaging platforms.

### Option B: New independent Dev API server (SELECTED)

| Aspect | Assessment |
|--------|-----------|
| Process isolation | ✅ Completely separate process |
| Port isolation | ✅ Separate port (5181) from gateway (18080) and dashboard (9119) |
| HERMES_HOME isolation | ✅ Points to dev home only |
| Lifecycle independence | ✅ Start/stop independently |
| Risk to production | ✅ Zero — different process, different PID, different home |
| Framework dependency | ✅ FastAPI already in project dependencies |
| Code reuse | ✅ Directly imports existing service modules |
| **Recommendation** | **Accepted** |

### Option C: Frontend reads local files / calls CLI

| Aspect | Assessment |
|--------|-----------|
| Browser security | ❌ Browser cannot access filesystem |
| CLI stdout parsing | ❌ Fragile, no structured contract |
| Error handling | ❌ No unified error model |
| Security | ❌ No boundary between frontend and backend |
| Testability | ❌ Cannot test API contract |
| Path leakage | ❌ Would expose local paths |
| **Recommendation** | **Rejected** |

---

## Decision Details

### Server Location

New file: `hermes_cli/dev_web_api.py` (top-level module alongside existing `web_server.py`)

Why this location:
- `hermes_cli/web_server.py` already serves the React dashboard — we follow the same pattern
- Keeping it in `hermes_cli/` means it has access to all hermes modules via the existing import path
- It can be started via `hermes dev-webui-api` CLI command

### Port Allocation

| Service | Host:Port | Purpose |
|---------|-----------|---------|
| Dev WebUI Frontend | `127.0.0.1:5180` | Vite dev server |
| Dev WebUI API | `127.0.0.1:5181` | FastAPI read-only API |
| Dev Gateway | `127.0.0.1:18080` | Dev messaging gateway |
| Production Dashboard | `127.0.0.1:9119` | Production web dashboard |

### API Prefix

`/api/dev/v1/` — Clear versioning, clear dev-only scope.

### Read-Only Enforcement

1. **SessionDB:** Instantiated with `read_only=True` — SQLite opened in read-only mode (`mode=ro`)
2. **Memory Router:** Only calls functions from the documented read-only set
3. **Context Preview:** Uses `load_runtime_memory_context()` which is side-effect-free
4. **HTTP Methods:** Only `GET` and one `POST` (context preview, explicitly side-effect-free)
5. **DTO Layer:** Every response passes through a whitelist DTO transformer

### Startup Validation

```python
from gateway.dev_isolation import EXPECTED_DEV_HOME, EXPECTED_SOURCE_ROOT

def enforce_dev_api_environment():
    home = Path(os.environ.get("HERMES_HOME", "")).resolve()
    if home != EXPECTED_DEV_HOME:
        raise RuntimeError(f"Dev API requires HERMES_HOME={EXPECTED_DEV_HOME}")
```

---

## Consequences

### Positive

1. **Zero risk to production.** Different process, different PID, different HERMES_HOME, different port.
2. **No new framework dependencies.** FastAPI and uvicorn are already in `pyproject.toml`.
3. **Direct service reuse.** No subprocess, no stdout parsing, no fragile text extraction.
4. **Clear trust boundary.** DTO layer is the single boundary between internal objects and API responses.
5. **Testable.** API contract can be tested with standard FastAPI test client.
6. **Independent lifecycle.** Dev API can be restarted without affecting gateway or dashboard.

### Negative

1. **Additional process to manage.** Developers need to start the API server separately (or via script).
2. **No shared state with gateway.** Agent runtime status is read from config, not live state. This is acceptable for Phase 0C read-only.
3. **Memory data is a point-in-time snapshot.** Files are read on each request. Acceptable for dev-only use.

---

## Security Boundary

| Constraint | Implementation |
|-----------|---------------|
| Bind host | `127.0.0.1` only, never `0.0.0.0` |
| HERMES_HOME | Must equal `/Users/huangruibang/Code/hermes-home-dev` |
| CORS | Allow `http://127.0.0.1:5180` only |
| API methods | GET only, except POST /context/preview |
| Session writes | None (read_only=True on SessionDB) |
| Memory writes | None (only read functions called) |
| LLM calls | None |
| Tool execution | None |
| File system writes | None |
| Secret exposure | DTO whitelist strips all sensitive fields |
| Error details | No traceback, no paths, no SQL |
| Request size | Bounded (max query length, max limit) |

---

## Future Actions

1. **Phase 0C-02:** Implement the Dev API server skeleton
2. **Phase 0C-03:** Wire session list endpoint to real SessionDB
3. **Phase 0C-04:** Wire message endpoint to real SessionDB
4. **Phase 0C-05:** Wire memory, context, and agent endpoints
5. **Phase 0C-06:** Testing, error handling, and freeze

---

## References

- Phase 0C-01 Audit Report: `docs/webui/phase-0c-01-data-source-audit.md`
- Data Flow Design: `docs/webui/phase-0c-data-flow.md`
- API Contract: `docs/webui/dev-web-api-v1.md`
- CLAUDE.md Dev WebUI section
