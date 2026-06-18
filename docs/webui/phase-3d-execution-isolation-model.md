# Phase 3D — Execution Isolation Model

| Field | Value |
|-------|-------|
| Phase | 3D (Planning) |
| Title | Plugin Execution Isolation Model (Frozen) |
| Status | Frozen (docs-only planning; Plugin Runtime **not started**) |
| Date | 2026-06-18 |
| Planning ID | `PHASE-3D-PLANNING-001` |
| Isolation ID | `PHASE-3D-EXECUTION-ISOLATION-001` |

> This document freezes the execution isolation model. **Planning phase: no
> execution. Future first implementation: no external plugin execution.** Any
> plugin runtime, if ever implemented, must be isolated from shell, DB mutation,
> external HTTP, production paths, and secrets.

## 1. Planning-phase isolation

This planning phase introduces **no execution path at all.** No plugin is loaded,
no descriptor is executed, no code runs on behalf of a descriptor. The only
artifacts are docs.

## 2. Future-first-implementation isolation

The future first implementation (if separately authorized) introduces **no
external plugin execution.** A descriptor is a data structure; it is not loaded or
invoked. Any capability the descriptor *binds to* is executed **only** through the
existing capability's gates (read-only allowlist, dry-run + confirmation + audit,
provider live gate, workflow approval) — never through a plugin-specific path.

## 3. Minimum isolation gates (future implementation)

If a plugin runtime is ever implemented, it must hold:

- **no shell** — no `subprocess` / `os.system` / `shell=True`.
- **no DB mutation** — no `INSERT INTO` / `UPDATE … SET` / `DELETE FROM`; no
  production `state.db` access.
- **no external network** — no `requests` / `httpx` / `urllib` / `aiohttp` /
  `curl` from a plugin path.
- **no production path** — no `~/.hermes` access; `enforce_dev_environment()`
  allowlist enforced.
- **no secret access** — no API-key / Authorization / bearer read from env or
  config by a plugin path; secrets are read only by the existing provider live
  gate past every gate, value-free.
- **no write unless the existing WRITE_CONFIRM path** — any write rides the Phase
  2C / 2C-H1 dry-run + confirmation token + digest + audit chain.
- **no live provider unless the Phase 3B live gate** — any live provider action
  requires the Phase 3B-Live-Enablement gate (human approval + budget + kill
  switch + audit).
- **no workflow write unless Phase 3A approval** — any workflow write requires the
  workflow approval gate.
- **audit required** — every descriptor lifecycle event is audited (safe fields,
  fail-closed).
- **kill switch required** — a plugin runtime kill switch must exist and default
  disabled.

## 4. Why descriptor-only isolation

A descriptor carries no code, so it has no execution surface to isolate — it can
only *reference* an existing capability. This is the strongest possible isolation:
there is nothing to sandbox. The existing capability gates remain the sole
execution authority.

## 5. Cross-references

- [Phase 3D planning](phase-3d-planning.md)
- [Phase 3D lifecycle model](phase-3d-plugin-lifecycle-model.md)
- [Phase 3D permission / approval model](phase-3d-permission-and-approval-model.md)
- [Phase 3D provider / workflow boundary](phase-3d-provider-and-workflow-boundary.md)
- [Phase 3C final security boundary](phase-3c-security-boundary-final.md)
