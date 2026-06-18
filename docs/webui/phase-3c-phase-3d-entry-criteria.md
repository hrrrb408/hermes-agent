# Phase 3C — Phase 3D Entry Criteria

| Field | Value |
|-------|-------|
| Phase | 3C (Closeout) |
| Title | Phase 3D (Plugin Runtime) Entry Criteria |
| Status | Defined |
| Date | 2026-06-18 |

## 1. Phase 3D Planning — may enter when ALL are true

1. Phase 3C closeout is completed and pushed.
2. P0 open = 0; P1 open = 0.
3. Route governance unchanged (34 / 34 / 5 / 0 / 1 / 1).
4. Production Gateway PID 28428 unchanged (count 1).
5. No `~/.hermes` access; no production `state.db` access.
6. **Explicit user approval** to begin Phase 3D Planning.
7. Phase 3D scope is **planning only** (docs-only; no implementation).

## 2. Phase 3D Implementation — NO-GO by default

Phase 3D Implementation is **NO-GO** unless a subsequent, separately authorized
phase plans it. Until then:

- No plugin runtime implementation.
- No dynamic loading until a separate security model exists.
- No remote registry until a separate security model exists.
- No marketplace until a separate security model exists.
- No production rollout.

## 3. What Phase 3D Planning (if ever authorized) must produce

Before any Phase 3D Implementation, a planning phase must produce:

- A Phase 3D scope freeze.
- A dynamic-loading / plugin-execution threat model.
- A remote-registry / marketplace security model (or an explicit decision to
  keep them forbidden).
- A Phase 3D risk register (P0 / P1 / P2).
- A Phase 3D GO / NO-GO decision recorded by the user.

## 4. Out of scope for Phase 3D

The manual one-shot live provider execution remains **separately gated** and is
not part of Phase 3D. Production rollout is never part of Phase 3D.

## 5. Phase 3D Planning Status (2026-06-18)

The docs-only **Phase 3D Planning** (`PHASE-3D-PLANNING-001`) has now been
prepared — it produced exactly the artifacts §3 requires (a Phase 3D scope freeze,
a dynamic-loading / plugin-execution threat model, an explicit decision to keep
remote-registry / marketplace forbidden, a Phase 3D risk register, and a Phase 3D
GO / NO-GO). It did **not** implement the plugin runtime. **Phase 3D
Implementation remains NO-GO** until all entry criteria in §1 / §2 are met and the
user explicitly approves it. See [Phase 3D planning](phase-3d-planning.md),
[Phase 3D implementation entry criteria](phase-3d-implementation-entry-criteria.md),
and [Phase 3D GO / NO-GO](phase-3d-go-no-go.md).

## 6. Cross-references

- [Closeout](phase-3c-closeout.md)
- [Final GO / NO-GO](phase-3c-final-go-no-go.md)
- [Known limitations / deferred work](phase-3c-known-limitations-and-deferred-work.md)
- [Phase 3D planning](phase-3d-planning.md)
- [Closeout prompt](phase-3c-closeout-prompt.md)
