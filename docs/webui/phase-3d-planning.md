# Phase 3D Planning — Plugin Runtime Scope Freeze / Threat Model / Safety Architecture

## Document Information

| Field | Value |
|-------|-------|
| Phase | 3D (Planning) |
| Title | Plugin Runtime Planning — Scope Freeze, Threat Model, Trust Boundary, Execution Policy, Audit Policy, GO / NO-GO |
| Status | Planning prepared — Plugin Runtime **not started** |
| Date | 2026-06-18 |
| Branch | `dev-huangruibang` |
| Input HEAD | `26da46b9cf90d9f1e41c65574fbad0a545495982` (`docs(webui): close phase 3c capability registry`) |
| Planning ID | `PHASE-3D-PLANNING-001` |

> This is a **docs-only planning phase.** It freezes the scope, the threat model,
> the trust boundary, the non-goals / forbidden scope, the future plugin manifest
> contract, the plugin lifecycle model, the execution isolation model, the
> capability-registry integration, the permission / approval model, the provider /
> workflow boundary, the audit / redaction policy, the UI / status design, the
> test strategy, the risk register, and the GO / NO-GO for a **future,
> separately-authorized** Phase 3D Plugin Runtime. It does **not** implement the
> plugin runtime, does **not** create a plugin loader, does **not** perform any
> dynamic loading, does **not** create a backend module, does **not** add a
> frontend component, does **not** add a test, does **not** modify `toolsets.py`,
> does **not** add a route, does **not** read any plugin directory, and does
> **not** perform any network call.

---

## 1. Goal

After Phase 3C shipped and closed a **static, dev-only, descriptive Capability
Registry** (the descriptive layer that classifies capabilities, binds them to the
existing tool / provider / workflow surfaces, and grants no permission), this
planning phase freezes the **minimal safe shape** of a future **Phase 3D — Plugin
Runtime**:

- A future **dev-only, static, reviewed, capability-bound** plugin runtime
  architecture, described only.
- A frozen **threat model** for plugin / dynamic-loading / remote-registry /
  marketplace hazards.
- A frozen **trust boundary** (trusted_builtin_code → production_forbidden).
- A frozen **non-goals / forbidden scope** list.
- A frozen future **plugin manifest contract** (allowed + forbidden fields).
- A frozen future **plugin lifecycle model** (descriptor → visible → disabled).
- A frozen future **execution isolation model** (no shell / DB / HTTP / production).
- A frozen **capability-registry integration** (descriptors bind to Phase 3C
  capability IDs; they cannot create a new permission class).
- A frozen **permission / approval model** (descriptors grant no permission).
- A frozen **provider / workflow boundary** (no provider- or workflow-generated
  plugin).
- A frozen **audit / redaction policy** (safe fields only, fail-closed).
- A frozen **UI / status design** (read-only descriptor list; runtime disabled
  banner).
- A frozen **test strategy** (docs-only planning gates; no new test code).
- A **risk register**, **GO / NO-GO**, **implementation entry criteria**,
  **execution brief**, and **prompt draft**.

## 2. Core positioning

Phase 3D Planning defines the **architecture of a future plugin runtime** — it
does not build one.

> A future Plugin Runtime, if ever separately authorized, must remain **dev-only,
> static-descriptor-based, reviewed, capability-bound, disabled-by-default, and
> audit-only-dry-run**. It must start from static reviewed descriptors, **not**
> from executable external plugins. It grants no permission by itself; it inherits
> the existing tool policy, provider live gate, workflow approval gates,
> dry-run / confirmation / audit chain, and route governance.

Phase 3D Planning is frozen as:

- **docs-only**
- **no implementation**
- **no plugin runtime**
- **no dynamic loading**
- **no remote registry**
- **no marketplace**
- **no external plugin fetch**
- **no plugin execution**
- **no new route**
- **no production rollout**

## 3. Non-goals (forbidden in this planning phase)

- Implementing the plugin runtime or any plugin loader.
- Creating any backend module (`dev_web_plugin*.py`) or frontend component.
- Adding any test, smoke profile, or smoke spec.
- Modifying `toolsets.py`, runtime stores, or `state.db`.
- Adding any HTTP route, Provider route, or Tool write route.
- Any dynamic loading (`importlib` / `__import__` / path-based load / `pkgutil`
  walk), marketplace, remote registry, remote manifest fetch, arbitrary-URL
  fetch, shell-command plugin, database plugin, external-HTTP plugin,
  provider-generated plugin, LLM-generated tool installed as a plugin,
  self-modifying plugin, auto-enable, or production plugin.
- Reading any API key, performing any network call, or accessing `~/.hermes` /
  production `state.db`.
- Any production rollout; stopping / restarting / replacing / signaling the
  Production Gateway.

See [phase-3d-non-goals-and-forbidden-scope.md](phase-3d-non-goals-and-forbidden-scope.md).

## 4. Scope freeze

The future Phase 3D Plugin Runtime scope is frozen to **Static Dev-only Plugin
Descriptor Runtime Skeleton**. See
[phase-3d-plugin-runtime-scope-freeze.md](phase-3d-plugin-runtime-scope-freeze.md).

The future first implementation, if separately authorized, may at most consider:
a static dev-only plugin runtime skeleton; built-in reviewed plugin descriptors
only; no external plugin files; no user plugin directory; no remote plugin
registry; no marketplace; no arbitrary dynamic loading; capability-bound
execution policy; read-only registry display; audit-only dry-run lifecycle;
disabled-by-default plugin activation model.

> **Future implementation must start from static reviewed descriptors, not
> executable external plugins.**

## 5. Companion documents

| Topic | Document |
|-------|----------|
| Scope freeze | [phase-3d-plugin-runtime-scope-freeze.md](phase-3d-plugin-runtime-scope-freeze.md) |
| Threat model | [phase-3d-threat-model.md](phase-3d-threat-model.md) |
| Trust boundary | [phase-3d-trust-boundary.md](phase-3d-trust-boundary.md) |
| Non-goals / forbidden scope | [phase-3d-non-goals-and-forbidden-scope.md](phase-3d-non-goals-and-forbidden-scope.md) |
| Plugin manifest contract | [phase-3d-plugin-manifest-contract.md](phase-3d-plugin-manifest-contract.md) |
| Plugin lifecycle model | [phase-3d-plugin-lifecycle-model.md](phase-3d-plugin-lifecycle-model.md) |
| Execution isolation model | [phase-3d-execution-isolation-model.md](phase-3d-execution-isolation-model.md) |
| Capability registry integration | [phase-3d-capability-registry-integration.md](phase-3d-capability-registry-integration.md) |
| Permission / approval model | [phase-3d-permission-and-approval-model.md](phase-3d-permission-and-approval-model.md) |
| Provider / workflow boundary | [phase-3d-provider-and-workflow-boundary.md](phase-3d-provider-and-workflow-boundary.md) |
| Audit / redaction policy | [phase-3d-audit-and-redaction-policy.md](phase-3d-audit-and-redaction-policy.md) |
| UI / status design | [phase-3d-ui-and-status-design.md](phase-3d-ui-and-status-design.md) |
| Test strategy | [phase-3d-test-strategy.md](phase-3d-test-strategy.md) |
| Risk register | [phase-3d-risk-register.md](phase-3d-risk-register.md) |
| GO / NO-GO | [phase-3d-go-no-go.md](phase-3d-go-no-go.md) |
| Implementation entry criteria | [phase-3d-implementation-entry-criteria.md](phase-3d-implementation-entry-criteria.md) |
| Execution brief | [phase-3d-execution-brief.md](phase-3d-execution-brief.md) |
| Prompt draft | [phase-3d-prompt.md](phase-3d-prompt.md) |
| Human review brief (optional) | [phase-3d-human-review-brief.md](phase-3d-human-review-brief.md) |
| Security review checklist (optional) | [phase-3d-security-review-checklist.md](phase-3d-security-review-checklist.md) |
| Design alternatives (optional) | [phase-3d-design-alternatives.md](phase-3d-design-alternatives.md) |

## 6. GO / NO-GO summary

- **GO** for **completing** Phase 3D Planning (this docs-only phase).
- **GO** for preparing the Phase 3D Implementation prompt **only after an
  explicit user request**.
- **NO-GO** for Phase 3D Implementation by default.
- **NO-GO** for plugin runtime implementation.
- **NO-GO** for dynamic loading, local plugin directory loading, remote registry,
  marketplace, external plugin fetch, provider-generated plugin, LLM-generated
  plugin install, shell execution, database mutation, external HTTP execution,
  production operation, provider write, autonomous write, production rollout.

> **Planning does not equal authorization to implement.** Implementation requires
> a separate explicit user request.

See [phase-3d-go-no-go.md](phase-3d-go-no-go.md).

## 7. Production safety

Production Gateway PID `28428` was not stopped / restarted / replaced / signaled /
reconfigured (count 1). Dev services bind `127.0.0.1` only. No `~/.hermes` access;
no production `state.db` access. Route governance unchanged (34 / 34 / 5 / 0 / 1
/ 1). No plugin was loaded; no plugin directory was read; no dynamic import was
performed; no network call was made; no API key was read.

## 8. Relationship to Phase 3C

Phase 3D Planning is **additive** to the closed Phase 3C Capability Registry.
Phase 3C remains the **source of visible capability classification**. A future
plugin descriptor must **bind to existing Phase 3C capability IDs**; it cannot
create a new permission class, cannot self-authorize, and cannot bypass
capability-registry validation or forbidden-field checks. See
[phase-3d-capability-registry-integration.md](phase-3d-capability-registry-integration.md).

## 9. Cross-references

- [Phase 3C closeout](phase-3c-closeout.md)
- [Phase 3C final GO / NO-GO](phase-3c-final-go-no-go.md)
- [Phase 3C Phase 3D entry criteria](phase-3c-phase-3d-entry-criteria.md)
- [Phase 3C no dynamic loading policy](phase-3c-no-dynamic-loading-policy.md)
- [Phase 3C capability permission classes](phase-3c-capability-permission-classes.md)
- [Phase 3 planning](phase-3-planning.md)
- [Phase 3 scope freeze](phase-3-scope-freeze.md)
- [Phase 3 GO / NO-GO](phase-3-go-no-go.md)
- [Phase 3 risk register](phase-3-risk-register.md)
