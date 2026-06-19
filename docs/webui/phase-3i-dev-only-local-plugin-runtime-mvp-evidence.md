# Phase 3I — Dev-only Local Plugin Runtime MVP (Evidence)

> **Status:** implemented (dev-only MVP). **NOT a signoff. NOT a closeout. NOT an
> authorization. NOT a production plugin runtime.**
>
> Code-allowed / production-forbidden. This document is lightweight evidence for
> the Phase 3I dev-only local plugin runtime MVP. It resolves nothing on its own.

## What this implements

A **very narrow** dev-only local plugin runtime that may invoke **reviewed,
side-effect-free fixture operations** — and only those:

- `hermes_cli/dev_web_fixture_plugins.py` — three reviewed fixture operations
  (`echo_uppercase`, `summarize_keys`, `deliberate_failure`) bound to plugin ids
  `fixture.echo` / `fixture.inspect` / `fixture.fault` through a frozen
  `FIXTURE_REGISTRY` / `FIXTURE_ALLOWLIST`.
- `hermes_cli/dev_web_plugin_runtime.py` — `PluginRuntimeRequest`,
  `PluginRuntimeResult`, `PluginRuntimePolicy`, descriptor-to-fixture binding
  (`resolve_runtime_binding`), and the single entry point `run_dev_plugin()`.
- `hermes_cli/dev_web_sandbox_scenarios.py` — a **separate** fixed
  `RUNTIME_PROOF_SCENARIOS` library (5 scenarios) driven through the existing
  descriptor-only proof runner. The frozen Phase 3H `FIXED_SCENARIOS`
  (22 scenarios) is unchanged.
- `tests/test_dev_web_phase_3i_local_plugin_runtime_mvp.py` — full happy /
  denied / failure / immutability / source-boundary / API-isolation /
  production-safety / P0-integration / binding / proof-scenario coverage.

The runtime reuses the Phase 3H guards / policy / audit / evidence logic
verbatim and layers a single new capability: invoke a reviewed fixture by
allowlist binding.

## Hard scope (what the runtime IS and IS NOT)

The runtime:

- loads reviewed fixture operations **only** from the hardcoded `FIXTURE_ALLOWLIST`;
- is invoked **only** through tests / internal function calls (`run_dev_plugin`);
- produces an **in-memory**, redacted `PluginRuntimeResult` and audit record;
- enforces capability / filesystem / network / secrets / production / route /
  kill-switch guards, and a metadata authorization-smuggling denial;
- catches and redacts fixture failures (fail-closed).

The runtime does **NOT**:

- expose an HTTP route (it is **not** imported by `dev_web_api.py`);
- connect to `dev_web_api` or register any OpenAPI path;
- access production or `~/.hermes` (not even a metadata-only `stat` / `ls` /
  `resolve`);
- access the production `state.db`;
- read a real API key, `Authorization` / `Bearer` material, or a PEM private key;
- perform any external network call (no socket, no DNS, no `requests` /
  `httpx` / `aiohttp` / `urllib`);
- write a runtime store, JSONL, database, or any persistent artifact;
- support a remote registry, marketplace, or external plugin fetch;
- support arbitrary local plugin directory loading;
- support provider-generated or LLM-generated plugin install;
- load plugins via `importlib`, `__import__`, `eval`, `exec`, subprocess, or
  shell (verified by a call-pattern source boundary scan);
- equal a production plugin runtime.

## Runtime flags (frozen, all results)

```
dev_only              = true
fixture_only          = true
production_access     = false
external_network      = false
real_secret_read      = false
route_change          = false
runtime_store_write   = false
arbitrary_plugin_load = false
remote_plugin_fetch   = false
marketplace_access    = false
```

A successful fixture execution flips **none** of these. They are enforced in
`PluginRuntimeResult.__post_init__`.

## Authorization (unchanged, frozen NO-GO)

A successful fixture execution is **dev-only partial evidence only**. It is:

- **NOT** Implementation Authorization GO;
- **NOT** Phase 3I production authorization;
- **NOT** real-runtime authorization;
- **NOT** a new-route approval;
- **NOT** a production rollout approval;
- **NOT** a P0 gate resolution.

`resolved_count` stays **0**. The frozen flags remain:

| Flag | Value |
|------|-------|
| Implementation Authorization | `NO-GO` |
| Phase 3I Authorized | `False` |
| Real Runtime | `NO-GO` |
| New Route | `NO-GO` |
| Production Rollout | `NO-GO` |

Request metadata is untrusted by construction: every approval / authorization /
signoff / trust-token / route-exception / production / runtime / phase-3I /
resolved bypass key is detected and the request is denied
(`metadata_authorization_smuggling_denied`). A forged `HumanApprovalRecord`
remains invalid (the dev skeleton holds no trust token).

## Route governance (unchanged)

```
OpenAPI paths        = 34
Runtime routes       = 34
Tool GET             = 5
Tool write HTTP route = 0
Tool dry-run route   = 1
Tool execution route = 1
new HTTP route       = 0
new Tool write route = 0
new Provider route   = 0
new plugin route     = 0
new runtime route    = 0
```

The runtime is **not** imported by `dev_web_api.py`; probes for plausible runtime
paths return 404.

## P0 evidence classification

| Outcome | Classification | Resolved |
|---------|---------------|----------|
| Fixture executed successfully | `partial_evidence` | False |
| Guard denied the request | `guard_evidence` | False |
| Fixture failed (caught / redacted) | `failure_mode_evidence` | False |

All three are recorded as **partial** evidence. None advances a gate. The
24-gate registry's `resolved_count` remains 0 regardless of how many fixtures
run or how many proof scenarios pass.

## Still NOT authorized (deferred)

- production plugin runtime;
- arbitrary plugin loading;
- user-uploaded plugin;
- remote registry;
- marketplace;
- external plugin fetch;
- provider-generated plugin install;
- LLM-generated plugin install;
- real API-key reading;
- external network;
- new HTTP route;
- production rollout;
- gateway integration;
- `dev_web_api` route integration.

These require explicit, separate human authorization that no code or metadata
in this MVP can grant.
