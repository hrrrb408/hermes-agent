# Phase 3F Planning Prompt

| Field | Value |
|-------|-------|
| Phase | 3F (Planning) |
| Title | Real Plugin Runtime — Phase 3F Planning Prompt (archived) |
| Prompt ID | `PHASE-3F-PROMPT-001` |
| Date | 2026-06-19 |
| Branch | `dev-huangruibang` |
| Status | Docs-only archived prompt — does **not** authorize implementation |

> This document is docs-only.
> This document archives the planning prompt only.
> This document does not authorize implementation.
> This document does not authorize real plugin runtime.
> This document does not authorize plugin execution.
> This document does not authorize dynamic loading.
> This document does not authorize production rollout.
> This document does not authorize new routes.

## 1. Task instruction (summary)

Start Phase 3F Planning as an authorized docs-only planning task and produce a
real-plugin-runtime **implementation readiness roadmap** without implementing
anything. Decide what must be planned, reviewed, decomposed, proven, tested, and
approved before any future real plugin runtime implementation can even be
considered.

## 2. Scope

- Add or update Markdown documentation under `docs/webui/` only.
- Create the Phase 3F planning package (15 deliverables).
- Produce an implementation readiness roadmap, gap analysis, future subphase
  decomposition, P0 gate consolidation, implementation entry review, test
  strategy planning, route governance planning, production isolation planning,
  audit/redaction planning, UI/review-flow planning, human review plan, GO/NO-GO,
  risk register, and this archived prompt.
- Run read-only validation commands and existing tests/checks that do not mutate
  runtime state.
- Commit and push documentation-only changes after validation.

## 3. Forbidden work (summary)

Do not authorize or implement: Phase 3F Implementation, Phase 3E Implementation,
real plugin runtime, plugin loader, plugin execution, dynamic loading, `importlib`
runtime loading, `__import__` runtime loading, local plugin directory loading,
remote registry, marketplace, external plugin fetch, provider-generated plugin,
LLM-generated plugin install, shell execution, database mutation, external HTTP
execution, production operation, provider write, autonomous write, live provider
execution, real API-key read, external network, new route, or production rollout.

Do not modify product/frontend/backend/test/script/runtime/config/route files.
Do not create runtime artifacts or plugin stores. Do not touch `~/.hermes` or
production `state.db`. Do not stage or commit `.claude`.

## 4. Deliverables (summary)

The 15 Phase 3F planning documents listed in
[phase-3f-planning](phase-3f-planning.md) §F, plus minimal cross-reference
updates to the Phase 3F authorization, boundary, Phase 3 GO/NO-GO, and Phase 3E
archive docs.

## 5. Validation (summary)

- Git validation: only intended `docs/webui/*.md` changed; `.claude` not staged.
- Boundary search: no secrets, runtime artifacts, implementation/route
  authorization.
- Route governance: counts unchanged at 34 / 34 / 5 / 0 / 1 / 1.
- `memory-check` PASS; `dev-check` WARN only on dirty worktree / untracked
  `.claude`.
- Production safety: PID 28428 unchanged; ports 5180/5181 free; no `~/.hermes`
  or production `state.db` access.

## 6. Acceptance criteria (summary)

All new docs under `docs/webui`; only docs modified; all 15 deliverables created;
existing docs only minimally cross-referenced; Phase 3F Planning docs-only;
Phase 3F Implementation not authorized; real plugin runtime not authorized; no
product/test/runtime/route changes; route counts unchanged; no production
process affected; `.claude` not staged/committed; pushed to
`origin/dev-huangruibang` with local == remote and ahead/behind 0/0.

## 7. Safety statement

```
This prompt is documentation only.
It contains no secrets, no executable implementation code, and no runtime code.
It authorizes no implementation, runtime, route, or production rollout.
```

## Cross-references

- [Phase 3F planning](phase-3f-planning.md)
- [Phase 3F GO / NO-GO](phase-3f-go-no-go.md)
- [Phase 3F planning authorization](phase-3f-planning-authorization.md)
- [Phase 3E archive index](phase-3e-archive-index.md)
