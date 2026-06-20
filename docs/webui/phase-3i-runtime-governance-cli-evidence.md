# Phase 3I — Runtime Governance CLI Evidence

> **Phase 3I — Runtime Governance CLI (code allowed, production forbidden).**
> This is **dev-only partial evidence**, not a closeout, not a signoff, not an
> archive, not an authorization review, not a production runtime, and not a
> WebUI route integration. It records the addition of a developer-facing CLI
> command group that exposes the *already-implemented* descriptor-backed fixture
> runtime. It authorizes **nothing** for production.

## Summary

This change adds a **dev-only runtime governance CLI** (`hermes dev-runtime`)
that promotes the Phase 3I dev-only descriptor-backed fixture runtime from
"callable inside tests" to "operable by a developer through a CLI / internal
command". The CLI is a thin, fail-closed wrapper over the pure report
projections in `hermes_cli/dev_web_runtime_governance.py`; it adds **no**
capability — it only projects the existing reviewed-fixture runtime as
JSON-safe, redacted reports.

| Item | Value |
|------|-------|
| Command group | `hermes dev-runtime` |
| Subcommands | `list`, `show`, `run`, `batch`, `audit`, `p0-report`, `help` |
| Descriptor reach | Frozen reviewed-fixture descriptors only |
| Output | JSON-safe, redacted, `persisted: False`, stdout only |
| New HTTP route | **0** (route governance unchanged: `34/34/5/0/1/1`) |
| P0 resolved_count | **0** (unchanged) |
| Implementation Authorization | **NO-GO** (unchanged) |
| Phase 3I production authorization | **NOT AUTHORIZED** (unchanged) |

## Files added / changed

**Code (dev-only, read-only projections):**
- `hermes_cli/dev_web_runtime_governance.py` — pure report projection module
  (`list_runtime_descriptors`, `show_runtime_descriptor_binding`,
  `run_runtime_descriptor`, `run_runtime_descriptor_batch`,
  `build_runtime_audit_report`, `build_runtime_p0_report`,
  `authorization_projection`, `assert_no_side_effect_surface`).
- `hermes_cli/dev_web_runtime_governance_cli.py` — argparse CLI entry
  (`main`, input parsing, JSON envelope, `__main__` for
  `python -m hermes_cli.dev_web_runtime_governance_cli`).
- `hermes_cli/main.py` — minimal wiring: one `dev-runtime` subparser + a
  `cmd_dev_runtime` delegator that forwards remaining args to the governance CLI.

**Tests:**
- `tests/test_dev_web_phase_3i_runtime_governance_cli.py` — governance module
  projections, CLI list/show/run/batch/audit/p0-report, invalid-input /
  failure paths, redaction, source boundary, `dev_web_api` isolation, route
  governance, production safety, regression preservation, and end-to-end
  subprocess wiring (96 default tests + 2 integration tests).

**Docs:**
- `docs/webui/phase-3i-runtime-governance-cli-evidence.md` — this file.

## What the CLI can do

- `list` — list the frozen reviewed-fixture descriptors (no execution).
- `show <descriptor-id>` — inspect the registry→runtime binding (no execution).
- `run <descriptor-id> --input JSON` — run one descriptor-backed fixture
  operation.
- `batch --items JSON [--fail-fast]` — run a multi-descriptor batch (isolated,
  fail-closed, order-preserving).
- `audit <descriptor-id> --input JSON` — run one descriptor and print its
  redacted audit.
- `p0-report` — print the conservative P0 evidence projection summary.
- `help` — print the command help (states the dev-only / production-forbidden
  boundary).

Every command prints a JSON-safe envelope:

```json
{
  "ok": true,
  "command": "<subcommand>",
  "result": { "...": "redacted, persisted: false" },
  "authorization": {
    "implementationGate": "NO-GO",
    "phase3iProductionGate": "NOT_AUTHORIZED",
    "productionRuntimeGate": "NO-GO",
    "newRouteGate": "NO-GO",
    "productionRolloutGate": "NO-GO"
  }
}
```

The `*Gate` key names mirror the value-preserving P0 projection vocabulary so
the redactor (which masks values under secret-bearing keys such as
`*Authorization`) cannot hide the very NO-GO / not-authorized signal this block
exists to surface. Invalid input / unknown commands return `ok: false` with a
redacted `error.code` and exit code `2`.

## What the CLI does NOT do (frozen boundary)

This CLI:

- operates **only** on reviewed fixture descriptors — it does **not** load
  arbitrary plugins;
- does **not** support local plugin directory loading (outside the fixture
  allowlist);
- does **not** support a remote registry;
- does **not** support a marketplace;
- does **not** support external plugin fetch;
- does **not** support provider-generated or LLM-generated plugin install;
- does **not** read real API keys;
- does **not** access external network;
- does **not** write a runtime store;
- does **not** add an HTTP route;
- does **not** modify `dev_web_api.py` route registration (it is **not**
  imported by the FastAPI app);
- does **not** access production;
- does **not** access `~/.hermes` — not even metadata-only `stat` / `ls` /
  `resolve`;
- does **not** access a production `state.db`;
- does **not** read `--input-file` or write `--output-file` (no file I/O);
- does **not** persist an audit store (every report is `persisted: False`).

The frozen boundary constants live in
`hermes_cli/dev_web_runtime_governance.py` (`NO_*` flags + `assert_no_side_effect_surface`)
and are asserted on every CLI invocation.

## P0 evidence status (unchanged / conservative)

A descriptor-backed fixture execution (single or batch) is **dev-only partial
evidence**. It is **never** a P0 resolution.

- **Total P0 gates:** 24
- **Resolved / approved:** 0
- **Partial evidence:** about 19
- **Pending human review:** about 5
- **Implementation Authorization:** **NO-GO** — a reviewed-fixture pass is not
  authorization for a production / real external runtime.
- **Phase 3I production authorization:** **NOT AUTHORIZED.**
- **Production runtime authorization:** **NO-GO.**
- **New route:** **NO-GO.**
- **Production rollout:** **NO-GO.**

`resolved_count` stays 0 and every authorization flag stays NO-GO /
not-authorized no matter what runs or what untrusted input is supplied.

## Route governance (unchanged)

```
OpenAPI paths        = 34
Runtime routes       = 34
Tool GET             = 5
Tool write HTTP route= 0
Tool dry-run route   = 1
Tool execution route = 1
New HTTP route       = 0
New Tool write route = 0
New Provider route   = 0
New plugin route     = 0
New runtime route    = 0
```

The CLI adds no HTTP route. `tests/test_dev_web_phase_3i_runtime_governance_cli.py::TestDevWebApiIsolation`
probes governance route paths (404) and asserts the OpenAPI path count and the
`34/34/5/0/1/1` baseline are unchanged.

## Why Implementation Authorization remains NO-GO

The governance CLI reuses the existing dev-only descriptor-backed fixture
runtime verbatim. That runtime executes only reviewed fixture functions over the
frozen allowlist, against in-memory descriptors, with no real plugin runtime, no
external network, no real API key, and no production access. A CLI surface over
that runtime changes none of those facts: it is still dev-only fixture
execution, not a production plugin runtime, not real-runtime authorization, and
not a substitute for human review of the production rollout gates. The CLI is
explicitly forbidden from production rollout, new routes, provider writes,
autonomous writes, and live provider execution.

## Deferred / still not authorized

Production plugin runtime; arbitrary plugin loading; user-uploaded plugins;
local plugin directory loading outside the fixture allowlist; remote registry;
marketplace; external plugin fetch; provider-generated / LLM-generated plugin
install; real API key reading; external network; new route; production rollout;
provider write; autonomous write; live provider execution; shell execution;
database mutation outside approved tests; production operation; CLI input-file
reading; CLI output-file writing; persistent runtime audit store.
