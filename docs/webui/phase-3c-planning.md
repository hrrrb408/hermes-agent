# Phase 3C Planning — Plugin / Capability Registry Scope Freeze

## Document Information

| Field | Value |
|-------|-------|
| Phase | 3C (Planning) |
| Title | Plugin / Capability Registry — Scope Freeze (Planning) |
| Status | Planning prepared — Capability Registry **not started**; no dynamic loading, no marketplace, no remote registry |
| Date | 2026-06-17 |
| Branch | `dev-huangruibang` |
| Input HEAD | `31ba0a62d838ded03b5fd38e22d71ee6811ab84b` (`chore(webui): harden provider live enablement gate`) |
| Planning ID | `PHASE-3C-PLANNING-001` |

> This is a **docs-only planning phase.** It freezes the scope, the capability
> model, the permission classes, the trust levels, the static manifest schema,
> the no-dynamic-loading policy, the tool / provider / workflow capability
> mappings, the UI / status design, the audit policy, the risk register, and the
> GO / NO-GO for a **future, separately-authorized** Phase 3C Capability
> Registry. It does **not** implement the registry, does **not** create a Python
> module, does **not** add a frontend component, does **not** add a test, does
> **not** modify `toolsets.py`, does **not** add a route, does **not** load any
> plugin, does **not** read any plugin directory, and does **not** perform any
> network call.

---

## 1. Goal

After Phase 3B-Live-Enablement and its H1 hardening shipped a default-disabled,
strict manual one-shot live gate on top of the read-only provider boundary, this
planning phase freezes the **minimal safe shape** of a future **Phase 3C —
Plugin / Capability Registry**:

- A **static, dev-only** capability registry that describes built-in tool /
  provider / workflow / sandbox / audit / system capabilities.
- A frozen **capability model** (stable IDs, categories, statuses).
- A frozen **permission-class** taxonomy (READ_ONLY → PRODUCTION_FORBIDDEN).
- A frozen **trust-level** taxonomy (BUILTIN_VERIFIED → UNKNOWN_FORBIDDEN).
- A frozen **static manifest schema** with an explicit forbidden-fields list.
- A frozen **no-dynamic-loading** policy (no importlib, no marketplace, no remote
  registry, no arbitrary-URL fetch).
- Frozen **capability mappings** for existing tools, providers, and workflows.
- A frozen **UI / status** design (read-only panel + badges; no secret leak).
- A frozen **audit policy** (capability registry events; safe fields only).
- A **risk register**, **GO / NO-GO**, **execution brief**, and **prompt draft**.

## 2. Core positioning

Phase 3C establishes a **Capability Registry** — not a Plugin Runtime.

> The Capability Registry **describes, exposes, audits, and blocks**
> capabilities. It does **not grant** permission. Real execution remains
> constrained by the existing tool policy, the approval / confirmation model,
> route governance, the provider live gate, and the workflow approval gates.

Phase 3C first version is frozen as:

- **static** capability registry
- **dev-only**
- **no dynamic loading**
- **no external marketplace**
- **no remote registry**
- **no arbitrary plugin execution**
- **no new route by default**
- **no production rollout**

## 3. Non-goals (forbidden in this planning phase)

- Implementing the Capability Registry.
- Creating any backend module (`dev_web_capability_registry*.py`).
- Creating any frontend component (`CapabilityRegistry*.vue`).
- Adding any test, smoke profile, or smoke spec.
- Modifying `toolsets.py`, runtime stores, or `state.db`.
- Adding any HTTP route, Provider route, or Tool write route.
- Enabling any plugin, or implementing dynamic loading.
- Python `importlib` / path-based plugin loading; npm dynamic loading; remote JS
  plugin loading; marketplace; remote registry; remote manifest; arbitrary-URL
  fetch; shell-command plugin; database plugin; external-HTTP plugin;
  provider-generated plugin; LLM-generated tool installed as plugin;
  self-modifying capability; auto-enable capability; production plugin.
- Reading any API key, performing any network call, or accessing `~/.hermes` /
  production `state.db`.
- Any production rollout; stopping / restarting / replacing / signaling the
  Production Gateway.

This phase is **docs-only.** Only files under `docs/webui/` are added / updated.

## 4. Scope freeze

The Phase 3C Capability Registry scope is frozen to **Static Dev-only Capability
Registry.** See
[phase-3c-capability-registry-scope-freeze.md](phase-3c-capability-registry-scope-freeze.md).

## 5. Companion documents

| Topic | Document |
|-------|----------|
| Scope freeze | [phase-3c-capability-registry-scope-freeze.md](phase-3c-capability-registry-scope-freeze.md) |
| Capability model | [phase-3c-capability-model.md](phase-3c-capability-model.md) |
| Permission classes + trust levels | [phase-3c-capability-permission-classes.md](phase-3c-capability-permission-classes.md) |
| Static manifest schema | [phase-3c-static-manifest-schema.md](phase-3c-static-manifest-schema.md) |
| No dynamic loading policy | [phase-3c-no-dynamic-loading-policy.md](phase-3c-no-dynamic-loading-policy.md) |
| Tool capability mapping | [phase-3c-tool-capability-mapping.md](phase-3c-tool-capability-mapping.md) |
| Provider capability mapping | [phase-3c-provider-capability-mapping.md](phase-3c-provider-capability-mapping.md) |
| Workflow capability mapping | [phase-3c-workflow-capability-mapping.md](phase-3c-workflow-capability-mapping.md) |
| UI / status design | [phase-3c-ui-and-status-design.md](phase-3c-ui-and-status-design.md) |
| Audit policy | [phase-3c-capability-audit-policy.md](phase-3c-capability-audit-policy.md) |
| Risk register | [phase-3c-security-risk-register.md](phase-3c-security-risk-register.md) |
| GO / NO-GO | [phase-3c-go-no-go.md](phase-3c-go-no-go.md) |
| Execution brief | [phase-3c-execution-brief.md](phase-3c-execution-brief.md) |
| Prompt draft | [phase-3c-prompt.md](phase-3c-prompt.md) |
| Threat model (optional) | [phase-3c-capability-threat-model.md](phase-3c-capability-threat-model.md) |
| Test strategy (optional) | [phase-3c-capability-registry-test-strategy.md](phase-3c-capability-registry-test-strategy.md) |
| UI wireframe (optional) | [phase-3c-capability-registry-ui-wireframe.md](phase-3c-capability-registry-ui-wireframe.md) |

## 6. GO / NO-GO summary

- **GO** for preparing the Phase 3C **implementation prompt only.**
- **NO-GO** for a dynamic plugin runtime.
- **NO-GO** for external plugin loading.
- **NO-GO** for production rollout.
- **NO-GO** for provider write.
- **NO-GO** for autonomous write.

See [phase-3c-go-no-go.md](phase-3c-go-no-go.md).

## 7. Production safety

Production Gateway PID `28428` was not stopped / restarted / replaced / signaled /
reconfigured. Dev services bind `127.0.0.1` only. No `~/.hermes` access; no
production `state.db` access. Route governance unchanged (34 / 34 / 5 / 0 / 1 / 1).
No plugin was loaded; no plugin directory was read; no network call was made.

## 8. Cross-references

- [Phase 3 planning](phase-3-planning.md)
- [Phase 3 scope freeze](phase-3-scope-freeze.md)
- [Phase 3 GO / NO-GO](phase-3-go-no-go.md)
- [Phase 3B-Live-Enablement H1 hardening](phase-3b-live-h1-hardening.md)
- [Phase 3B security boundary](phase-3b-security-boundary.md)
