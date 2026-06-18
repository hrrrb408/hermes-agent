# Phase 3D — Human Review Brief (Optional)

| Field | Value |
|-------|-------|
| Phase | 3D (Planning) |
| Title | Plugin Runtime Planning — Human Review Brief |
| Status | Optional companion |
| Date | 2026-06-18 |
| Planning ID | `PHASE-3D-PLANNING-001` |

> **Planning Closeout (2026-06-18):** This brief is now superseded in depth by the
> closeout human-review package —
> [phase-3d-human-review-readiness.md](phase-3d-human-review-readiness.md),
> [phase-3d-human-approver-checklist.md](phase-3d-human-approver-checklist.md),
> and [phase-3d-final-go-no-go.md](phase-3d-final-go-no-go.md). Phase 3D Planning
> is closed; **Implementation remains NO-GO** until explicitly approved.

> A short brief for the human reviewer of this docs-only planning phase. It states
> what was decided, what was deliberately **not** done, and what approval is
> required next.

## 1. What this phase is

A **docs-only planning phase** that freezes the architecture of a future Plugin
Runtime — without implementing it. 23 documents were added under `docs/webui/`.

## 2. What was decided

- A future Plugin Runtime, if ever authorized, is **dev-only, static-descriptor-
  based, reviewed, capability-bound, disabled-by-default, and audit-only-dry-run**.
- It must start from **static reviewed descriptors**, not executable external
  plugins.
- It must bind to **existing Phase 3C capability IDs** and inherit their
  permission class (no escalation, no self-authorization).
- The trust boundary, manifest contract, lifecycle, execution isolation, audit
  policy, UI, test strategy, threat model, and risk register are frozen.

## 3. What was deliberately NOT done

No plugin runtime, no plugin loader, no dynamic loading, no remote registry, no
marketplace, no external plugin fetch, no provider-generated plugin, no
LLM-generated plugin install, no shell / DB / external-HTTP / production
execution, no provider write, no autonomous write, no production rollout, no new
route, no `~/.hermes` / production `state.db` access, no API key read, no network
call, no backend / frontend / test / script change.

## 4. Production safety confirmed

Production Gateway PID `28428` (count 1) was not touched. Dev services bind
`127.0.0.1`. Route governance unchanged (34 / 34 / 5 / 0 / 1 / 1).

## 5. What approval is required next

- **Phase 3D Implementation is NO-GO** until the reviewer explicitly approves it.
- Implementation, if approved, must obey
  [phase-3d-implementation-entry-criteria.md](phase-3d-implementation-entry-criteria.md)
  and the prompt draft [phase-3d-prompt.md](phase-3d-prompt.md).

## 6. Suggested review order

1. [phase-3d-planning.md](phase-3d-planning.md) — overview.
2. [phase-3d-go-no-go.md](phase-3d-go-no-go.md) — decisions.
3. [phase-3d-threat-model.md](phase-3d-threat-model.md) + [phase-3d-risk-register.md](phase-3d-risk-register.md)
   — hazards.
4. [phase-3d-plugin-runtime-scope-freeze.md](phase-3d-plugin-runtime-scope-freeze.md)
   + [phase-3d-non-goals-and-forbidden-scope.md](phase-3d-non-goals-and-forbidden-scope.md)
   — boundary.
5. [phase-3d-prompt.md](phase-3d-prompt.md) — the future implementation contract.
