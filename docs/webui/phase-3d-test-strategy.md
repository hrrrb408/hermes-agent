# Phase 3D — Test Strategy

| Field | Value |
|-------|-------|
| Phase | 3D (Planning) |
| Title | Plugin Runtime — Test Strategy (Frozen) |
| Status | Frozen (docs-only planning; Plugin Runtime **not started**) |
| Date | 2026-06-18 |
| Planning ID | `PHASE-3D-PLANNING-001` |
| Strategy ID | `PHASE-3D-TEST-STRATEGY-001` |

> This document plans the **future** test strategy for a Phase 3D Plugin Runtime.
> **This planning phase adds no test code.** The categories below describe what a
> separately-authorized future implementation must cover.

## 1. Future test categories

- **docs-only planning gates** — verify this planning phase is docs-only.
- **manifest forbidden-field tests** — every forbidden field is rejected at any
  depth (recursive + scalar type guard), mirroring Phase 3C-H1.
- **descriptor validation tests** — schema, required fields, duplicate `pluginId`,
  taxonomy membership, `productionAllowed=false`.
- **non-grant tests** — a descriptor grants no permission; cannot create an
  approval / confirmation token / rollback manifest; cannot bypass audit.
- **no-dynamic-loading AST tests** — no `importlib` / `__import__` /
  `spec_from_file_location` / path-load call path in any plugin module.
- **no-remote-registry tests** — no remote fetch / arbitrary-URL fetch /
  marketplace path.
- **no-marketplace tests** — no marketplace code path.
- **no-provider-generated-plugin tests** — provider responses cannot mutate the
  descriptor set.
- **no-workflow-created-plugin tests** — workflows cannot create / enable /
  execute a plugin.
- **audit no-leak tests** — no `plugin_*` event carries a secret / callable repr
  / path / command / URL; `redactionApplied = true`; fail-closed.
- **UI no-leak tests** — the descriptor list / drawer / status block surface no
  secret / callable repr / path / command / URL in any state.
- **route governance tests** — `test_dev_check_webui.py` +
  `test_dev_web_0c06_closure.py` (34 / 34 / 5 / 0 / 1 / 1); no new route.
- **production isolation tests** — no `~/.hermes` access; no production `state.db`
  access; PID `28428` untouched.
- **smoke tests** — a new additive smoke profile + spec (if a future
  implementation adds a surface); zero regression on existing profiles.
- **preservation tests** — the Phase 1G / 2 / 3A / 3B / 3C controlled-execution
  chain stays green.

## 2. This planning phase adds no test code

Phase 3D Planning is docs-only. No test file, smoke profile, or smoke spec is
added. The categories above govern a **future** implementation.

## 3. Capability-binding tests (future)

- A descriptor's `capabilityBindings` must resolve to existing Phase 3C capability
  IDs.
- A descriptor's permission class cannot exceed its bound capability's class.
- A descriptor bound to a terminal/forbidden capability is blocked.

## 4. Smoke strategy (future)

If a future implementation adds a UI surface, a new additive smoke profile (e.g.
`phase3d_plugin_descriptor`) is wired into the `all` target, mirroring the Phase
3C Profile P / Q addition. Existing profiles must keep passing.

## 5. Cross-references

- [Phase 3D planning](phase-3d-planning.md)
- [Phase 3D risk register](phase-3d-risk-register.md)
- [Phase 3C capability registry test strategy](phase-3c-capability-registry-test-strategy.md)
- [Phase 3C test gate summary](phase-3c-test-gate-summary.md)
