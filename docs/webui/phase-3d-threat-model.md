# Phase 3D — Plugin Runtime Threat Model

| Field | Value |
|-------|-------|
| Phase | 3D (Planning) |
| Title | Plugin Runtime — Threat Model (Frozen) |
| Status | Frozen (docs-only planning; Plugin Runtime **not started**) |
| Date | 2026-06-18 |
| Planning ID | `PHASE-3D-PLANNING-001` |
| Threat-Model ID | `PHASE-3D-THREAT-MODEL-001` |

> This document freezes the threat model for a future Phase 3D Plugin Runtime. It
> lists the threat categories a plugin / dynamic-loading / remote-registry /
> marketplace surface would introduce, and the planning-time mitigation + future
> implementation gate for each. No code is written here.

Each threat follows: ID · Description · Attack path · Impact · Phase 3D planning
mitigation · Future implementation gate · GO / NO-GO implication.

---

## PLUG-THREAT-01 — Dynamic import arbitrary code execution

- **Description:** A plugin path uses `importlib` / `__import__` /
  `spec_from_file_location` to load code from a descriptor, turning the registry
  into an arbitrary-code-execution surface.
- **Attack path:** descriptor with a hidden `pythonImportPath` → import at load →
  module-level side effects (file / network / subprocess).
- **Impact:** arbitrary code execution inside the dev process; escape from every
  gate.
- **Phase 3D planning mitigation:** freeze **no dynamic loading**; forbid
  `pythonImportPath` / `dynamicModule` / `callable` in the manifest contract; the
  future runtime is descriptor-only.
- **Future implementation gate:** AST / call-graph scan asserting no `importlib` /
  `__import__` / path-load path; audit `plugin_no_dynamic_loading_checked`.
- **GO / NO-GO:** dynamic import is **NO-GO**.

## PLUG-THREAT-02 — Local plugin directory traversal

- **Description:** The runtime walks a user's local plugin directory to discover
  plugins (`os.walk` / `pkgutil` / glob).
- **Attack path:** a dropped file in a scanned directory is picked up and
  described / promoted.
- **Impact:** untrusted file influences the descriptor set; path traversal.
- **Phase 3D planning mitigation:** forbid scanning any local plugin directory;
  descriptors are tracked source only.
- **Future implementation gate:** test asserting no directory walk / glob of any
  plugin folder; `localPath` forbidden in the manifest.
- **GO / NO-GO:** local plugin directory loading is **NO-GO**.

## PLUG-THREAT-03 — Remote registry supply-chain attack

- **Description:** A remote plugin registry is fetched to discover / update
  plugins.
- **Attack path:** compromised or malicious registry serves a descriptor/code pair
  that is installed and run.
- **Impact:** supply-chain compromise of the dev instance.
- **Phase 3D planning mitigation:** forbid any remote registry; no remote manifest
  fetch; no arbitrary-URL fetch for discovery.
- **Future implementation gate:** test asserting no `externalUrl` / `downloadUrl` /
  `remoteUrl` is honored; no `requests` / `httpx` / `urllib` / `aiohttp` discovery.
- **GO / NO-GO:** remote registry is **NO-GO**.

## PLUG-THREAT-04 — Marketplace malicious plugin

- **Description:** A marketplace lets operators browse / install plugins.
- **Attack path:** a malicious listing is installed and executed.
- **Impact:** untrusted-code execution; reputational / data risk.
- **Phase 3D planning mitigation:** forbid a marketplace entirely.
- **Future implementation gate:** test asserting no marketplace path exists.
- **GO / NO-GO:** marketplace is **NO-GO**.

## PLUG-THREAT-05 — Provider-generated plugin injection

- **Description:** A provider response carries a plugin / tool definition that the
  system installs as a plugin.
- **Attack path:** prompt-injected provider output becomes an installed,
  executable plugin.
- **Impact:** untrusted LLM output gains an execution path.
- **Phase 3D planning mitigation:** freeze that provider responses cannot create,
  install, enable, or execute a plugin; provider tool_calls stay classified only.
- **Future implementation gate:** test asserting no provider response can mutate
  the descriptor set.
- **GO / NO-GO:** provider-generated plugin is **NO-GO**.

## PLUG-THREAT-06 — LLM-generated tool auto-install

- **Description:** An LLM-generated tool is auto-installed as a plugin.
- **Attack path:** agent emits a tool definition that is auto-registered and run.
- **Impact:** untrusted model output executes.
- **Phase 3D planning mitigation:** forbid auto-install of LLM-generated tools.
- **Future implementation gate:** test asserting no auto-registration path.
- **GO / NO-GO:** LLM-generated plugin install is **NO-GO**.

## PLUG-THREAT-07 — Shell command execution

- **Description:** A plugin carries or invokes a shell command.
- **Attack path:** `shellCommand` field or `subprocess` / `os.system` /
  `shell=True` invocation.
- **Impact:** arbitrary command execution; sandbox escape.
- **Phase 3D planning mitigation:** forbid `shellCommand`; forbid subprocess /
  shell paths.
- **Future implementation gate:** boundary scan rejects `subprocess` / `os.system`
  / `shell=True`; `shellCommand` forbidden in manifest.
- **GO / NO-GO:** shell execution is **NO-GO**.

## PLUG-THREAT-08 — Database mutation

- **Description:** A plugin writes to a database or production `state.db`.
- **Attack path:** `sqlStatement` field or direct DB mutation.
- **Impact:** persisted state corruption; production touched.
- **Phase 3D planning mitigation:** forbid `sqlStatement`; no DB mutation.
- **Future implementation gate:** boundary scan rejects `INSERT INTO` /
  `UPDATE … SET` / `DELETE FROM`; no production `state.db` access.
- **GO / NO-GO:** database mutation is **NO-GO**.

## PLUG-THREAT-09 — External HTTP exfiltration

- **Description:** A plugin performs outbound HTTP.
- **Attack path:** `requests` / `httpx` / `urllib` / `aiohttp` / `curl` call.
- **Impact:** data exfiltration; unauthorized side effects.
- **Phase 3D planning mitigation:** forbid external HTTP execution by a plugin.
- **Future implementation gate:** boundary scan rejects outbound network calls in
  plugin code paths.
- **GO / NO-GO:** external HTTP execution is **NO-GO**.

## PLUG-THREAT-10 — Production operation escalation

- **Description:** A plugin performs a production operation or reaches production
  paths.
- **Attack path:** `productionPath` field or runtime reaching `~/.hermes` /
  production `state.db`.
- **Impact:** production exposure.
- **Phase 3D planning mitigation:** forbid `productionPath`; `productionAllowed =
  false`.
- **Future implementation gate:** `enforce_dev_environment()` allowlist; no
  `~/.hermes` / production `state.db` access.
- **GO / NO-GO:** production operation is **NO-GO**.

## PLUG-THREAT-11 — Capability permission bypass

- **Description:** A descriptor grants itself a permission its bound capability
  does not have.
- **Attack path:** descriptor declares `permissionClass = WRITE_CONFIRM` while its
  bound capability is `READ_ONLY`, then the runtime trusts the descriptor.
- **Impact:** privilege escalation via descriptor self-classification.
- **Phase 3D planning mitigation:** a descriptor inherits the permission class of
  its bound capability; it cannot declare a higher class.
- **Future implementation gate:** test asserting descriptor permission class ≤
  bound-capability permission class.
- **GO / NO-GO:** permission bypass is **NO-GO**.

## PLUG-THREAT-12 — Tool policy bypass

- **Description:** A plugin route/execution path skips the dry-run / confirmation
  / audit chain.
- **Attack path:** a plugin execution endpoint bypasses the Phase 2 controlled
  execution chain.
- **Impact:** unauthorized execution.
- **Phase 3D planning mitigation:** plugins inherit the existing Tool policy; no
  new execution path is introduced.
- **Future implementation gate:** test asserting no plugin can execute outside the
  existing chain.
- **GO / NO-GO:** Tool policy bypass is **NO-GO**.

## PLUG-THREAT-13 — Provider live gate bypass

- **Description:** A plugin triggers a live provider request without the Phase
  3B-Live-Enablement gate.
- **Attack path:** plugin path calls a provider directly, skipping approval /
  budget / kill switch.
- **Impact:** unauthorized live cost / network call / secret use.
- **Phase 3D planning mitigation:** plugins cannot trigger live provider
  execution; the live gate stays separate.
- **Future implementation gate:** test asserting no plugin reaches the provider
  live path.
- **GO / NO-GO:** Provider live gate bypass is **NO-GO**.

## PLUG-THREAT-14 — Workflow approval bypass

- **Description:** A plugin auto-advances a workflow or executes a write without
  the workflow approval gate.
- **Attack path:** plugin path writes / advances steps without confirmation.
- **Impact:** unauthorized step execution / write.
- **Phase 3D planning mitigation:** plugins cannot create / advance / write inside
  a workflow.
- **Future implementation gate:** test asserting no plugin mutates workflow state.
- **GO / NO-GO:** Workflow approval bypass is **NO-GO**.

## PLUG-THREAT-15 — Audit bypass

- **Description:** A plugin action is not audited, or audit fails open.
- **Attack path:** plugin path that skips audit, or an audit write failure that
  allows the action to proceed.
- **Impact:** loss of traceability.
- **Phase 3D planning mitigation:** audit is mandatory and fail-closed for every
  descriptor lifecycle event.
- **Future implementation gate:** test asserting every lifecycle event is audited
  and audit failure blocks the action.
- **GO / NO-GO:** audit bypass is **NO-GO**.

## PLUG-THREAT-16 — Secret leak

- **Description:** A descriptor / read model / audit / UI surfaces an API key,
  Authorization header, bearer token, or raw secret.
- **Attack path:** secret-bearing field passes through to a read surface.
- **Impact:** secret exposure.
- **Phase 3D planning mitigation:** forbidden-fields list + recursive scan + safe
  read-model allowlist + defensive re-redaction.
- **Future implementation gate:** no-leak tests across descriptor / read model /
  audit / UI; `redactionApplied = true`.
- **GO / NO-GO:** secret leak is **NO-GO**.

## PLUG-THREAT-17 — Callable repr leak

- **Description:** A callable / function repr or import path is surfaced.
- **Attack path:** `callable` / `pythonImportPath` leaks into a read surface.
- **Impact:** internal exposure / reverse-engineering of entry points.
- **Phase 3D planning mitigation:** forbid `callable` / `pythonImportPath`;
  sanitizer collapses non-JSON values.
- **Future implementation gate:** no-leak test asserting no callable repr / import
  path is surfaced.
- **GO / NO-GO:** callable repr leak is **NO-GO**.

## PLUG-THREAT-18 — Production path leak

- **Description:** A production path (`~/.hermes` / production `state.db`) is
  surfaced in a read model / audit / UI.
- **Attack path:** `productionPath` field or a resolved production path rendered.
- **Impact:** production structure disclosure.
- **Phase 3D planning mitigation:** forbid `productionPath`; dev paths only.
- **Future implementation gate:** no-leak test asserting no production path.
- **GO / NO-GO:** production path leak is **NO-GO**.

## PLUG-THREAT-19 — Route governance drift

- **Description:** A plugin implementation adds an HTTP / Tool write / Provider
  route.
- **Attack path:** new endpoint introduced for plugin status / execution.
- **Impact:** surface / boundary drift.
- **Phase 3D planning mitigation:** no new route by default; status rides the
  existing `/status` block.
- **Future implementation gate:** `test_dev_check_webui.py` +
  `test_dev_web_0c06_closure.py` (34 / 34 / 5 / 0 / 1 / 1).
- **GO / NO-GO:** route drift is **NO-GO**.

## PLUG-THREAT-20 — Runtime artifact commit

- **Description:** A plugin implementation commits a runtime artifact (store /
  JSONL / token / manifest runtime file).
- **Attack path:** staging a generated runtime file.
- **Impact:** secret / state leak into the repo.
- **Phase 3D planning mitigation:** descriptors are tracked source; runtime data
  is gitignored.
- **Future implementation gate:** boundary search rejects runtime artifacts; no
  plugin runtime store is committed.
- **GO / NO-GO:** runtime artifact commit is **NO-GO**.

## PLUG-THREAT-21 — `.claude/` commit

- **Description:** `.claude/` is staged / committed.
- **Attack path:** accidental `git add .`.
- **Impact:** session / state leak.
- **Phase 3D planning mitigation:** verify `.gitignore`; never stage `.claude/`.
- **Future implementation gate:** `git diff --cached --name-only` rejects `.claude/`.
- **GO / NO-GO:** `.claude/` commit is **NO-GO**.

## PLUG-THREAT-22 — `~/.hermes` access

- **Description:** A plugin path reads from / writes to `~/.hermes`.
- **Attack path:** path resolution reaching the production home.
- **Impact:** production instance touched.
- **Phase 3D planning mitigation:** `enforce_dev_environment()` allowlist; dev
  `HERMES_HOME` only.
- **Future implementation gate:** boundary search rejects `~/.hermes` as a live
  target.
- **GO / NO-GO:** `~/.hermes` access is **NO-GO**.

## PLUG-THREAT-23 — Production `state.db` access

- **Description:** A plugin path accesses the production `state.db`.
- **Attack path:** DB connection / file read reaching production state.
- **Impact:** production state touched.
- **Phase 3D planning mitigation:** dev `HERMES_HOME` isolation enforced.
- **Future implementation gate:** boundary search rejects production `state.db`.
- **GO / NO-GO:** production `state.db` access is **NO-GO**.

---

## Summary

| Category | Threats | All NO-GO? |
|----------|---------|------------|
| Dynamic / external code | 01–06, 09 | yes |
| Shell / DB / production | 07, 08, 10 | yes |
| Permission / gate bypass | 11–14 | yes |
| Audit / leak | 15–18 | yes |
| Governance / artifact / prod access | 19–23 | yes |

Every threat resolves to **NO-GO** in this planning phase: the future runtime is
descriptor-only, dev-only, disabled-by-default, capability-bound, and
audit-only-dry-run.

## Cross-references

- [Phase 3D planning](phase-3d-planning.md)
- [Phase 3D scope freeze](phase-3d-plugin-runtime-scope-freeze.md)
- [Phase 3D trust boundary](phase-3d-trust-boundary.md)
- [Phase 3D risk register](phase-3d-risk-register.md)
- [Phase 3C no dynamic loading policy](phase-3c-no-dynamic-loading-policy.md)
- [Phase 3C readonly provider threat model](phase-3b-readonly-provider-threat-model.md)
