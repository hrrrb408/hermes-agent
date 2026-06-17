# Phase 3C Execution Brief — Static Dev-only Capability Registry

## Document Information

| Field | Value |
|-------|-------|
| Phase | 3C |
| Title | Static Dev-only Capability Registry (Execution Brief) |
| Status | Brief prepared — Capability Registry **not started** |
| Date | 2026-06-17 |
| Branch | `dev-huangruibang` |
| Planning ID | `PHASE-3C-PLANNING-001` |
| Brief ID | `PHASE-3C-EXECUTION-BRIEF-001` |

> This brief is the one-page contract for a future, separately-authorized
> Phase 3C. **The Capability Registry is not started by this planning phase.**
> The full copy-paste prompt is [phase-3c-prompt.md](phase-3c-prompt.md).

---

## 1. Name

Static Dev-only Capability Registry.

## 2. Goal

Ship a **static, tracked, deterministic, dev-only** Capability Registry that
describes the system's built-in tool / provider / workflow / sandbox / audit /
system capabilities, classifies each by a frozen permission class and trust
level, validates a static manifest against a forbidden-fields list, exposes a
read-only view, and audits registry load / view / block. The registry grants no
permission and loads no code.

## 3. Scope (allowed, future)

- A static capability registry module (single tracked Python file, e.g.
  `hermes_cli/dev_web_capability_registry.py`) holding the manifest data.
- Static manifest validation with the frozen forbidden-fields list
  ([phase-3c-static-manifest-schema.md](phase-3c-static-manifest-schema.md)).
- Capability classification (permissionClass + trustLevel + status).
- Capability status surfaced inside the **existing** `/status` response only if
  no new route is required (`capabilityRegistry` block, value-free markers).
- Frontend read-only Capability Registry panel + detail drawer (additive).
- `capability_registry_*` audit events (safe fields only, dual-write, fail-closed).
- Backend + frontend unit / contract tests; a no-leak test; a route-governance
  contract test.
- A new additive smoke profile + spec.

## 4. Non-goals (forbidden)

Dynamic plugin runtime; dynamic loading (`importlib`, path load, npm / remote JS
plugin); marketplace; remote registry; remote manifest; arbitrary-URL fetch;
shell-command / database / external-HTTP plugin; provider-generated plugin;
LLM-generated tool installed as plugin; self-modifying capability; auto-enable;
trust auto-upgrade; provider write / auto-write / autonomous write; production
rollout; `~/.hermes` access; production `state.db` access; a new HTTP route /
Provider route / Tool write route by default; reading any API key; any network
call.

## 5. Inputs

- Baseline: `31ba0a62d838ded03b5fd38e22d71ee6811ab84b` (Phase 3B-Live-H1).
- HERMES_HOME: `/Users/huangruibang/Code/hermes-home-dev`.
- Reused surfaces: Phase 2A read-only allowlist, Phase 2C / 2C-H1 write +
  rollback confirmation, Phase 2D durable audit store, Phase 3A workflow
  approval gates, Phase 3B / 3B-Live provider boundary.

## 6. Outputs

- A static, validated capability registry manifest module.
- A `capabilityRegistry` status block under the existing `/status` (no new route).
- A read-only frontend Capability Registry panel + drawer.
- `capability_registry_*` audit events dual-written to the Phase 2D store + dev
  JSONL.
- Phase 3C closeout docs.

## 7. Capability mappings

Tool / provider / workflow mappings are frozen in
[phase-3c-tool-capability-mapping.md](phase-3c-tool-capability-mapping.md),
[phase-3c-provider-capability-mapping.md](phase-3c-provider-capability-mapping.md),
[phase-3c-workflow-capability-mapping.md](phase-3c-workflow-capability-mapping.md).
The implementation must declare exactly these mappings and not invent new
executable capabilities.

## 8. Permission / trust

Frozen in [phase-3c-capability-permission-classes.md](phase-3c-capability-permission-classes.md).
Every capability is `devOnly=true`, `productionAllowed=false`. Forbidden classes
are terminal and non-executable.

## 9. Risk gates

P0 stop conditions and P1 push-gates from
[phase-3c-security-risk-register.md](phase-3c-security-risk-register.md).

## 10. Commit message (this planning phase)

```
docs(webui): plan phase 3c capability registry
```

The future implementation uses its own conventional commit, e.g.
`feat(webui): add static dev capability registry`.

## 11. Final report format

A closeout report mirroring the Phase 3B / 3B-Live structure: scope, what
changed, what did not change, route governance, production safety, gates,
residual risks (P2), conclusion.

## 12. Phase 3C implementation must NOT start here

This brief is the contract for a future, separately-authorized phase. It does not
start the Capability Registry. The copy-paste prompt lives at
[phase-3c-prompt.md](phase-3c-prompt.md).

## 13. Cross-references

- [Phase 3C planning](phase-3c-planning.md)
- [Phase 3C GO / NO-GO](phase-3c-go-no-go.md)
- [Phase 3C prompt draft](phase-3c-prompt.md)
