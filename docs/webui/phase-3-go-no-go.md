# Phase 3 GO / NO-GO

## Document Information

| Field | Value |
|-------|-------|
| Phase | 3 Planning |
| Title | Phase 3 GO / NO-GO — Phase 3A Handoff Decision |
| Status | Decision recorded — Phase 3A **implemented** (dev-only, within the frozen scope) |
| Date | 2026-06-15 |
| Branch | `dev-huangruibang` |
| Planning ID | `PHASE-3-PLANNING-001` |
| Decision ID | `PHASE-3-GO-NOGO-001` |

---

## 1. Decision

| Field | Value |
|-------|-------|
| Decision | **GO** for Phase 3A prompt preparation |
| Recommended Phase 3A | Dev-only Agent Workflow MVP |
| Phase 3A execution | not started |
| Human approval required before execution | yes |
| Phase 3A may start | only after the user explicitly asks for the Phase 3A prompt / implementation |
| Phase 3A may code | only inside `dev-huangruibang`, separately authorized |
| Phase 3A may use real provider | **no** |
| Phase 3A may write | preview / sandbox only (reuse Phase 2C gate); **no autonomous write** |
| Phase 3A may production rollout | **no** |
| Shell / DB / external-service write allowed in Phase 3A | **no** |

---

## 2. Basis for Decision

- Phase 2 is **functionally complete** for dev-only controlled tool execution
  and auditability (read-only tools, provider fake round-trip, sandbox write,
  rollback, durable audit storage, unified console, frontend UX hardening).
- Phase 2E-H1 closed the console UX hardening pass (9 / 9 lenses PASS, 0 P0,
  0 P1). Route governance is unchanged at 34 / 34 / 5 / 0 / 1 / 1 and the
  Production Gateway PID `28428` is untouched.
- Five Phase 3 candidate directions were evaluated. The recommended path is
  Dev-only Agent Workflow MVP (3A) → Real Provider (3B) → Plugin Registry
  (3C) → Production Pilot (3D) → Audit Compliance (3E). See
  [phase-3-options-evaluation.md](phase-3-options-evaluation.md).
- Phase 3A is the lowest-risk, highest-readiness, fully dev-only, fully
  reversible slice. It reuses the entire Phase 2 capability chain and becomes
  the container for later phases.
- All P0 risks are stop conditions (none introduced by this planning phase);
  P1 risks are execution-phase push-gates; P2 risks are deferred sequencing.
  See [phase-3-risk-register.md](phase-3-risk-register.md).

---

## 3. What GO Authorizes

GO authorizes **preparing** the Phase 3A handoff only:

- Authoring the Phase 3A execution brief ([phase-3a-execution-brief.md](phase-3a-execution-brief.md)).
- Authoring the Phase 3A prompt draft ([phase-3a-prompt.md](phase-3a-prompt.md)).
- Committing and pushing this docs-only planning phase
  (`docs(webui): plan phase 3 scope`).

---

## 4. What GO Does Not Authorize

GO does **not** authorize:

- Starting Phase 3A implementation.
- Any product / frontend / backend / script change.
- Enabling a real provider.
- Provider auto-write / auto-rollback.
- Autonomous write.
- Shell command / database mutation / external service write.
- Production rollout.
- `~/.hermes` or production `state.db` access.
- A new HTTP route, Tool write HTTP route, or Provider route.
- Stopping / restarting / replacing / signaling the Production Gateway.

---

## 5. Phase 3A Entry Gate (restated)

Phase 3A may start only when **all** are true:

1. The user explicitly asks for the Phase 3A execution prompt / implementation.
2. Phase 3A is separately authorized by the user.
3. Branch = `dev-huangruibang`; tree clean (only `.claude/` untracked).
4. Route governance unchanged (34 / 34 / 5 / 0 / 1 / 1) or an explicitly
   approved, separately-authorized change.
5. Production Gateway PID healthy (`28428`) or consciously refreshed by a
   separately authorized safety phase.
6. `~/.hermes` and production `state.db` not accessed.
7. `PHASE-3-PLANNING-001` committed and pushed.
8. The Phase 3A prompt draft is the approved starting brief.

---

## 6. NO-GO Conditions

The decision becomes **NO-GO** (stop, do not push, do not proceed) if, during
a future Phase 3A execution:

- Phase 3A scope is violated (real provider, autonomous write, shell / db /
  external write, production rollout, route drift, secret exposure).
- The Production Gateway PID drifts from `28428` or count != `1`.
- Route governance drifts without an approved change.
- Any P0 risk materializes.
- Any P1 push-gate fails.

---

## 7. Phase 3B Planning Update (2026-06-16)

Phase 3A has since been **implemented** and hardened (Phase 3A-H1), so the Phase
3A container that Phase 3B was sequenced behind now exists. The next slice —
**Phase 3B — Real Provider Read-only Controlled Integration** — has now had its
own **GO for prompt preparation only** decision recorded in a separate docs-only
planning phase (`PHASE-3B-PLANNING-001`, decision `PHASE-3B-GO-NOGO-001`),
without being implemented. The Phase 3B decision keeps every constraint of this
Phase 3 decision (separately authorized, human-approval-gated, no autonomous
write, no shell / db / external write, no production rollout, default no new
route) and additionally pins: real provider **disabled by default**, **read-only**
only, env-only API key, no UI key input, full audit + redaction. See
[phase-3b-go-no-go](phase-3b-go-no-go.md) and
[phase-3b-planning](phase-3b-planning.md).

---

## 8. Cross-References

- [Phase 3 planning](phase-3-planning.md)
- [Phase 3 scope freeze](phase-3-scope-freeze.md)
- [Phase 3 risk register](phase-3-risk-register.md)
- [Phase 3A execution brief](phase-3a-execution-brief.md)
- [Phase 3A prompt draft](phase-3a-prompt.md)
- [Phase 3B planning](phase-3b-planning.md)
- [Phase 3B GO / NO-GO](phase-3b-go-no-go.md)

---

## 9. Phase 3C Planning Update (2026-06-17)

After Phase 3A (+ H1), Phase 3B (+ H1), and Phase 3B-Live-Enablement (+ H1)
shipped, the next slice — **Phase 3C — Plugin / Capability Registry** — has now
had its own **GO for implementation-prompt preparation only** decision recorded
in a separate docs-only planning phase (`PHASE-3C-PLANNING-001`, decision
`PHASE-3C-GO-NOGO-001`), without being implemented. The Phase 3C decision keeps
every constraint of this Phase 3 decision (separately authorized, human-approval-
gated, no autonomous write, no shell / db / external write, no production
rollout, default no new route) and additionally pins: a **static, dev-only,
descriptive** capability registry (grants no permission), a frozen permission /
trust taxonomy, a static manifest with a forbidden-fields list, a no-dynamic-
loading policy, and `capability_registry_*` audit. **NO-GO** for a dynamic plugin
runtime, external plugin loading, remote registry / marketplace, production
rollout, provider write, and autonomous write. **Phase 3C Implementation was not
started.** See [phase-3c-go-no-go](phase-3c-go-no-go.md) and
[phase-3c-planning](phase-3c-planning.md).

---

## 10. Phase 3C Implementation + 3C-H1 Hardening Update (2026-06-18)

Phase 3C (Static dev-only Capability Registry) was subsequently **implemented**
(`PHASE-3C-IMPL-001`) and then **hardened** by `HARDENING-3C-H1-001` (12 / 12
lenses PASS, P0 = 0, P1 = 0). The hardening pass closed one real defect
(recursive forbidden-field scan + scalar type guard) and bounded every boundary
with tests, a new smoke profile (Profile Q,
`phase3c_h1_capability_registry_hardening`), and the hardening audit script
`scripts/run-dev-webui-phase3c-hardening-audit.sh`. Every Phase 3 / 3C NO-GO
still holds: no plugin runtime, no dynamic loading, no remote registry /
marketplace, no provider write, no autonomous write, no production rollout, no
new route, no `~/.hermes` / production `state.db` access. Route governance
unchanged (34 / 34 / 5 / 0 / 1 / 1). **Phase 3D (Plugin Runtime) was not
started.** See [Phase 3C-H1 hardening](phase-3c-h1-capability-registry-hardening.md)
and [Phase 3C implementation](phase-3c-static-capability-registry-implementation.md).

---

## 11. Phase 3C Closeout Update (2026-06-18)

Phase 3C is formally **closed** as a static dev-only Capability Registry
milestone (`PHASE-3C-CLOSEOUT-001`, docs-only). Final state: static / dev-only
/ read-only / descriptive-only; 12 / 12 hardening lenses PASS; P0 = 0, P1 = 0.
Every Phase 3 / 3C NO-GO still holds: no plugin runtime, dynamic loading,
remote registry, marketplace, provider write, autonomous write, production
rollout, new route, or `~/.hermes` / production `state.db` access. Route
governance unchanged (34 / 34 / 5 / 0 / 1 / 1). **Phase 3D Planning is
CONDITIONAL GO (only after explicit user request); Phase 3D Implementation is
NO-GO.** See [Phase 3C closeout](phase-3c-closeout.md) and
[Phase 3C final GO / NO-GO](phase-3c-final-go-no-go.md).

---

## 12. Phase 3D Planning Update (2026-06-18)

The docs-only **Phase 3D Planning** (`PHASE-3D-PLANNING-001`, decision
`PHASE-3D-GO-NOGO-001`) has now been prepared — exactly the conditional GO this
document recorded (only after explicit user request). It keeps every constraint of
this Phase 3 decision (separately authorized, human-approval-gated, no autonomous
write, no shell / db / external write, no production rollout, default no new
route) and additionally freezes a future **dev-only, static, reviewed,
capability-bound** plugin descriptor runtime architecture: descriptor-only (no
execution), capability-bound to existing Phase 3C IDs, disabled-by-default,
audit-only-dry-run, no dynamic loading, no remote registry, no marketplace, no
external plugin fetch, no provider-generated plugin, no LLM-generated plugin
install, no provider write. **GO** for Phase 3D Planning completion + Phase 3D
Implementation prompt preparation only after explicit user request. **NO-GO** for
Phase 3D Implementation, plugin runtime, dynamic loading, remote registry,
marketplace, external plugin fetch, provider-generated plugin, LLM-generated
plugin install, shell execution, DB mutation, external HTTP execution, production
operation, provider write, autonomous write, and production rollout. Route
governance unchanged (34 / 34 / 5 / 0 / 1 / 1). **Phase 3D Implementation was not
started.** See [Phase 3D planning](phase-3d-planning.md) and
[Phase 3D GO / NO-GO](phase-3d-go-no-go.md).

---

## 13. Phase 3D Planning Closeout Update (2026-06-18)

Phase 3D Planning is formally **closed** (`PHASE-3D-PLANNING-CLOSEOUT-001`,
docs-only). The final GO / NO-GO is recorded in
[phase-3d-final-go-no-go.md](phase-3d-final-go-no-go.md): **GO** for the planning
closeout + human review package + implementation prompt preparation (after
explicit user request); **NO-GO** for Phase 3D Implementation, plugin runtime,
plugin loader, dynamic loading, local plugin directory loading, remote registry,
marketplace, external plugin fetch, provider-generated plugin, LLM-generated
plugin install, shell execution, DB mutation, external HTTP execution, production
operation, provider write, autonomous write, production rollout, and live
provider execution as part of Phase 3D. Risk closure: P0 = 0, P1 = 0, P2 = 5
deferred. Route governance unchanged (34 / 34 / 5 / 0 / 1 / 1). **Phase 3D
Implementation was not started.** See
[Phase 3D planning closeout](phase-3d-planning-closeout.md).
