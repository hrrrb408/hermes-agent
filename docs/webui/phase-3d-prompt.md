# Phase 3D Prompt Draft — Static Dev-only Plugin Descriptor Runtime Skeleton

> This is an **implementation prompt draft.** It is not executed in this planning
> phase. **Phase 3D implementation requires an explicit user request and separate
> authorization.** The first implementation must be a **static descriptor runtime
> skeleton only**: no dynamic loading, no marketplace, no remote registry, no
> external plugin execution, no production rollout, no new route by default.

## Document Information

| Field | Value |
|-------|-------|
| Phase | 3D |
| Title | Static Dev-only Plugin Descriptor Runtime Skeleton (Prompt Draft) |
| Status | Draft — implementation **not started** |
| Date | 2026-06-18 |
| Branch | `dev-huangruibang` |
| Planning ID | `PHASE-3D-PLANNING-001` |
| Brief ID | `PHASE-3D-EXECUTION-BRIEF-001` |

---

## Allowed scope (first implementation, if separately authorized)

```
static plugin descriptor module
plugin descriptor schema + validation (frozen forbidden-fields list, recursive + scalar type guard)
plugin descriptor -> capability binding (existing Phase 3C IDs only)
descriptor classification (permissionClass + trustLevel + status)
descriptor status in the existing /status response (no new route, pluginRuntime block)
frontend read-only descriptor list + detail drawer + runtime-disabled banner
plugin_* audit (declared / validated / rejected / blocked / classified / rendered / blocked-execution / runtime-disabled / no-dynamic-loading-checked / route-governance-checked)
backend + frontend tests + a no-leak test + a route-governance contract test
smoke profile + spec (only if a UI surface is added)
docs closeout
```

## Still forbidden (first implementation)

```
plugin code execution
dynamic import (importlib / __import__ / path load / pkgutil walk)
local plugin directory loading
remote registry
marketplace
external plugin fetch
provider-generated plugin
LLM-generated tool installed as plugin
self-modifying plugin
auto-enable / trust auto-upgrade
shell / db / external HTTP capability
production operation
provider write / autonomous write
new route unless separately approved
reading any API key
any network call
~/.hermes access
production state.db access
```

## Boundary invariants the implementation must hold

1. The runtime is **descriptor-based** — it grants no permission; it declares,
   binds, classifies, exposes, audits, and blocks.
2. The descriptor is **static + tracked + deterministic** — no code pointer, no
   callable, no import path, no shell command, no external URL, no install hook,
   no SQL, no secret, no local path, no remote URL.
3. **No dynamic loading** — no `importlib`, no `__import__`, no path load, no
   `pkgutil` walk, no marketplace, no remote registry, no remote manifest, no
   arbitrary-URL fetch.
4. **Capability-bound** — `capabilityBindings` references existing Phase 3C
   capability IDs only; the descriptor's permission class ≤ bound capability's
   class.
5. **dev-only** — every descriptor is `devOnly=true`, `productionAllowed=false`,
   disabled by default.
6. **No new route by default** — status rides the existing `/status` block; route
   governance stays 34 / 34 / 5 / 0 / 1 / 1.
7. **No leak** — descriptor / read model / audit / UI never carry an API key,
   Authorization, bearer token, raw token hash, callable repr, production path,
   local plugin path, dynamic import path, shell command, SQL, external URL, or
   install command.
8. **Audit** — every lifecycle event writes a `plugin_*` event (safe fields only,
   `redactionApplied=true`, dual-write, fail-closed).
9. **Production untouched** — PID `28428`, count `1`; no `~/.hermes` / production
   `state.db` access; no runtime artifacts / `.claude/` committed.

## Pre-flight (re-affirm before any implementation)

```
branch = dev-huangruibang
input HEAD = 26da46b9cf90d9f1e41c65574fbad0a545495982
HERMES_HOME = /Users/huangruibang/Code/hermes-home-dev
Production Gateway PID = 28428, count = 1
Dev Gateway = stopped; 5180 / 5181 free
route governance = 34 / 34 / 5 / 0 / 1 / 1
```

## Reference documents

- [Phase 3D execution brief](phase-3d-execution-brief.md)
- [Phase 3D scope freeze](phase-3d-plugin-runtime-scope-freeze.md)
- [Phase 3D manifest contract](phase-3d-plugin-manifest-contract.md)
- [Phase 3D lifecycle model](phase-3d-plugin-lifecycle-model.md)
- [Phase 3D trust boundary](phase-3d-trust-boundary.md)
- [Phase 3D execution isolation model](phase-3d-execution-isolation-model.md)
- [Phase 3D capability registry integration](phase-3d-capability-registry-integration.md)
- [Phase 3D permission / approval model](phase-3d-permission-and-approval-model.md)
- [Phase 3D provider / workflow boundary](phase-3d-provider-and-workflow-boundary.md)
- [Phase 3D audit / redaction policy](phase-3d-audit-and-redaction-policy.md)
- [Phase 3D UI / status design](phase-3d-ui-and-status-design.md)
- [Phase 3D threat model](phase-3d-threat-model.md)
- [Phase 3D risk register](phase-3d-risk-register.md)
- [Phase 3D GO / NO-GO](phase-3d-go-no-go.md)
- [Phase 3C capability model](phase-3c-capability-model.md)
- [Phase 3C capability permission classes](phase-3c-capability-permission-classes.md)

## Suggested commit (future implementation)

```
feat(webui): add static dev plugin descriptor runtime
```
