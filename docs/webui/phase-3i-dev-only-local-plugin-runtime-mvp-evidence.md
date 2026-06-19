# Phase 3I — Dev-only Local Plugin Runtime MVP (Evidence)

> **Status:** implemented (dev-only MVP, expanded fixture + batch surface). **NOT
> a signoff. NOT a closeout. NOT an authorization. NOT a production plugin
> runtime.**
>
> Code-allowed / production-forbidden. This document is lightweight evidence for
> the Phase 3I dev-only local plugin runtime MVP and its expansion (additional
> reviewed fixture operations, per-operation metadata hardening, batch
> execution, input/output validation, failure isolation, audit redaction, and P0
> evidence projection). It resolves nothing on its own.

## What this implements

A **very narrow** dev-only local plugin runtime that may invoke **reviewed,
side-effect-free fixture operations** — and only those:

- `hermes_cli/dev_web_fixture_plugins.py` — **seven** reviewed fixture operations
  bound through a frozen `FIXTURE_REGISTRY` / `FIXTURE_ALLOWLIST`:

  | plugin id | operation | description |
  |-----------|-----------|-------------|
  | `fixture.echo` | `echo_uppercase` | Echo the text field uppercased; redacts secret-shaped input. |
  | `fixture.inspect` | `summarize_keys` | Summarize mapping keys; never leaks values; redacts secret keys. |
  | `fixture.fault` | `deliberate_failure` | Always fails with a controlled, fake-secret-bearing exception. |
  | `fixture.transform` | `normalize_text` | Trim + collapse whitespace; redacts secret-shaped input. |
  | `fixture.validate` | `validate_required_keys` | Validate required keys; returns sorted missing; redacts secret keys. |
  | `fixture.math` | `count_items` | Count list items; never leaks values. |
  | `fixture.redact` | `redact_payload` | Redact fake secrets and forbidden paths from a payload. |

  Each `FixtureOperation` now carries frozen, all-`False` safety metadata
  (`side_effects` / `network` / `secrets` / `filesystem` / `production` /
  `route_change`), an `allowed_capabilities` tuple, and input/output policies.
  The runtime re-validates that metadata at bind time (`validate_fixture_metadata`)
  and rejects an operation whose metadata is missing or unsafe.

- `hermes_cli/dev_web_plugin_runtime.py` — `PluginRuntimeRequest`,
  `PluginRuntimeResult`, `PluginRuntimePolicy`, descriptor-to-fixture binding
  (`resolve_runtime_binding`, now with metadata re-validation + capability
  compatibility), the single entry point `run_dev_plugin()`, an output
  validator (`_assert_fixture_output`), an authorization-summary audit block,
  and a **batch harness**: `PluginRuntimeBatchRequest`,
  `PluginRuntimeBatchResult`, and `run_dev_plugin_batch()`.

- `hermes_cli/dev_web_sandbox_scenarios.py` — a **third** fixed
  `RUNTIME_EXPANSION_PROOF_SCENARIOS` library (4 scenarios) for the four new
  fixture ids, driven through the existing descriptor-only proof runner. The
  frozen Phase 3H `FIXED_SCENARIOS` (22) and `RUNTIME_PROOF_SCENARIOS` (5) are
  unchanged.

- `hermes_cli/dev_web_sandbox_policy.py` — the descriptor execution-surface
  scanner is widened so a descriptor naming `file` / `path` / `remote` /
  `pluginDir` / `localDirectory` is denied descriptor-only read (these are
  load/path/remote surfaces a clean descriptor never names).

- `tests/test_dev_web_phase_3i_runtime_mvp_expansion.py` — full coverage of the
  new operations, registry/allowlist immutability, descriptor binding for the
  new operations, batch execution (success / mixed / fail-fast / isolation /
  fail-closed), input/output validation, audit redaction, P0 evidence, and the
  source boundary.

The runtime reuses the Phase 3H guards / policy / audit / evidence logic
verbatim and layers two new capabilities on top: invoke a reviewed fixture by
allowlist binding, and run a batch of such bindings in isolation.

## Hard scope (what the runtime IS and IS NOT)

The runtime:

- loads reviewed fixture operations **only** from the hardcoded `FIXTURE_ALLOWLIST`;
- is invoked **only** through tests / internal function calls (`run_dev_plugin`
  / `run_dev_plugin_batch`);
- produces an **in-memory**, redacted `PluginRuntimeResult` /
  `PluginRuntimeBatchResult` and audit record;
- re-validates each bound fixture's safety metadata and rejects a request whose
  requested capabilities are incompatible with the bound fixture;
- enforces capability / filesystem / network / secrets / production / route /
  kill-switch guards, and a metadata authorization-smuggling denial;
- catches and redacts fixture failures and non-JSON-safe outputs (fail-closed);
- runs batch requests in isolation — one fixture failure or denial never poisons
  another request — with optional `fail_fast`.

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

## Runtime flags (frozen, all results — single and batch)

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

A successful fixture execution (single or batch) flips **none** of these. They
are enforced in `PluginRuntimeResult.__post_init__` and
`PluginRuntimeBatchResult.__post_init__` (an attempt to construct a result with
unfrozen flags raises).

## Input / output validation

- **Input**: each fixture bounds its input (`MAX_FIXTURE_INPUT_BYTES` repr size,
  `MAX_FIXTURE_NESTING_DEPTH`, `MAX_FIXTURE_LIST_ITEMS`) and its types. Oversized
  / too-deep / wrong-type / missing-required-field input raises a controlled
  `FixtureInputError` that the runtime records as `fixture_input_invalid`.
- **Output**: every fixture result is run through `_assert_fixture_output`
  (JSON-native mapping only — no callable / module / object) and then the shared
  redactor. A non-JSON-safe output raises `FixtureOutputError`, recorded as
  `fixture_output_unsafe`. Secret-shaped and forbidden-path values are redacted.

## Batch execution (`run_dev_plugin_batch`)

- Validates the batch id (a non-empty unsafe label fails the batch closed), the
  requests list (a sequence of `PluginRuntimeRequest`), the batch size
  (`MAX_BATCH_REQUESTS = 32`), and the batch metadata (an authorization-smuggling
  payload fails the batch closed).
- Runs each request through `run_dev_plugin` independently — isolation by
  construction (no shared mutable state).
- `fail_fast=True` stops after the first request that is not allowed (denied or
  failed); `fail_fast=False` runs every request.
- Result order is preserved; the aggregate audit carries a per-operation summary,
  a redacted P0 projection, a frozen authorization summary, and `persisted=false`.

## Authorization (unchanged, frozen NO-GO)

A successful fixture execution — single or batch — is **dev-only partial
evidence only**. It is:

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
(`metadata_authorization_smuggling_denied`), for single requests and at the batch
level. A forged `HumanApprovalRecord` remains invalid (the dev skeleton holds no
trust token).

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
/ batch / fixture paths return 404.

## P0 evidence classification

| Outcome | Classification | Resolved |
|---------|---------------|----------|
| Fixture executed successfully (single or batch) | `partial_evidence` | False |
| Guard denied the request | `guard_evidence` | False |
| Fixture failed (caught / redacted) | `failure_mode_evidence` | False |

All three are recorded as **partial** evidence. None advances a gate. The
24-gate registry's `resolved_count` remains 0 regardless of how many fixtures run,
how many batches pass, or how many proof scenarios pass.

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

These require explicit, separate human authorization that no code or metadata in
this MVP (or its expansion) can grant.
