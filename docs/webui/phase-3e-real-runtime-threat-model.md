# Phase 3E — Real Plugin Runtime Threat Model

| Field | Value |
|-------|-------|
| Phase | 3E (Planning) |
| Title | Real Plugin Runtime — Threat Model (Frozen) |
| Status | Frozen (docs-only planning; Real Plugin Runtime **not started**) |
| Date | 2026-06-19 |
| Planning ID | `PHASE-3E-PLANNING-001` |
| Threat-Model ID | `PHASE-3E-THREAT-MODEL-001` |

> This document freezes the threat model for a future, separately-authorized real
> Plugin Runtime. It lists the runtime-specific threat categories an executable
> plugin / dynamic-loading / out-of-process / containerized / remote-registry /
> marketplace / supply-chain surface would introduce, and the current planning
> mitigation + future required mitigation + implementation stop condition for
> each. No code is written here. Every high-severity item resolves to NO-GO until
> the sandbox / process / filesystem / network / supply-chain / audit / kill-switch
> models are approved.

Each threat follows: ID · Title · Description · Attack path · Impact · Likelihood
· Severity · Current mitigation · Future required mitigation · Implementation
stop condition · GO / NO-GO implication.

---

## RUNTIME-THREAT-01 — Arbitrary code execution

- **Description:** A real runtime gives plugins a code-execution entry point
  (interpreted plugin body, Wasm, or callable dispatch) inside the dev process
  or a worker.
- **Attack path:** a plugin (built-in, remote, provider-generated, or
  LLM-generated) carries code that runs at load or invocation; module-level or
  top-of-function side effects fire.
- **Impact:** full arbitrary code execution; escape of every gate.
- **Likelihood:** High (execution is the runtime's purpose).
- **Severity:** Critical.
- **Current mitigation:** no runtime exists; descriptor-only registry executes
  nothing.
- **Future required mitigation:** out-of-process / containerized sandbox with no
  in-process code execution; explicit allowlist of runtime capabilities; AST /
  call-graph + capability-policy check before any dispatch.
- **Implementation stop condition:** no approved sandbox model ⇒ stop.
- **GO / NO-GO:** arbitrary code execution is **NO-GO** until the sandbox model
  is approved.

## RUNTIME-THREAT-02 — Sandbox escape

- **Description:** A plugin breaks out of its sandbox through a misconfigured
  boundary, a shared interpreter, a namespace collision, or a sandbox primitive
  bug.
- **Attack path:** sandbox primitive bypass; shared mutable state; reflection;
  environment / capability leakage into the sandbox.
- **Impact:** escape into the dev process; reach of every secret and path.
- **Likelihood:** Medium.
- **Severity:** Critical.
- **Current mitigation:** no sandbox exists (no runtime).
- **Future required mitigation:** independently reviewed sandbox with escape
  tests; least-privilege capability surface; no shared interpreter with the host.
- **Implementation stop condition:** no approved sandbox + no escape test suite
  ⇒ stop.
- **GO / NO-GO:** sandbox escape is **NO-GO** until the sandbox model is
  approved.

## RUNTIME-THREAT-03 — Process breakout

- **Description:** An out-of-process or containerized worker breaks out of its
  process / container boundary into the host.
- **Attack path:** kernel / container-runtime bug; excessive capabilities; shared
  mount; PID-namespace escape; setuid abuse.
- **Impact:** host compromise; reach of production paths and secrets.
- **Likelihood:** Low–Medium.
- **Severity:** Critical.
- **Current mitigation:** no worker exists.
- **Future required mitigation:** hardened container image; dropped capabilities;
  read-only rootfs; seccomp / AppArmor profile; non-root; no new privileges.
- **Implementation stop condition:** no approved process-isolation model ⇒ stop.
- **GO / NO-GO:** process breakout is **NO-GO** until the process-isolation
  model is approved.

## RUNTIME-THREAT-04 — Filesystem exfiltration

- **Description:** A plugin reads files outside its dev sandbox (source repo,
  dotfiles, SSH keys, other projects).
- **Attack path:** relative / absolute path traversal; symlink traversal; path
  normalization bug; `..` smuggling; `/proc` / `/etc` probing.
- **Impact:** source / secret / key exfiltration.
- **Likelihood:** High.
- **Severity:** Critical.
- **Current mitigation:** no runtime filesystem access exists.
- **Future required mitigation:** explicit read / write allowlists; symlink
  resolution rejection; path normalization; deny-by-default; allowlist root
  validation.
- **Implementation stop condition:** no approved filesystem-boundary model ⇒
  stop.
- **GO / NO-GO:** filesystem exfiltration is **NO-GO** until the
  filesystem-boundary model is approved.

## RUNTIME-THREAT-05 — Network exfiltration

- **Description:** A plugin performs outbound network calls to exfiltrate data or
  phone home.
- **Attack path:** `requests` / `httpx` / `urllib` / `aiohttp` / raw socket /
  DNS tunneling.
- **Impact:** data exfiltration; C2; unauthorized side effects.
- **Likelihood:** High.
- **Severity:** Critical.
- **Current mitigation:** no runtime network path exists.
- **Future required mitigation:** network disabled by default; explicit egress
  allowlist; DNS policy; no secret headers; per-plugin budget + timeout; egress
  audit.
- **Implementation stop condition:** no approved network-boundary model ⇒ stop.
- **GO / NO-GO:** network exfiltration is **NO-GO** until the network-boundary
  model is approved.

## RUNTIME-THREAT-06 — Secret exfiltration

- **Description:** A plugin reaches environment variables, the dev `HERMES_HOME`,
  or process memory to read an API key / token / Authorization header.
- **Attack path:** `os.environ` read; inherited environment; secret file read;
  memory inspection; log scraping.
- **Impact:** secret disclosure; lateral provider access.
- **Likelihood:** High.
- **Severity:** Critical.
- **Current mitigation:** no runtime exists; secrets never reach descriptors.
- **Future required mitigation:** no inherited environment / secrets / filesystem
  into the sandbox; env scrubbing; secret-redaction in audit / logs / results.
- **Implementation stop condition:** no secret-isolation guarantee ⇒ stop.
- **GO / NO-GO:** secret exfiltration is **NO-GO** until secret isolation is
  approved.

## RUNTIME-THREAT-07 — Production path access

- **Description:** A runtime path reaches `~/.hermes` or production `state.db`.
- **Attack path:** path resolution beyond the dev sandbox; misconfigured
  `HERMES_HOME`; production path in a read surface.
- **Impact:** production instance touched.
- **Likelihood:** Medium.
- **Severity:** Critical.
- **Current mitigation:** `enforce_dev_environment()` allowlist; dev
  `HERMES_HOME` only; no runtime.
- **Future required mitigation:** runtime constrained to dev `HERMES_HOME`
  sandbox; production path forbidden in manifests, audit, UI; fail-closed on
  drift.
- **Implementation stop condition:** any production-path reachability ⇒ stop.
- **GO / NO-GO:** production path access is **NO-GO**.

## RUNTIME-THREAT-08 — Database mutation

- **Description:** A plugin writes to a database or the dev / production
  `state.db`.
- **Attack path:** `sqlite3` open + `INSERT` / `UPDATE` / `DELETE`; ORM path.
- **Impact:** persisted state corruption; production touched.
- **Likelihood:** Medium.
- **Severity:** High.
- **Current mitigation:** no runtime DB path exists.
- **Future required mitigation:** no DB driver in the sandbox; SQL statements
  forbidden in manifests; boundary scan rejects DML.
- **Implementation stop condition:** DB mutation reachable ⇒ stop.
- **GO / NO-GO:** database mutation is **NO-GO**.

## RUNTIME-THREAT-09 — Shell command execution

- **Description:** A plugin invokes a shell.
- **Attack path:** `subprocess` / `os.system` / `shell=True` / `popen`; a
  `shellCommand` manifest field.
- **Impact:** arbitrary command execution; sandbox escape.
- **Likelihood:** High.
- **Severity:** Critical.
- **Current mitigation:** `shellCommand` forbidden in descriptors; no runtime.
- **Future required mitigation:** no shell in the sandbox capability surface;
  `shellCommand` forbidden; AST / call-graph scan rejects shell primitives.
- **Implementation stop condition:** shell reachable ⇒ stop.
- **GO / NO-GO:** shell execution is **NO-GO**.

## RUNTIME-THREAT-10 — External package supply-chain compromise

- **Description:** A plugin (or its build) installs an external package whose
  dependency tree is compromised (typosquat, malicious maintainer, dep confusion).
- **Attack path:** `pip` / `npm` / `cargo` install inside the runtime; a poisoned
  transitive dependency executes at install or import.
- **Impact:** supply-chain compromise of the dev instance.
- **Likelihood:** Medium.
- **Severity:** Critical.
- **Current mitigation:** no package install exists; descriptors are tracked
  source.
- **Future required mitigation:** no package install by default; pinned versions
  + hash / digest verification; signed manifest (future); quarantine; no
  post-install / pre-execution hooks.
- **Implementation stop condition:** no approved supply-chain policy ⇒ stop.
- **GO / NO-GO:** external package install is **NO-GO** until the supply-chain
  policy is approved.

## RUNTIME-THREAT-11 — Remote registry poisoning

- **Description:** A remote plugin registry is fetched and serves a malicious
  descriptor / code pair.
- **Attack path:** compromised or malicious registry; MITM; CDN poisoning;
  stale-cache replay.
- **Impact:** supply-chain compromise; untrusted code execution.
- **Likelihood:** Medium.
- **Severity:** Critical.
- **Current mitigation:** no remote registry exists.
- **Future required mitigation:** no remote registry by default; if ever
  considered, signed manifests + pinning + allowlist + integrity check + separate
  review.
- **Implementation stop condition:** remote registry reachable ⇒ stop.
- **GO / NO-GO:** remote registry is **NO-GO**.

## RUNTIME-THREAT-12 — Marketplace malicious plugin

- **Description:** A marketplace lets operators browse / install plugins; a
  malicious listing is installed and executed.
- **Attack path:** search-ranking / impersonation / trojaned listing; one-click
  install → execute.
- **Impact:** untrusted-code execution; reputational / data risk.
- **Likelihood:** Medium.
- **Severity:** Critical.
- **Current mitigation:** no marketplace exists.
- **Future required mitigation:** no marketplace.
- **Implementation stop condition:** marketplace path exists ⇒ stop.
- **GO / NO-GO:** marketplace is **NO-GO**.

## RUNTIME-THREAT-13 — Provider-generated malicious plugin

- **Description:** A provider response carries a plugin / tool definition that
  the runtime installs and executes.
- **Attack path:** prompt-injected provider output becomes an installed,
  executable plugin.
- **Impact:** untrusted LLM output gains an execution path.
- **Likelihood:** Medium.
- **Severity:** Critical.
- **Current mitigation:** provider responses cannot create / install / enable /
  execute a plugin (Phase 3D boundary).
- **Future required mitigation:** runtime rejects any provider-sourced plugin;
  provider tool_calls stay classified only.
- **Implementation stop condition:** provider response can mutate the runtime ⇒
  stop.
- **GO / NO-GO:** provider-generated plugin is **NO-GO**.

## RUNTIME-THREAT-14 — LLM-generated tool injection

- **Description:** An LLM-generated tool is auto-registered as a plugin and run.
- **Attack path:** agent emits a tool definition that is auto-registered and
  invoked.
- **Impact:** untrusted model output executes.
- **Likelihood:** Medium.
- **Severity:** Critical.
- **Current mitigation:** LLM-generated plugin install is forbidden (Phase 3D).
- **Future required mitigation:** no auto-registration path; every runtime
  capability is reviewed static source.
- **Implementation stop condition:** auto-registration reachable ⇒ stop.
- **GO / NO-GO:** LLM-generated plugin install is **NO-GO**.

## RUNTIME-THREAT-15 — Permission escalation

- **Description:** A runtime path grants a plugin a permission higher than its
  bound capability, or self-classifies upward.
- **Attack path:** runtime trusts a descriptor-declared permission class; trust
  level auto-upgrades; capability binding is loosened.
- **Impact:** privilege escalation via self-classification.
- **Likelihood:** Medium.
- **Severity:** High.
- **Current mitigation:** descriptors inherit most-restrictive capability
  permission class; no runtime.
- **Future required mitigation:** runtime enforces permission class ≤
  most-restrictive bound capability; no self-grant; trust never auto-upgrades.
- **Implementation stop condition:** permission escalation path ⇒ stop.
- **GO / NO-GO:** permission escalation is **NO-GO**.

## RUNTIME-THREAT-16 — Tool policy bypass

- **Description:** A runtime execution path skips the dry-run / confirmation /
  audit chain.
- **Attack path:** a runtime endpoint invokes a capability directly, bypassing
  the Phase 2 controlled-execution chain.
- **Impact:** unauthorized execution.
- **Likelihood:** Medium.
- **Severity:** High.
- **Current mitigation:** no runtime execution path exists.
- **Future required mitigation:** runtime dispatch routes through the existing
  controlled-execution chain; no new execution path.
- **Implementation stop condition:** execution outside the chain ⇒ stop.
- **GO / NO-GO:** Tool policy bypass is **NO-GO**.

## RUNTIME-THREAT-17 — Provider live gate bypass

- **Description:** A runtime path triggers a live provider request without the
  Phase 3B-Live-Enablement gate.
- **Attack path:** runtime calls a provider directly, skipping approval / budget
  / kill switch / allowlist.
- **Impact:** unauthorized live cost / network call / secret use.
- **Likelihood:** Medium.
- **Severity:** High.
- **Current mitigation:** no runtime provider path exists.
- **Future required mitigation:** runtime cannot reach the provider live path;
  live gate stays separate and mandatory.
- **Implementation stop condition:** provider live path reachable ⇒ stop.
- **GO / NO-GO:** Provider live gate bypass is **NO-GO**.

## RUNTIME-THREAT-18 — Workflow approval bypass

- **Description:** A runtime path auto-advances a workflow or executes a write
  without the workflow approval gate.
- **Attack path:** runtime writes / advances steps without confirmation.
- **Impact:** unauthorized step execution / write.
- **Likelihood:** Medium.
- **Severity:** High.
- **Current mitigation:** no runtime workflow path exists.
- **Future required mitigation:** runtime cannot create / advance / write inside
  a workflow.
- **Implementation stop condition:** workflow mutation reachable ⇒ stop.
- **GO / NO-GO:** Workflow approval bypass is **NO-GO**.

## RUNTIME-THREAT-19 — Audit bypass

- **Description:** A runtime action is not audited, or audit fails open.
- **Attack path:** runtime path that skips audit, or an audit write failure that
  allows the action to proceed.
- **Impact:** loss of traceability.
- **Likelihood:** Medium.
- **Severity:** High.
- **Current mitigation:** no runtime actions exist.
- **Future required mitigation:** audit mandatory and fail-closed for every
  runtime lifecycle / dispatch / boundary event.
- **Implementation stop condition:** audit failure permits an action ⇒ stop.
- **GO / NO-GO:** audit bypass is **NO-GO**.

## RUNTIME-THREAT-20 — Route governance drift

- **Description:** A runtime implementation adds an HTTP / Tool write / Provider /
  plugin / runtime route.
- **Attack path:** a new endpoint introduced for runtime status / dispatch /
  install.
- **Impact:** surface / boundary drift.
- **Likelihood:** Medium.
- **Severity:** High.
- **Current mitigation:** no runtime route exists; status rides the existing
  `/status` block.
- **Future required mitigation:** no new route by default; any route requires a
  separate threat model + OpenAPI governance update + explicit approval.
- **Implementation stop condition:** route count drifts from 34 / 34 / 5 / 0 / 1
  / 1 without approval ⇒ stop.
- **GO / NO-GO:** route drift is **NO-GO**.

## RUNTIME-THREAT-21 — Runtime artifact leak

- **Description:** A runtime implementation commits a runtime artifact (store /
  JSONL / token / manifest runtime file) to the repo.
- **Attack path:** staging a generated runtime file.
- **Impact:** secret / state leak into the repo.
- **Likelihood:** Low.
- **Severity:** High.
- **Current mitigation:** descriptors are tracked source; runtime data is
  gitignored; no runtime artifacts exist.
- **Future required mitigation:** boundary search rejects runtime artifacts; no
  runtime store is committed.
- **Implementation stop condition:** a runtime artifact is staged ⇒ stop.
- **GO / NO-GO:** runtime artifact commit is **NO-GO**.

## RUNTIME-THREAT-22 — Prompt / response leak

- **Description:** A runtime plugin surface leaks raw prompts or raw provider
  responses into audit / logs / UI.
- **Attack path:** a plugin result / log line carries raw prompt / response text.
- **Impact:** disclosure of sensitive conversation content.
- **Likelihood:** Medium.
- **Severity:** High.
- **Current mitigation:** no runtime result surface exists.
- **Future required mitigation:** raw prompt / response forbidden in audit /
  logs / UI; redaction applied; safe fields only.
- **Implementation stop condition:** raw prompt / response reachable ⇒ stop.
- **GO / NO-GO:** prompt / response leak is **NO-GO**.

## RUNTIME-THREAT-23 — Token / authorization leak

- **Description:** A runtime surface leaks an API key, Authorization header,
  bearer token, or raw secret hash.
- **Attack path:** secret-bearing field passes through a runtime result / audit /
  log / UI.
- **Impact:** secret disclosure.
- **Likelihood:** Medium.
- **Severity:** Critical.
- **Current mitigation:** forbidden-fields list + recursive scan + safe
  allowlist; no runtime.
- **Future required mitigation:** forbidden-fields enforced at runtime result /
  audit / log / UI; defensive re-redaction.
- **Implementation stop condition:** any secret reachable ⇒ stop.
- **GO / NO-GO:** token / authorization leak is **NO-GO**.

## RUNTIME-THREAT-24 — Production rollout accident

- **Description:** A runtime path or feature flag is accidentally enabled in
  production.
- **Attack path:** default-on flag; misrouted config; prod `HERMES_HOME`
  picked up; operator copy-paste.
- **Impact:** production exposure to untrusted-code execution.
- **Likelihood:** Low.
- **Severity:** Critical.
- **Current mitigation:** `productionAllowed = false`; `devOnly = true`; dev
  `HERMES_HOME` only.
- **Future required mitigation:** runtime disabled by default; `devOnly` enforced;
  fail-closed in production `HERMES_HOME`; explicit kill switch.
- **Implementation stop condition:** runtime reachable from production
  `HERMES_HOME` ⇒ stop.
- **GO / NO-GO:** production rollout is **NO-GO**.

## RUNTIME-THREAT-25 — Denial of service

- **Description:** A plugin consumes unbounded CPU / memory / time / file handles
  and starves the dev process.
- **Attack path:** infinite loop; large allocation; fork bomb; unbounded
  recursion.
- **Impact:** dev instance hang / crash.
- **Likelihood:** Medium.
- **Severity:** Medium.
- **Current mitigation:** no runtime exists.
- **Future required mitigation:** per-plugin CPU / memory / time / fd limits;
  kill switch; quota enforcement.
- **Implementation stop condition:** no resource limits ⇒ stop.
- **GO / NO-GO:** unbounded resource use is **NO-GO**.

## RUNTIME-THREAT-26 — Persistence / backdoor plugin

- **Description:** A plugin installs a persistence mechanism (cron, launchd,
  startup hook, modified config) that survives restarts.
- **Attack path:** plugin writes a scheduled / startup entry; modifies global
  hermes config.
- **Impact:** persistent backdoor.
- **Likelihood:** Low–Medium.
- **Severity:** Critical.
- **Current mitigation:** no runtime exists; config mutation forbidden.
- **Future required mitigation:** no persistence surface; no cron / launchd /
  startup / config write capability; ephemeral sandbox only.
- **Implementation stop condition:** persistence surface reachable ⇒ stop.
- **GO / NO-GO:** persistence / backdoor is **NO-GO**.

## RUNTIME-THREAT-27 — Privilege confusion across dev / prod

- **Description:** A plugin authored for dev is run against the production
  `HERMES_HOME`, or a production capability is granted in dev and leaks upward.
- **Attack path:** dev / prod config confusion; shared plugin set across homes.
- **Impact:** dev plugin reaches production.
- **Likelihood:** Low.
- **Severity:** Critical.
- **Current mitigation:** dev-only enforcement; separate homes.
- **Future required mitigation:** runtime hard-bound to dev `HERMES_HOME`; no
  cross-home plugin set.
- **Implementation stop condition:** cross-home reachability ⇒ stop.
- **GO / NO-GO:** dev / prod privilege confusion is **NO-GO**.

## RUNTIME-THREAT-28 — Multi-user plugin ownership confusion

- **Description:** In a future multi-user setting, plugin ownership / visibility
  is ambiguous, letting one user's plugin affect another.
- **Attack path:** shared namespace; missing ownership check.
- **Impact:** cross-tenant effect.
- **Likelihood:** Low (single-user today).
- **Severity:** Medium.
- **Current mitigation:** single-user dev instance; no multi-user namespace.
- **Future required mitigation:** if multi-user is ever considered, per-user
  ownership + isolation; today: deferred.
- **Implementation stop condition:** multi-user namespace introduced without
  ownership ⇒ stop.
- **GO / NO-GO:** multi-user plugin confusion is **NO-GO** (deferred).

## RUNTIME-THREAT-29 — Plugin version downgrade attack

- **Description:** A plugin is downgraded to a vulnerable prior version, or a
  rollback swaps in an older, weaker descriptor / code.
- **Attack path:** version field manipulation; rollback to pre-patch version.
- **Impact:** re-introduction of a patched vulnerability.
- **Likelihood:** Low.
- **Severity:** Medium.
- **Current mitigation:** descriptors are static, pinned, reviewed source.
- **Future required mitigation:** monotonic version floor; downgrade rejection;
  signed manifest pinning (future).
- **Implementation stop condition:** downgrade path exists ⇒ stop.
- **GO / NO-GO:** version downgrade is **NO-GO**.

## RUNTIME-THREAT-30 — Kill switch bypass

- **Description:** A runtime path continues to operate after the kill switch is
  thrown, or the kill switch is unreachable from the runtime layer.
- **Attack path:** runtime caches a dispatch path past the kill switch; kill
  switch checked too late (after secret read / network).
- **Impact:** the runtime cannot be stopped cleanly.
- **Likelihood:** Low.
- **Severity:** High.
- **Current mitigation:** no runtime exists; the Phase 3B-Live-Enablement kill
  switch governs provider live, not runtime.
- **Future required mitigation:** a dedicated runtime kill switch checked before
  secret read / network / dispatch; fail-closed on kill.
- **Implementation stop condition:** no dedicated runtime kill switch ⇒ stop.
- **GO / NO-GO:** kill switch bypass is **NO-GO**.

---

## Summary

| Category | Threats | Default verdict |
|----------|---------|-----------------|
| Code execution / sandbox / process breakout | 01–03 | NO-GO until sandbox + process models approved |
| Filesystem / network / secret / production exfiltration | 04–07 | NO-GO until filesystem + network + secret models approved |
| Shell / DB / supply-chain / registry / marketplace | 08–12 | NO-GO until supply-chain policy approved |
| Provider- / LLM-generated injection | 13–14 | NO-GO |
| Permission / gate bypass | 15–18 | NO-GO |
| Audit / artifact / prompt / token leak | 19, 21–23 | NO-GO |
| Production rollout / DoS / persistence / dev-prod / multi-user / downgrade / kill switch | 20, 24–30 | NO-GO |

Every high-severity threat resolves to **NO-GO** until the corresponding sandbox /
process / filesystem / network / supply-chain / audit / kill-switch model is
approved. The default verdict for the whole runtime surface is:

```
NO-GO until sandbox / process / filesystem / network / supply-chain /
audit / kill-switch models are approved.
```

## Cross-references

- [Phase 3E planning](phase-3e-planning.md)
- [Phase 3E runtime scope freeze](phase-3e-runtime-scope-freeze.md)
- [Phase 3E sandbox architecture](phase-3e-sandbox-architecture.md)
- [Phase 3E risk register](phase-3e-risk-register.md)
- [Phase 3E runtime GO / NO-GO](phase-3e-runtime-go-no-go.md)
- [Phase 3D threat model](phase-3d-threat-model.md)
- [Phase 3D real runtime NO-GO](phase-3d-real-runtime-no-go.md)
- [Phase 3C capability threat model](phase-3c-capability-threat-model.md)
