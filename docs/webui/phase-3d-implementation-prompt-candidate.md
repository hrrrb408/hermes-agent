# Phase 3D — Implementation Prompt Candidate

| Field | Value |
|-------|-------|
| Phase | 3D (Planning Closeout) |
| Title | Plugin Runtime — Implementation Prompt Candidate (Draft) |
| Status | Candidate — implementation **not started** |
| Date | 2026-06-18 |
| Candidate ID | `PHASE-3D-IMPL-PROMPT-CANDIDATE-001` |

> This is an **implementation prompt candidate.** It is **not executed** during
> closeout. Implementation requires an explicit user request and separate
> authorization. The first implementation must be a **static descriptor registry
> skeleton only**.

```
This prompt candidate must not be executed during closeout.
```

## 1. Candidate allowed scope (first implementation, if separately authorized)

```
static dev-only plugin descriptor registry skeleton
descriptor schema
descriptor validation
descriptor to Phase 3C capability binding
descriptor trust classification
descriptor permission inheritance (≤ bound capability class)
descriptor disabled-by-default status
descriptor no-leak sanitizer
descriptor audit events
existing /status read-only block extension if no route drift
read-only UI panel if no new route
tests
smoke
docs
```

## 2. Candidate still-forbidden scope

```
plugin code execution
plugin loader execution
dynamic import
importlib
__import__
local plugin directory loading
remote registry
marketplace
external plugin fetch
provider-generated plugin
LLM-generated plugin install
shell execution
DB mutation
external HTTP execution
production operation
provider write
autonomous write
production rollout
new route unless separately approved
```

## 3. Boundary invariants the candidate must hold

1. Descriptor-only — grants no permission; declares, binds, classifies, exposes,
   audits, blocks.
2. Static + tracked + deterministic — no code pointer / callable / import path /
   shell command / external URL / install hook / SQL / secret / local path /
   remote URL.
3. No dynamic loading.
4. Capability-bound to existing Phase 3C IDs; permission class ≤ bound class.
5. dev-only; `productionAllowed=false`; disabled by default.
6. No new route by default (34 / 34 / 5 / 0 / 1 / 1).
7. No leak across descriptor / read model / audit / UI.
8. Audit: `plugin_*` events, safe fields, `redactionApplied=true`, dual-write,
   fail-closed.
9. Production untouched: PID `28428`, count `1`; no `~/.hermes` / production
   `state.db` access; no runtime artifacts / `.claude/` committed.

## 4. Pre-flight (re-affirm before any implementation)

```
branch = dev-huangruibang
HERMES_HOME = /Users/huangruibang/Code/hermes-home-dev
Production Gateway PID = 28428, count = 1
Dev Gateway = stopped; 5180 / 5181 free
route governance = 34 / 34 / 5 / 0 / 1 / 1
```

## 5. Suggested commit (future implementation)

```
feat(webui): add static dev plugin descriptor registry
```

## 6. Cross-references

- [Phase 3D prompt draft (planning)](phase-3d-prompt.md)
- [Phase 3D execution brief](phase-3d-execution-brief.md)
- [Implementation readiness review](phase-3d-implementation-readiness-review.md)
- [Implementation entry criteria](phase-3d-implementation-entry-criteria.md)
- [Final security boundary](phase-3d-final-security-boundary.md)
