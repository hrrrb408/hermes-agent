# Phase 3C Prompt Draft — Static Dev-only Capability Registry

> This is an **implementation prompt draft.** It is not executed in this planning
> phase. **Phase 3C implementation requires an explicit user request and separate
> authorization.** The first implementation must be a **static capability
> registry only**: no dynamic loading, no marketplace, no remote registry, no
> production rollout, no new route by default.

## Document Information

| Field | Value |
|-------|-------|
| Phase | 3C |
| Title | Static Dev-only Capability Registry (Prompt Draft) |
| Status | Draft — implementation **not started** |
| Date | 2026-06-17 |
| Branch | `dev-huangruibang` |
| Planning ID | `PHASE-3C-PLANNING-001` |
| Brief ID | `PHASE-3C-EXECUTION-BRIEF-001` |

---

## Allowed scope (first implementation, if separately authorized)

```
static capability registry module
static manifest validation (frozen forbidden-fields list)
capability classification (permissionClass + trustLevel + status)
capability status in the existing /status response (no new route)
frontend read-only registry panel + detail drawer
capability_registry_* audit (loaded / viewed / blocked / classified)
backend + frontend tests + a no-leak test + a route-governance contract test
smoke profile + spec
docs closeout
```

## Still forbidden (first implementation)

```
dynamic plugin runtime
plugin marketplace
remote registry
external plugin fetch
provider-generated plugin
LLM-generated tool installed as plugin
self-modifying capability
auto-enable / trust auto-upgrade
shell / db / external HTTP capability
production operation
new route unless separately approved
reading any API key
any network call
~/.hermes access
production state.db access
```

## Boundary invariants the implementation must hold

1. The registry is **descriptive** — it grants no permission; it labels, exposes,
   audits, and blocks.
2. The manifest is **static + tracked + deterministic** — no code pointer, no
   callable, no import path, no shell command, no external URL, no SQL, no secret.
3. **No dynamic loading** — no `importlib`, no path load, no marketplace, no
   remote registry, no remote manifest, no arbitrary-URL fetch.
4. **dev-only** — every capability is `devOnly=true`, `productionAllowed=false`.
5. **No new route by default** — status rides the existing `/status` block; route
   governance stays 34 / 34 / 5 / 0 / 1 / 1.
6. **No leak** — registry / UI / audit never carry an API key, Authorization,
   bearer token, raw token hash, callable repr, production path, local plugin
   path, dynamic import path, shell command, or SQL.
7. **Audit** — every load / validate / view / block / classification writes a
   `capability_registry_*` event (safe fields only, `redactionApplied=true`,
   dual-write, fail-closed).
8. **Production untouched** — PID `28428`, count `1`; no `~/.hermes` / production
   `state.db` access; no runtime artifacts / `.claude/` committed.

## Pre-flight (re-affirm before any implementation)

```
branch = dev-huangruibang
input HEAD = 31ba0a62d838ded03b5fd38e22d71ee6811ab84b
HERMES_HOME = /Users/huangruibang/Code/hermes-home-dev
Production Gateway PID = 28428, count = 1
Dev Gateway = stopped; 5180 / 5181 free
route governance = 34 / 34 / 5 / 0 / 1 / 1
```

## Reference documents

- [Phase 3C execution brief](phase-3c-execution-brief.md)
- [Phase 3C scope freeze](phase-3c-capability-registry-scope-freeze.md)
- [Phase 3C capability model](phase-3c-capability-model.md)
- [Phase 3C permission classes + trust levels](phase-3c-capability-permission-classes.md)
- [Phase 3C static manifest schema](phase-3c-static-manifest-schema.md)
- [Phase 3C no dynamic loading policy](phase-3c-no-dynamic-loading-policy.md)
- [Phase 3C tool / provider / workflow mappings](phase-3c-tool-capability-mapping.md)
- [Phase 3C UI & status design](phase-3c-ui-and-status-design.md)
- [Phase 3C audit policy](phase-3c-capability-audit-policy.md)
- [Phase 3C risk register](phase-3c-security-risk-register.md)
- [Phase 3C GO / NO-GO](phase-3c-go-no-go.md)

## Suggested commit (future implementation)

```
feat(webui): add static dev capability registry
```
