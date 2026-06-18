# Phase 3G Implementation Authorization Review Prompt

| Field | Value |
|-------|-------|
| Phase | 3G (Implementation Authorization Review) |
| Title | Real Plugin Runtime — Phase 3G Implementation Authorization Review Prompt (archived) |
| Prompt ID | `PHASE-3G-PROMPT-001` |
| Date | 2026-06-19 |
| Branch | `dev-huangruibang` |
| Source commit | `f9de4c395f4eb05b2f3285cb254d8b46fcd568d7` |
| Status | Docs-only archived prompt — does **not** authorize implementation |

> This document is docs-only.
> This document archives the Phase 3G review prompt only.
> This document does not authorize implementation.
> This document does not authorize real plugin runtime.
> This document does not authorize plugin execution.
> This document does not authorize dynamic loading.
> This document does not authorize production rollout.
> This document does not authorize new routes.

## 1. Task instruction (summary)

Create a Phase 3G Implementation Authorization Review package as a docs-only
review. Review whether the project is ready to authorize any implementation work
after Phase 3F. The recommended decision is that the Phase 3G review itself is
GO, while Implementation Authorization, real plugin runtime, plugin loader,
plugin execution, dynamic loading, new route, and production rollout all remain
NO-GO. Phase 3F produced a readiness roadmap, gap analysis, P0 gate
consolidation, test planning, route governance planning, and a human review
package, but did not resolve P0 gates, did not produce implementation proofs,
did not approve enforcement, did not approve route changes, did not approve
production isolation, and did not authorize runtime artifacts.

## 2. Scope (summary)

- Add or update Markdown documentation under `docs/webui/` only.
- Create the Phase 3G implementation authorization review documents.
- Create a formal implementation authorization decision document.
- Create a P0 gate resolution review.
- Create a readiness evidence review.
- Create a future safe-next-step recommendation document.
- Create Phase 3G GO/NO-GO documentation.
- Create a Phase 3G risk review.
- Update Phase 3-level GO/NO-GO documentation with minimal status changes.
- Update Phase 3F archive/index with a minimal forward pointer only if useful.
- Run read-only validation commands and existing checks that do not mutate
  runtime state.
- Commit and push documentation-only changes after validation.

## 3. Forbidden work (summary)

Do not authorize or implement: Phase 3G Implementation, Phase 3F Implementation,
Phase 3E Implementation, real plugin runtime, plugin loader, plugin execution,
dynamic loading, `importlib` runtime loading, `__import__` runtime loading,
local plugin directory loading, remote registry, marketplace, external plugin
fetch, provider-generated plugin, LLM-generated plugin install, shell execution,
database mutation, external HTTP execution, production operation, provider write,
autonomous write, live provider execution, real API-key read, external network,
new route, or production rollout.

Do not modify product/frontend/backend/test/script/runtime/config/route files.
Do not create runtime artifacts, plugin registry data, plugin store data,
runtime JSONL files, audit-store files, workflow-store files, provider-live-store
files, or capability registry stores. Do not touch `~/.hermes` or production
`state.db`. Do not stage or commit `.claude`.

## 4. Deliverables (summary)

The eight Phase 3G review documents:

- [phase-3g-implementation-authorization-review.md](phase-3g-implementation-authorization-review.md)
- [phase-3g-readiness-evidence-review.md](phase-3g-readiness-evidence-review.md)
- [phase-3g-p0-gate-resolution-review.md](phase-3g-p0-gate-resolution-review.md)
- [phase-3g-implementation-authorization-decision.md](phase-3g-implementation-authorization-decision.md)
- [phase-3g-next-step-recommendation.md](phase-3g-next-step-recommendation.md)
- [phase-3g-go-no-go.md](phase-3g-go-no-go.md)
- [phase-3g-risk-review.md](phase-3g-risk-review.md)
- [phase-3g-prompt.md](phase-3g-prompt.md)

plus minimal cross-reference updates to the Phase 3F archive index, the Phase 3
GO / NO-GO, and (only if appropriate) the Phase 3F signoff and Phase 3F GO /
NO-GO.

## 5. Validation (summary)

- Git validation: only intended `docs/webui/*.md` changed; `.claude` not staged.
- Boundary search: no secrets, runtime artifacts, or implementation / runtime /
  route / production authorization.
- Route governance: counts unchanged at 34 / 34 / 5 / 0 / 1 / 1.
- `memory-check` PASS; `dev-check` WARN only on dirty worktree / untracked
  `.claude`.
- Production safety: PID `28428` unchanged; ports 5180/5181 free; no `~/.hermes`
  or production `state.db` access.

## 6. Acceptance criteria (summary)

All new docs under `docs/webui`; only docs modified; all eight deliverables
created; existing docs only minimally cross-referenced; Phase 3G review is
docs-only; Implementation Authorization = NO-GO; Phase 3G/3F/3E Implementation
not authorized; real plugin runtime not authorized; no product/test/runtime/route
changes; route counts unchanged; no production process affected; `.claude` not
staged/committed; pushed to `origin/dev-huangruibang` with local == remote and
ahead/behind 0/0.

## 7. Safety statement

```
This prompt is documentation only.
It contains no secrets, no executable implementation code, and no runtime code.
It authorizes no implementation, runtime, route, or production rollout.
```

## Cross-references

- [Phase 3G implementation authorization review](phase-3g-implementation-authorization-review.md)
- [Phase 3G implementation authorization decision](phase-3g-implementation-authorization-decision.md)
- [Phase 3G GO / NO-GO](phase-3g-go-no-go.md)
- [Phase 3F archive index](phase-3f-archive-index.md)
- [Phase 3F prompt](phase-3f-prompt.md)
- [Phase 3 GO / NO-GO](phase-3-go-no-go.md)
