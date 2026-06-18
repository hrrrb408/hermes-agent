# Phase 3E — Process Isolation Model

| Field | Value |
|-------|-------|
| Phase | 3E (Planning) |
| Title | Real Plugin Runtime — Process Isolation Model (Frozen, Design-only) |
| Status | Frozen (docs-only planning; Real Plugin Runtime **not started**) |
| Date | 2026-06-19 |
| Planning ID | `PHASE-3E-PLANNING-001` |
| Process-Isolation ID | `PHASE-3E-PROCESS-ISOLATION-001` |

> This document designs — but does **not** implement — the process-isolation
> model a future real plugin runtime would require. No implementation is
> authorized.

## 1. Position

```
In-process execution is HIGH RISK.
Out-of-process execution may reduce risk but requires an IPC policy.
Containerized execution requires image / filesystem / network / lifecycle policy.
No implementation is authorized.
```

## 2. Process boundary

- Plugin code runs in a separate process from the host dev server (never
  in-process execution of plugin code).
- The host and the worker communicate only through a narrow, versioned IPC
  channel.
- The worker has no pointer / shared-memory access to the host.

## 3. IPC boundary

- A small, explicitly-typed message schema (request / response / lifecycle).
- No serialized code, no callable, no dynamic import path is ever carried over
  IPC.
- Every IPC message is bounded in size; oversize messages are rejected.
- The host never trusts worker-supplied capability / permission claims — it
  re-checks them against the descriptor + capability registry.

## 4. Resource limits

```
timeout   — per-dispatch wall-clock cap; kill on exceed
memory    — per-process RSS cap; kill on exceed
CPU       — per-process CPU cap; kill on exceed
file descriptors — per-process cap
```

Exceeding any limit kills the worker and records `runtime_*` audit (fail-closed).

## 5. Kill switch

- A dedicated runtime kill switch is checked **before** secret read, network, or
  dispatch — never after.
- Kill = immediate worker termination + no new dispatch + pending dispatches
  cancelled.
- Kill state is audited; the runtime fails closed when killed.

## 6. Lifecycle audit

- Process lifecycle events are audited: spawn, dispatch-start, dispatch-end,
  resource-limit-hit, kill, crash, cleanup.
- Safe fields only (see [phase-3e-audit-redaction-review](phase-3e-audit-redaction-review.md));
  no secret / callable / path / command in audit.
- Audit failure is fail-closed.

## 7. No inherited host state

```
no inherited secrets (no API key / Authorization / token)
no inherited environment (scrubbed / allowlisted env only)
no inherited filesystem (explicit dev-sandbox root only)
no inherited network egress (disabled by default; allowlist only)
no inherited privileges (non-root; no new privileges)
```

## 8. No production process access

- The worker never reaches the production `HERMES_HOME` or production `state.db`.
- `enforce_dev_environment()` allowlist is inherited; the worker is constrained
  to the dev `HERMES_HOME` sandbox.

## 9. Cross-references

- [Phase 3E planning](phase-3e-planning.md)
- [Phase 3E sandbox architecture](phase-3e-sandbox-architecture.md)
- [Phase 3E filesystem boundary model](phase-3e-filesystem-boundary-model.md)
- [Phase 3E network boundary model](phase-3e-network-boundary-model.md)
- [Phase 3E audit / redaction review](phase-3e-audit-redaction-review.md)
- [Phase 3D execution isolation model](phase-3d-execution-isolation-model.md)
