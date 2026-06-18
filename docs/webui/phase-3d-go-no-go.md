# Phase 3D — GO / NO-GO

| Field | Value |
|-------|-------|
| Phase | 3D (Planning) |
| Title | Plugin Runtime — GO / NO-GO |
| Status | Decision recorded |
| Date | 2026-06-18 |
| Branch | `dev-huangruibang` |
| Planning ID | `PHASE-3D-PLANNING-001` |
| Decision ID | `PHASE-3D-GO-NOGO-001` |

## 1. Decision

| Item | Decision |
|------|----------|
| Phase 3D Planning completion | **GO** |
| Phase 3D Implementation prompt preparation (after explicit user request) | **GO** |
| Phase 3D Implementation by default | **NO-GO** |
| Plugin runtime implementation | **NO-GO** |
| Dynamic loading | **NO-GO** |
| Local plugin directory loading | **NO-GO** |
| Remote registry | **NO-GO** |
| Marketplace | **NO-GO** |
| External plugin fetch | **NO-GO** |
| Provider-generated plugin | **NO-GO** |
| LLM-generated plugin install | **NO-GO** |
| Shell execution | **NO-GO** |
| Database mutation | **NO-GO** |
| External HTTP execution | **NO-GO** |
| Production operation | **NO-GO** |
| Provider write | **NO-GO** |
| Autonomous write | **NO-GO** |
| Production rollout | **NO-GO** |

## 2. What GO authorizes

GO authorizes **completing** this docs-only Phase 3D Planning phase only:

- Authoring the Phase 3D planning + companion documents.
- Authoring the Phase 3D execution brief
  ([phase-3d-execution-brief.md](phase-3d-execution-brief.md)).
- Authoring the Phase 3D prompt draft
  ([phase-3d-prompt.md](phase-3d-prompt.md)).
- Committing and pushing this docs-only planning phase
  (`docs(webui): plan phase 3d plugin runtime`).

## 3. What GO does NOT authorize

```
Phase 3D Planning completion does not authorize Phase 3D Implementation.
Phase 3D Implementation requires a separate explicit user request.
```

GO does **not** authorize: implementing the plugin runtime; dynamic loading;
local plugin directory loading; remote registry; marketplace; external plugin
fetch; provider-generated plugin; LLM-generated plugin install; shell execution;
database mutation; external HTTP execution; production operation; provider write;
autonomous write; production rollout; any product / frontend / backend / script /
test change; any new route; any `~/.hermes` / production `state.db` access; any
Production Gateway stop / restart / replace / signal.

## 4. Basis

Phase 3C shipped and closed a static, dev-only, read-only, descriptive Capability
Registry (12 / 12 hardening lenses PASS, P0 = 0, P1 = 0). Phase 3D Planning
freezes a future dev-only, static, reviewed, capability-bound plugin descriptor
architecture without implementing it. Route governance is unchanged; production
is untouched.

## 5. Explicit constraints

- **Phase 3D Planning completion does not authorize Phase 3D Implementation.**
- **Phase 3D Implementation requires a separate explicit approval.**
- **Manual one-shot live provider execution remains separately gated** and is not
  part of Phase 3D.

## 6. Cross-references

- [Phase 3D planning](phase-3d-planning.md)
- [Phase 3D implementation entry criteria](phase-3d-implementation-entry-criteria.md)
- [Phase 3D risk register](phase-3d-risk-register.md)
- [Phase 3C final GO / NO-GO](phase-3c-final-go-no-go.md)
- [Phase 3C Phase 3D entry criteria](phase-3c-phase-3d-entry-criteria.md)
