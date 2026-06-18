# Phase 3C — GO / NO-GO

## Document Information

| Field | Value |
|-------|-------|
| Phase | 3C (Planning) |
| Title | Capability Registry — GO / NO-GO |
| Status | Decision recorded — Capability Registry **implemented** (Phase 3C static dev-only registry; no dynamic loading, no marketplace, no remote registry) |
| Date | 2026-06-17 |
| Branch | `dev-huangruibang` |
| Planning ID | `PHASE-3C-PLANNING-001` |
| Decision ID | `PHASE-3C-GO-NOGO-001` |

## 1. Decision

| Field | Value |
|-------|-------|
| Decision | **GO** for Phase 3C implementation prompt preparation only |
| Capability Registry implemented | **no** (not started) |
| Static dev-only registry scope frozen | **yes** |
| Dynamic plugin runtime | **no** (NO-GO) |
| External plugin loading | **no** (NO-GO) |
| Remote registry / marketplace | **no** (NO-GO) |
| Production rollout | **no** (NO-GO) |
| Provider write | **no** (NO-GO) |
| Autonomous write | **no** (NO-GO) |
| New route by default | **no** (NO-GO) |
| Phase 3C implementation may start | only after the user explicitly authorizes |

## 2. Basis

- Phase 3B-Live-Enablement shipped and Phase 3B-Live-H1 hardened the strict
  manual one-shot live gate (11 / 11 lenses PASS, P0 = 0, P1 = 0). The manual
  one-shot live execution remains NO-GO until separately authorized.
- This planning phase freezes the minimal safe shape of a future **static,
  dev-only Capability Registry** — descriptive only, no dynamic loading, no
  marketplace, no remote registry, no new route by default, no production
  rollout — without implementing it.
- The Capability Registry is a read-only descriptive layer; it grants no
  permission and relaxes no existing gate.

## 3. What GO authorizes

GO authorizes **preparing** the Phase 3C handoff only:

- Authoring the execution brief ([phase-3c-execution-brief.md](phase-3c-execution-brief.md)).
- Authoring the prompt draft ([phase-3c-prompt.md](phase-3c-prompt.md)).
- Committing and pushing this docs-only planning phase
  (`docs(webui): plan phase 3c capability registry`).

## 4. What GO does NOT authorize

- Starting the Capability Registry implementation.
- Any product / frontend / backend / script change.
- Creating `dev_web_capability_registry*.py` or `CapabilityRegistry*.vue`.
- Modifying `toolsets.py`, runtime stores, or `state.db`.
- Adding any HTTP route, Provider route, or Tool write route.
- Dynamic loading, marketplace, remote registry, remote manifest, arbitrary-URL
  fetch, provider-generated plugin, LLM-generated tool as plugin, self-modifying
  capability, auto-enable.
- Reading any API key, performing any network call, accessing `~/.hermes` /
  production `state.db`.
- Provider write / auto-write / autonomous write / shell / db / external write.
- Production rollout.
- Stopping / restarting / replacing / signaling the Production Gateway.

## 5. Phase 3C entry gate (future)

Phase 3C implementation may start only when **all** are true:

1. The user explicitly asks for the Phase 3C implementation.
2. Phase 3C is separately authorized by the user.
3. Branch = `dev-huangruibang`; tree clean (only `.claude/` untracked).
4. Route governance unchanged (34 / 34 / 5 / 0 / 1 / 1) or an explicitly
   approved, separately-authorized change.
5. Production Gateway PID healthy (`28428`) or consciously refreshed by a
   separately authorized safety phase.
6. `~/.hermes` and production `state.db` not accessed.
7. `PHASE-3C-PLANNING-001` committed and pushed.
8. The Phase 3C prompt draft is the approved starting brief.
9. The implementation stays within the frozen scope: **static dev-only registry
   only**, no dynamic loading, no marketplace, no remote registry, no new route
   by default, no production rollout.

## 6. NO-GO conditions

The decision becomes **NO-GO** (stop, do not push, do not proceed) if, during a
future Phase 3C execution:

- The frozen scope is violated (dynamic loading, marketplace, remote registry,
  arbitrary-URL fetch, provider-generated / LLM-generated plugin, auto-enable,
  self-modifying capability, secret / callable / path leak, route drift,
  production rollout, `~/.hermes` / production `state.db` access).
- The Production Gateway PID drifts from `28428` or count ≠ `1`.
- Route governance drifts without an approved change.
- Any P0 risk materializes.
- Any P1 push-gate fails.

## 7. Cross-references

- [Phase 3C planning](phase-3c-planning.md)
- [Phase 3C scope freeze](phase-3c-capability-registry-scope-freeze.md)
- [Phase 3C risk register](phase-3c-security-risk-register.md)
- [Phase 3C execution brief](phase-3c-execution-brief.md)
- [Phase 3C prompt draft](phase-3c-prompt.md)
- [Phase 3 GO / NO-GO](phase-3-go-no-go.md)

---

## 8. Phase 3C Implementation + 3C-H1 Hardening Update (2026-06-18)

Phase 3C (Static dev-only Capability Registry) was subsequently **implemented**
(`PHASE-3C-IMPL-001`) and then **hardened** by `HARDENING-3C-H1-001` (12 / 12
lenses PASS, P0 = 0, P1 = 0). The hardening pass closed one real defect
(recursive forbidden-field scan + scalar type guard) and bounded every boundary
with tests, a smoke profile (Profile Q), and a hardening audit script. Every
NO-GO of this decision still holds: no plugin runtime, no dynamic loading, no
remote registry / marketplace, no provider write, no autonomous write, no
production rollout, no new route, no `~/.hermes` / production `state.db`
access. Route governance unchanged (34 / 34 / 5 / 0 / 1 / 1). **Phase 3D
(Plugin Runtime) was not started.** See
[Phase 3C-H1 hardening](phase-3c-h1-capability-registry-hardening.md) and
[Phase 3C implementation](phase-3c-static-capability-registry-implementation.md).

---

## 9. Phase 3C Closeout Update (2026-06-18)

Phase 3C is formally **closed** (`PHASE-3C-CLOSEOUT-001`, docs-only). Final
state: static / dev-only / read-only / descriptive-only Capability Registry;
12 / 12 hardening lenses PASS; P0 = 0, P1 = 0; nested forbidden-field leak
closed. Every NO-GO of this decision still holds. Route governance unchanged
(34 / 34 / 5 / 0 / 1 / 1). **Phase 3D Planning is CONDITIONAL GO (explicit
user request only); Phase 3D Implementation is NO-GO.** See
[Phase 3C closeout](phase-3c-closeout.md),
[Phase 3C final GO / NO-GO](phase-3c-final-go-no-go.md), and
[Phase 3D entry criteria](phase-3c-phase-3d-entry-criteria.md).
