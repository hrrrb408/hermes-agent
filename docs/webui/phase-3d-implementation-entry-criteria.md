# Phase 3D — Implementation Entry Criteria

| Field | Value |
|-------|-------|
| Phase | 3D (Planning) |
| Title | Plugin Runtime Implementation Entry Criteria |
| Status | Defined |
| Date | 2026-06-18 |
| Planning ID | `PHASE-3D-PLANNING-001` |
| Criteria ID | `PHASE-3D-IMPL-ENTRY-001` |

## 1. Phase 3D Implementation — NO-GO until ALL are true

Phase 3D Implementation may start only when **all** of the following hold:

1. Phase 3D Planning is completed and pushed.
2. P0 open = 0; P1 open = 0.
3. Route governance unchanged (34 / 34 / 5 / 0 / 1 / 1).
4. Production Gateway PID `28428` unchanged (count 1).
5. No `~/.hermes` access; no production `state.db` access.
6. **Explicit user approval** to begin Phase 3D Implementation.
7. The Phase 3D implementation prompt is reviewed.
8. Scope is limited to a **static dev-only descriptor runtime skeleton**.
9. No dynamic loading.
10. No remote registry.
11. No marketplace.
12. No external plugin execution.
13. No production rollout.

```
Implementation remains NO-GO until all conditions are met.
```

## 2. What the first implementation may contain (if separately authorized)

- A static dev-only plugin descriptor registry module.
- A plugin descriptor schema + validation (recursive forbidden-field scan +
  scalar type guard).
- Plugin descriptor → capability binding (to existing Phase 3C IDs).
- A read-only `/status` block extension **only if no route drift**.
- A read-only UI planning panel.
- `plugin_*` audit events (safe fields, dual-write, fail-closed).
- Backend + frontend tests; smoke; docs.

## 3. What the first implementation must NOT contain

Plugin code execution; dynamic import; local plugin directory loading; remote
registry; marketplace; external plugin fetch; provider-generated plugin;
LLM-generated plugin install; shell execution; DB mutation; external HTTP
execution; production operation; provider write; autonomous write; production
rollout; a new route unless separately approved.

## 4. Out of scope

Manual one-shot live provider execution remains **separately gated** and is not
part of Phase 3D. Production rollout is never part of Phase 3D.

## 5. Cross-references

- [Phase 3D planning](phase-3d-planning.md)
- [Phase 3D GO / NO-GO](phase-3d-go-no-go.md)
- [Phase 3D execution brief](phase-3d-execution-brief.md)
- [Phase 3D prompt draft](phase-3d-prompt.md)
- [Phase 3C Phase 3D entry criteria](phase-3c-phase-3d-entry-criteria.md)
