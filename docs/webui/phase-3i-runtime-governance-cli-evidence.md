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

The CLI was then promoted from "basic usable" to a **complete developer CLI**:
stable JSON envelope, command aliases, `--pretty` output, subcommand help,
deterministic report snapshots, transcript-replay coverage, a redaction
regression corpus, invalid-input hardening, batch-consistency invariants, an
audit-completion surface, a no-side-effect invariant block on every envelope, a
subprocess smoke suite, a source-boundary scan, `dev_web_api` isolation, and
production-safety (no `~/.hermes` / production `state.db` access) checks.

| Item | Value |
|------|-------|
| Command group | `hermes dev-runtime` |
| Subcommands | `list`, `show`, `run`, `batch`, `audit`, `p0-report`, `help` |
| Aliases | `ls`→`list`, `inspect`→`show`, `exec`→`run`, `evidence`→`p0-report` |
| Output mode | compact JSON (default) / `--pretty` for `indent=2` |
| Descriptor reach | Frozen reviewed-fixture descriptors only |
| Envelope | `ok`, `command` (`dev-runtime.<canonical>`), `schemaVersion`, `authorization`, `sideEffects`, `result`/`error` |
| New HTTP route | **0** (route governance unchanged: `34/34/5/0/1/1`) |
| P0 resolved_count | **0** (unchanged) |
| Implementation Authorization | **NO-GO** (unchanged) |
| Phase 3I production authorization | **NOT AUTHORIZED** (unchanged) |

## Stable JSON envelope

Every command — success, failure, and help — prints the same envelope shape:

```json
{
  "ok": true,
  "command": "dev-runtime.<canonical-command>",
  "schemaVersion": "phase-3i-runtime-governance-v1",
  "authorization": {
    "implementationGate": "NO-GO",
    "phase3iProductionGate": "NOT_AUTHORIZED",
    "productionRuntimeGate": "NO-GO",
    "newRouteGate": "NO-GO",
    "productionRolloutGate": "NO-GO",
    "arbitraryPluginLoading": "NO-GO",
    "localPluginDirectoryLoading": "NO-GO",
    "remoteRegistry": "NO-GO",
    "marketplace": "NO-GO",
    "externalNetwork": "NO-GO",
    "newRoute": "NO-GO",
    "productionRollout": "NO-GO",
    "realApiKeyRead": false
  },
  "sideEffects": {
    "productionAccess": false,
    "externalNetwork": false,
    "realSecretRead": false,
    "routeChange": false,
    "runtimeStoreWrite": false,
    "auditStoreWrite": false,
    "arbitraryPluginLoad": false,
    "localPluginDirectoryRead": false,
    "remotePluginFetch": false,
    "marketplaceAccess": false,
    "inputFileRead": false,
    "outputFileWrite": false
  },
  "result": { "redacted": true, "persisted": false }
}
```

The `*Gate` / supply-chain verdict keys are chosen so the conservative redactor
cannot mask the NO-GO / not-authorized signal (a key whose name carries a secret
stem — e.g. `*Authorization` / `*ApiKey` — would have its value collapsed to
`[REDACTED]`, hiding the very signal the block exists to surface). The
real-API-key dimension is projected as `realApiKeyRead: false` (a bool) so it
stays visible. Invalid input / unknown commands return `ok: false` with a
redacted `error.code` and exit code `2`. Output is deterministic
(`sort_keys=True`), carries no timestamp / runId, and is therefore a stable
snapshot.

## CLI completion behavior

- **Command group:** `hermes dev-runtime` (and `python -m
  hermes_cli.dev_web_runtime_governance_cli ...` directly).
- **Subcommands:** `list`, `show`, `run`, `batch`, `audit`, `p0-report`, `help`.
- **Aliases:** `ls`, `inspect`, `exec`, `evidence` — each resolves to its
  canonical command before dispatch; the envelope `command` always carries the
  canonical token and the alias changes no behavior.
- **`--pretty`:** accepted anywhere on the command line; renders the identical
  data `indent=2`. Default output is compact single-line JSON.
- **Help:** `hermes dev-runtime help`, `hermes dev-runtime` (no args),
  `hermes dev-runtime --help` / `-h` (root), and
  `hermes dev-runtime <command> --help` (per-subcommand) all print a JSON-safe
  help envelope stating the dev-only / production-forbidden boundary.
- **Examples:** the help envelope carries concrete, copy-pasteable examples
  (no example reads or writes a file).
- **Exit codes:** `0` = parsed and ran (`ok` true; a denied / failed descriptor
  is still `ok` true — the CLI reported the outcome correctly); `2` = invalid
  input / usage error / unknown command (`ok` false; redacted error).

## Test coverage (completion suite)

`tests/test_dev_web_phase_3i_runtime_governance_cli.py` (governance projections,
CLI list/show/run/batch/audit/p0-report, invalid-input, redaction, source
boundary, `dev_web_api` isolation, route governance, production safety,
subprocess wiring) plus
`tests/test_dev_web_phase_3i_runtime_governance_cli_completion.py`:

- **UX / help / aliases / pretty** — root + subcommand help, every alias,
  `--pretty` indent + position-independence + data-identical, JSON parseability.
- **Envelope schema** — every success / failure / help / unknown envelope carries
  `schemaVersion`, the full `authorization` block, and the all-False
  `sideEffects` block.
- **Snapshots** — `list` (count 6, sorted ids), `show` (allowed binding),
  `run` (`HELLO`, resolved 0), denied run, `batch` (counts + order), `p0-report`
  (24 / 0) — inline expected dicts, no snapshot files.
- **Transcript replay** — happy, denied, and adversarial multi-step sequences;
  authorization invariant across the transcript; no secret / production leak.
- **Redaction corpus** — fake `sk-` / `ghp_` / `xoxb-` / `Bearer` / PEM /
  env-assignment secrets and fake `/Users/.../.hermes` / `state.db` paths are
  masked across `run` / `batch` / `audit` / error envelopes / `--pretty`.
- **Invalid-input hardening** — missing args, invalid JSON, wrong shapes,
  oversized input / batch, unsafe / too-long / secret-shaped descriptor ids,
  unsupported commands, no traceback on stdout.
- **Batch consistency** — `total == succeeded + failed + denied`, order
  preserved, fail-fast, isolation (a fault does not poison siblings), per-result
  + batch side-effects all False, resolved 0, not persisted.
- **Audit completion** — happy / fault / denied audit surface the full report
  (descriptorId, pluginId, operation, verdict, denialReasons, triggeredGuards,
  redactedAudit, p0Evidence, sideEffects, authorization, persisted false).
- **No-side-effect invariants** — metadata bypass keys, batch-item metadata, and
  fake-descriptor metadata cannot flip a side effect or authorize.
- **Smoke suite** — real subprocess invocations of
  `python -m hermes_cli.dev_web_runtime_governance_cli ...` and
  `python -m hermes_cli.main dev-runtime ...`.
- **Source boundary** — no dynamic-load / network / subprocess / file-I/O /
  path-resolution primitives in any governance-family module (precise usage
  patterns; the two modified modules held to a strict substring standard).
- **`dev_web_api` isolation** — the API does not import the governance surface;
  governance route probes return 404; OpenAPI paths remain 34; baseline
  `34/34/5/0/1/1` unchanged.
- **Production safety** — a recording stat/resolve/expanduser spy proves no
  command touches the production home or a production database; no runtime-store
  artifacts are created; every report is `persisted: false`.

## Redaction guarantees

The CLI runs every envelope through the frozen redactor
(`dev_web_sandbox_guards.redact_sandbox_payload`), which masks fake secret shapes
(`sk-` / `ghp_` / `xox[baprs]-` / `Bearer …` / `Authorization: …` / PEM blocks /
`.env`-style secret assignments) and fake production-path values
(`/Users/<user>/.hermes`, `state.db`) to `[REDACTED]`. The redaction regression
corpus pins these guarantees across `run` / `batch` / `audit`, error envelopes,
and `--pretty` output. The frozen redactor itself is **not** modified by this
task (it lives in `dev_web_sandbox_guards.py`); the corpus uses
redactor-matching forms.



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

The seven subcommands (`list`, `show`, `run`, `batch`, `audit`, `p0-report`,
`help`) plus their aliases, output mode, help routing, and exit-code behavior
are described above under **CLI completion behavior**. Each prints the stable
envelope described under **Stable JSON envelope**.

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
