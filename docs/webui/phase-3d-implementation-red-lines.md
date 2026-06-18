# Phase 3D — Implementation Red Lines (Optional)

| Field | Value |
|-------|-------|
| Phase | 3D (Planning Closeout) |
| Title | Plugin Runtime — Implementation Red Lines (Non-negotiable) |
| Status | Optional companion |
| Date | 2026-06-18 |

> The non-negotiable red lines any future Phase 3D implementation must not cross.
> Crossing any one is a P0 stop condition (see [phase-3d-risk-register.md](phase-3d-risk-register.md)).

## 1. Red lines

1. **No plugin code execution** — descriptors carry no executable code.
2. **No plugin loader** — nothing loads plugin code.
3. **No dynamic loading** — no `importlib` / `__import__` / path load / `pkgutil`
   walk.
4. **No local plugin directory loading** — no scanning of user / `plugins/`
   directories.
5. **No remote registry / marketplace / external plugin fetch.**
6. **No provider-generated plugin / LLM-generated plugin install.**
7. **No shell / DB mutation / external HTTP / production execution.**
8. **No provider write / autonomous write.**
9. **No permission escalation** — descriptor permission class ≤ bound capability
   class.
10. **No self-authorization / no auto-enable / no trust auto-upgrade.**
11. **No new route by default** — route governance stays 34 / 34 / 5 / 0 / 1 / 1.
12. **No secret / callable / path / command leak** — across descriptor / read
    model / audit / UI.
13. **No audit bypass** — every lifecycle event audited, fail-closed.
14. **No `~/.hermes` access / no production `state.db` access.**
15. **No runtime artifacts / `.claude/` committed.**
16. **No production rollout / no Production Gateway interference** — PID `28428`
    untouched.

## 2. If a red line is crossed

Stop. Do not push. Do not proceed. Record a P0 stop condition in
[phase-3d-risk-register.md](phase-3d-risk-register.md) and seek explicit
re-approval.

## 3. Cross-references

- [Final security boundary](phase-3d-final-security-boundary.md)
- [Implementation red lines → risk register](phase-3d-risk-register.md)
- [Implementation entry criteria](phase-3d-implementation-entry-criteria.md)
