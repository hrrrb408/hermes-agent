# Phase 3I — Runtime Descriptor Registry Integration (Evidence)

> **Status: dev-only partial evidence. NOT a closeout, NOT a signoff, NOT an
> archive, NOT a review-board decision, NOT a production authorization.**
>
> This document records that the integration was implemented and verified
> against the dev-only fixture runtime. It resolves no P0 gate and authorizes
> nothing for production or any real external runtime.

## What this is

This task integrates the **Phase 3D Static Plugin Descriptor Registry** with the
**Phase 3I Dev-only Local Plugin Runtime MVP**. A *descriptor* is not an
executable plugin — it is a static, reviewed record. The integration binds a
**reviewed fixture descriptor** to the runtime's frozen fixture allowlist
through a strict, fail-closed, dual-layer validation, and only then invokes the
existing dev-only runtime (`run_dev_plugin`).

The binding layer lives in
[`hermes_cli/dev_web_plugin_runtime_binding.py`](../../hermes_cli/dev_web_plugin_runtime_binding.py).

## What it does

- Reads / references a descriptor from the static descriptor registry (an
  in-memory reviewed fixture descriptor table).
- Allows **only** a descriptor that passes registry-level validation **and**
  runtime-level binding to enter the runtime.
- Binds the descriptor's `(pluginId, operation)` to the hardcoded
  `FIXTURE_ALLOWLIST` (exact membership only).
- Executes the bound reviewed fixture via the existing `run_dev_plugin`, so
  every Phase 3H guard (filesystem / network / secret / kill-switch /
  capability default-deny / redaction / P0 evidence) is enforced unchanged.
- Records the descriptor id and the `static_descriptor_registry` source in the
  redacted, in-memory audit.

## Explicit non-goals (still not authorized)

The integration intentionally does **not** enable any of the following. Each
remains NO-GO / not-authorized regardless of any descriptor, request, or
metadata:

- Arbitrary plugin loading (no `importlib` / `__import__` / path-based load).
- Local plugin directory loading outside the fixture allowlist.
- Remote registry / remote manifest fetch.
- Marketplace.
- External plugin fetch / external network of any kind.
- Provider-generated plugin install.
- LLM-generated plugin install.
- Real API-key reading.
- A new HTTP / OpenAPI route (the binding module is **not** imported by
  `dev_web_api.py`).
- Production rollout / production access.
- `~/.hermes` access (not even metadata-only `stat` / `ls` / `resolve`).
- Production `state.db` access.
- Persistent runtime artifacts / runtime store writes.

A descriptor may **never** carry a `module` / `command` / `entrypoint` / `path` /
`url` / `registry` / `marketplace` / `remote` / `fetch` / provider-generated /
LLM-generated / `dockerImage` / `install` field — at any depth, any casing. Such
a descriptor is denied outright before any fixture runs.

## Authorization boundary (unchanged)

| Boundary | Status |
|----------|--------|
| Implementation Authorization | **NO-GO** |
| Phase 3I production authorization | **NOT AUTHORIZED** (`False`) |
| Real runtime authorization | **NO-GO** |
| New route | **NO-GO** |
| Production rollout | **NO-GO** |
| P0 `resolved_count` | **0** (unchanged; 24 gates, none resolved) |

A successful descriptor-backed fixture execution is **dev-only partial
evidence** only. It is never Implementation Authorization GO, never Phase 3I
production authorization, never real-runtime authorization, never a P0
resolution.

## Verification

- New suite: `tests/test_dev_web_phase_3i_descriptor_runtime_integration.py`
  (registry discovery, descriptor-only preservation, binding happy / denied
  paths, nested dangerous fields, metadata smuggling, batch isolation, tamper
  resistance, source boundary, `dev_web_api` isolation, production safety, P0
  integration, proof scenarios).
- New proof-scenario block: `DESCRIPTOR_REGISTRY_PROOF_SCENARIOS` (5 scenarios,
  kept separate from the frozen `FIXED_SCENARIOS` (22) /
  `RUNTIME_PROOF_SCENARIOS` (5) / `RUNTIME_EXPANSION_PROOF_SCENARIOS` (4)
  libraries, whose regression counts are unchanged).
- Route governance unchanged: `34/34/5/0/1/1` (OpenAPI paths 34, runtime routes
  34, tool GET 5, tool write HTTP route 0, tool dry-run route 1, tool execution
  route 1; no new HTTP / tool-write / provider / plugin / runtime route).
- `memory-check` PASS; `dev-check` PASS (dirty-worktree WARN only).

## How to run

```bash
scripts/run_tests.sh tests/test_dev_web_phase_3i_descriptor_runtime_integration.py
```
