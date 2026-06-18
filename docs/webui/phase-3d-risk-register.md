# Phase 3D — Risk Register

| Field | Value |
|-------|-------|
| Phase | 3D (Planning) |
| Title | Plugin Runtime — Risk Register (P0 / P1 / P2) |
| Status | Recorded |
| Date | 2026-06-18 |
| Branch | `dev-huangruibang` |
| Planning ID | `PHASE-3D-PLANNING-001` |
| Risk-Register ID | `PHASE-3D-RISK-REGISTER-001` |

> **Planning Closeout (2026-06-18):** The risk register is **closed** at the
> planning baseline — P0 introduced by planning = 0, P1 = 0, P2 deferred = 5. See
> [phase-3d-risk-closure.md](phase-3d-risk-closure.md). All P0/P1 items govern a
> **future** implementation; none was introduced by this docs-only phase.

> Companion to [phase-3d-planning.md](phase-3d-planning.md). This register is
> **additive** to the Phase 3 risk register; it does not relax any P0 / P1 there.
> None of these risks is **introduced** by this planning phase — this is docs-only.
> They govern a **future** Phase 3D implementation.

Each risk follows: ID · Severity · Description · Impact · Mitigation · Gate ·
Blocking condition.

---

## 1. P0 Risks (block / stop immediately)

### PLUG-P0-01 — Plugin runtime implemented during planning

- **Severity:** P0
- **Description:** Any plugin runtime / loader code is written in this docs-only
  phase.
- **Impact:** Breaks the docs-only invariant; introduces an execution surface.
- **Mitigation:** docs-only discipline; boundary search rejects implementation
  files.
- **Blocking condition:** any plugin runtime code committed.

### PLUG-P0-02 — Dynamic import introduced

- **Description:** `importlib` / `__import__` / path-based load introduced.
- **Impact:** arbitrary code execution.
- **Mitigation:** frozen no-dynamic-loading policy; AST scan; audit
  `plugin_no_dynamic_loading_checked`.
- **Blocking condition:** any dynamic import path.

### PLUG-P0-03 — Local plugin directory loading introduced

- **Description:** The runtime reads a user plugin directory / scans the FS.
- **Impact:** untrusted file influences the descriptor set; path traversal.
- **Mitigation:** forbid directory scan; `localPath` forbidden.
- **Blocking condition:** any local plugin directory read.

### PLUG-P0-04 — Remote registry introduced

- **Description:** A remote registry / remote manifest fetch is added.
- **Impact:** supply-chain attack.
- **Mitigation:** forbid remote registry; no remote fetch.
- **Blocking condition:** any remote registry / remote fetch.

### PLUG-P0-05 — Marketplace introduced

- **Description:** A plugin marketplace is added.
- **Impact:** malicious plugin install.
- **Mitigation:** forbid marketplace.
- **Blocking condition:** any marketplace path.

### PLUG-P0-06 — External plugin fetch introduced

- **Description:** Arbitrary-URL plugin fetch is added.
- **Impact:** untrusted-code download + execution.
- **Mitigation:** forbid `externalUrl` / `downloadUrl` / `remoteUrl` honoring.
- **Blocking condition:** any external plugin fetch.

### PLUG-P0-07 — Provider-generated plugin introduced

- **Description:** A provider response can create / install a plugin.
- **Impact:** untrusted model output gains an execution path.
- **Mitigation:** freeze provider boundary; provider responses cannot mutate the
  descriptor set.
- **Blocking condition:** any provider-generated plugin.

### PLUG-P0-08 — LLM-generated tool auto-install introduced

- **Description:** An LLM-generated tool is auto-installed as a plugin.
- **Impact:** untrusted model output executes.
- **Mitigation:** forbid auto-install.
- **Blocking condition:** any auto-install of an LLM-generated tool.

### PLUG-P0-09 — Shell command execution introduced

- **Description:** A plugin path invokes a shell.
- **Impact:** arbitrary command execution; sandbox escape.
- **Mitigation:** forbid `shellCommand`; reject `subprocess` / `os.system` /
  `shell=True`.
- **Blocking condition:** any shell execution.

### PLUG-P0-10 — Database mutation introduced

- **Description:** A plugin writes to a database / production `state.db`.
- **Impact:** persisted state corruption; production touched.
- **Mitigation:** forbid `sqlStatement`; no DB mutation.
- **Blocking condition:** any database mutation.

### PLUG-P0-11 — External HTTP execution introduced

- **Description:** A plugin performs outbound HTTP.
- **Impact:** data exfiltration; unauthorized side effects.
- **Mitigation:** forbid external HTTP in plugin paths.
- **Blocking condition:** any outbound network call from a plugin path.

### PLUG-P0-12 — Production operation introduced

- **Description:** A plugin reaches production paths.
- **Impact:** production exposure.
- **Mitigation:** forbid `productionPath`; `productionAllowed=false`;
  `enforce_dev_environment()`.
- **Blocking condition:** any production operation.

### PLUG-P0-13 — Permission grant bypass introduced

- **Description:** A descriptor grants permission / elevates its class.
- **Impact:** privilege escalation.
- **Mitigation:** descriptor inherits bound capability's class; no escalation.
- **Blocking condition:** any permission grant by a descriptor.

### PLUG-P0-14 — Tool policy bypass introduced

- **Description:** A plugin path skips dry-run / confirmation / audit.
- **Impact:** unauthorized execution.
- **Mitigation:** plugins inherit the existing tool policy; no new execution path.
- **Blocking condition:** any tool-policy bypass.

### PLUG-P0-15 — Provider live gate bypass introduced

- **Description:** A plugin triggers a live provider request without the live gate.
- **Impact:** unauthorized live cost / secret use.
- **Mitigation:** plugins cannot reach the provider live path.
- **Blocking condition:** any provider live gate bypass.

### PLUG-P0-16 — Workflow approval bypass introduced

- **Description:** A plugin auto-advances / writes inside a workflow.
- **Impact:** unauthorized step execution / write.
- **Mitigation:** plugins cannot mutate workflow state.
- **Blocking condition:** any workflow approval bypass.

### PLUG-P0-17 — Audit bypass introduced

- **Description:** A plugin action is not audited, or audit fails open.
- **Impact:** loss of traceability.
- **Mitigation:** mandatory fail-closed audit for every lifecycle event.
- **Blocking condition:** any audit bypass.

### PLUG-P0-18 — Secret / callable / path leak introduced

- **Description:** A descriptor / read model / audit / UI surfaces a secret,
  callable repr, or production / plugin path.
- **Impact:** secret / internal exposure.
- **Mitigation:** forbidden-fields recursive scan + safe read-model allowlist +
  defensive re-redaction; no-leak tests.
- **Blocking condition:** any secret / callable / path leak.

### PLUG-P0-19 — Route governance drift introduced

- **Description:** A plugin implementation adds an HTTP / Tool write / Provider
  route.
- **Impact:** surface / boundary drift.
- **Mitigation:** no new route by default; status rides `/status`.
- **Gate:** `test_dev_check_webui.py` + `test_dev_web_0c06_closure.py`.
- **Blocking condition:** route count drifts from 34 / 34 without approval.

### PLUG-P0-20 — `~/.hermes` or production `state.db` access introduced

- **Description:** A plugin path reaches `~/.hermes` / production `state.db`.
- **Impact:** production touched.
- **Mitigation:** `enforce_dev_environment()` allowlist; boundary search.
- **Blocking condition:** any `~/.hermes` / production `state.db` access.

### PLUG-P0-21 — Runtime artifact committed

- **Description:** A runtime artifact (store / JSONL / token / runtime manifest)
  is committed.
- **Impact:** secret / state leak into the repo.
- **Mitigation:** descriptors are tracked source; runtime data is gitignored;
  boundary search.
- **Blocking condition:** any runtime artifact staged.

### PLUG-P0-22 — `.claude/` committed

- **Description:** `.claude/` is staged / committed.
- **Impact:** session / state leak.
- **Mitigation:** verify `.gitignore`; never stage `.claude/`.
- **Blocking condition:** any `.claude/` staged.

---

## 2. P1 Risks (block push until resolved)

### PLUG-P1-01 — Trust boundary ambiguity

- **Description:** A descriptor's zone vs Phase 3C trust level contradicts.
- **Impact:** mis-classification.
- **Mitigation:** frozen zone ↔ trust-level mapping; consistency test.

### PLUG-P1-02 — Descriptor schema ambiguity

- **Description:** A field's type / cardinality is unclear.
- **Impact:** validator drift.
- **Mitigation:** frozen manifest contract; required-field + type tests.

### PLUG-P1-03 — Permission mapping ambiguity

- **Description:** Descriptor permission class vs bound capability class unclear.
- **Impact:** accidental escalation.
- **Mitigation:** `min(declared, bound)` rule; escalation test.

### PLUG-P1-04 — UI implies plugin executable

- **Description:** The UI suggests a disabled descriptor is runnable.
- **Impact:** operator confusion; pressure to enable.
- **Mitigation:** runtime-disabled banner; "does not execute plugin" label; UI
  tests.

### PLUG-P1-05 — Audit event missing

- **Description:** A lifecycle step runs without its audit event.
- **Impact:** audit gap.
- **Mitigation:** every step audited; fail-closed; audit-linkage test.

### PLUG-P1-06 — Phase 3C registry binding ambiguity

- **Description:** A descriptor binds to a non-existent / stale capability ID.
- **Impact:** dangling binding.
- **Mitigation:** binding resolves against the live registry; test.

### PLUG-P1-07 — Phase 3B live boundary ambiguity

- **Description:** A descriptor is mistaken for a live-provider trigger.
- **Impact:** confusion about live gating.
- **Mitigation:** plugins cannot trigger live; boundary doc.

### PLUG-P1-08 — Phase 3A workflow boundary ambiguity

- **Description:** A descriptor is mistaken for a workflow step.
- **Impact:** confusion about workflow gating.
- **Mitigation:** plugins cannot create / advance workflows; boundary doc.

---

## 3. P2 Risks (recorded, non-blocking)

### PLUG-P2-01 — Generated frontend descriptor mirror deferred

- A generator that derives the frontend descriptor mirror from the backend is
  deferred (hand-maintained mirror first, drift bounded by a consistency test).

### PLUG-P2-02 — Runtime isolation implementation deferred

- The concrete runtime isolation (sandboxing, should execution ever be allowed)
  is deferred; the first version is descriptor-only, so there is nothing to
  sandbox.

### PLUG-P2-03 — Multi-user plugin ownership deferred

- Descriptors have a single `owner` label; per-user ownership is deferred.

### PLUG-P2-04 — Plugin version migration deferred

- Descriptor version migration / upgrade tooling is deferred.

### PLUG-P2-05 — Plugin marketplace explicitly deferred

- A marketplace is **explicitly deferred** (and forbidden) — not merely
  unimplemented.

---

## 4. Summary

| Tier | Count | Blocks Phase 3D Implementation? |
|------|-------|---------------------------------|
| P0 | 22 | Each is a stop condition; none is introduced by this planning phase |
| P1 | 8 | Block push until resolved (during a future implementation phase) |
| P2 | 5 | Non-blocking; recorded for sequencing |

## 5. Cross-references

- [Phase 3D planning](phase-3d-planning.md)
- [Phase 3D scope freeze](phase-3d-plugin-runtime-scope-freeze.md)
- [Phase 3D threat model](phase-3d-threat-model.md)
- [Phase 3D GO / NO-GO](phase-3d-go-no-go.md)
- [Phase 3 risk register](phase-3-risk-register.md)
- [Phase 3C security risk register](phase-3c-security-risk-register.md)

## Update — Phase 3D Implementation COMPLETE; risk posture unchanged

The static dev-only plugin descriptor registry skeleton was implemented without
introducing any of the deferred execution risks: no plugin runtime, no loader,
no dynamic loading, no local plugin directory loading, no remote registry /
marketplace / external plugin fetch, no provider-generated plugin, no
LLM-generated plugin install, no shell / DB / external-HTTP / production
execution, no provider write, no autonomous write, no new route. P0 = 0, P1 = 0;
the P2 plugin-runtime items remain deferred / NO-GO. Route governance unchanged
(34/34/5/0/1/1); Production Gateway PID `28428` untouched. See
[phase-3d-plugin-descriptor-security-boundary](phase-3d-plugin-descriptor-security-boundary.md).

## Update — Phase 3D-H1 Hardening COMPLETE

Phase 3D-H1 hardened the static dev-only plugin descriptor registry skeleton
(HARDENING-3D-H1-001). The hardening pass added 10 backend + 8 frontend
hardening tests, a `phase3d_h1_plugin_descriptor_registry_hardening` smoke
profile + spec, and `scripts/run-dev-webui-phase3d-hardening-audit.sh`. **No
implementation code changed** — no defect required a fix. All 12 lenses PASS;
P0 = 0; P1 = 0. The registry remains descriptor-only, disabled-by-default,
capability-bound, read-only, and dev-only — no plugin runtime, no loader, no
dynamic loading, no local plugin directory loading, no remote registry, no
marketplace, no external plugin fetch, no provider-generated plugin, no
LLM-generated plugin install. Route governance unchanged (34 / 34 / 5 / 0 / 1 /
1); Production Gateway PID `28428` untouched. See
[phase-3d-h1-plugin-descriptor-registry-hardening](phase-3d-h1-plugin-descriptor-registry-hardening.md)
and [phase-3d-h1-test-report](phase-3d-h1-test-report.md).

## Update — Phase 3D Closeout COMPLETE

Phase 3D is formally **closed** as a static dev-only Plugin Descriptor Registry
milestone (`PHASE-3D-CLOSEOUT-001`, docs-only). Final risk closure is recorded
in [phase-3d-risk-closure-after-h1](phase-3d-risk-closure-after-h1.md):
**P0 introduced by Phase 3D = 0; P1 = 0; P0 introduced by Phase 3D-H1 = 0; P1 =
0.** All 22 P0 stop conditions (PLUG-P0-01 … PLUG-P0-22) were NOT introduced;
all 8 P1 push-gates (PLUG-P1-01 … PLUG-P1-08) are closed; P2 deferred items are
runtime-related only (intentional deferrals, not defects). Route governance
unchanged (34 / 34 / 5 / 0 / 1 / 1); Production Gateway PID `28428` untouched.
Real plugin runtime execution remains NO-GO. See
[phase-3d-closeout](phase-3d-closeout.md) and
[phase-3d-real-runtime-no-go](phase-3d-real-runtime-no-go.md).
