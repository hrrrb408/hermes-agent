# Phase 3F Gap Analysis — Real Plugin Runtime Readiness

| Field | Value |
|-------|-------|
| Phase | 3F (Planning) |
| Title | Real Plugin Runtime — Implementation Readiness Gap Analysis |
| Gap-Analysis ID | `PHASE-3F-GAP-ANALYSIS-001` |
| Date | 2026-06-19 |
| Branch | `dev-huangruibang` |
| Status | Docs-only gap analysis — does **not** authorize implementation |

> This document is docs-only.
> This document identifies implementation-readiness gaps only.
> This document does not authorize implementation.
> This document does not authorize real plugin runtime.
> This document does not authorize plugin execution.
> This document does not authorize dynamic loading.
> This document does not authorize production rollout.
> This document does not authorize new routes.

## A. Gap summary

Real plugin runtime implementation remains **blocked**. Phase 3E designed, but
did not approve, the models a future runtime would require; Phase 3F Planning
inventories the concrete gaps that must be closed before any implementation
could be considered.

```
Real runtime implementation readiness: NO-GO
All gaps below: planning-only, none resolved by this document.
```

## B. Gap categories

### 1. Sandbox model gaps

- **Current state:** four sandbox options compared in Phase 3E (A descriptor-only
  / B in-process / C out-of-process worker / D containerized); no executable
  proof exists.
- **Missing decisions:** which option advances; Option C vs Option D for a
  production-grade boundary.
- **Blocking questions:** is out-of-process sufficient, or is container isolation
  mandatory?
- **Required evidence:** an executable sandbox proof-of-concept plan and a
  reviewed boundary test design.
- **Stop condition:** no approved sandbox model ⇒ STOP.
- **Future owner / review:** security reviewer + implementation owner.

### 2. Process isolation gaps

- **Current state:** process-isolation model designed (boundary, IPC, resource
  limits, kill switch); not implemented or approved.
- **Missing decisions:** worker lifecycle states, supervision, and teardown.
- **Blocking questions:** how is a runaway worker killed deterministically?
- **Required evidence:** worker lifecycle plan + IPC confinement proof design.
- **Stop condition:** no approved process-isolation model ⇒ STOP.
- **Future owner / review:** security reviewer.

### 3. Filesystem boundary gaps

- **Current state:** deny-by-default dev sandbox designed; no enforcement proof.
- **Missing decisions:** allowlist scope, path normalization, mount strategy.
- **Blocking questions:** can a worker reach `~/.hermes` or production paths?
- **Required evidence:** filesystem enforcement proof design.
- **Stop condition:** no approved filesystem-boundary model ⇒ STOP.
- **Future owner / review:** security reviewer.

### 4. Network boundary gaps

- **Current state:** network disabled by default designed; no enforcement proof.
- **Missing decisions:** allowlist model, egress policy, DNS handling.
- **Blocking questions:** can a worker make outbound calls?
- **Required evidence:** network enforcement proof design.
- **Stop condition:** no approved network-boundary model ⇒ STOP.
- **Future owner / review:** security reviewer.

### 5. Supply-chain verification gaps

- **Current state:** no package install by default designed; no provenance proof.
- **Missing decisions:** signed-manifest policy, dependency pinning, trust roots.
- **Blocking questions:** how is an untrusted plugin source refused?
- **Required evidence:** package-provenance proof design.
- **Stop condition:** no approved supply-chain policy ⇒ STOP.
- **Future owner / review:** security reviewer.

### 6. Permission / capability mapping gaps

- **Current state:** runtime inherits most-restrictive permission designed;
  Phase 3C capability IDs are static and descriptive only.
- **Missing decisions:** capability-to-permission binding at runtime, escalation
  rules.
- **Blocking questions:** can a plugin escalate beyond its bound capability?
- **Required evidence:** permission-escalation test design.
- **Stop condition:** any permission escalation ⇒ STOP.
- **Future owner / review:** route-governance / capability reviewer.

### 7. Audit / redaction gaps

- **Current state:** safe-fields-only, fail-closed model designed; no runtime
  audit store exists.
- **Missing decisions:** `runtime_*` event field schema, redaction rules,
  dual-write behavior.
- **Blocking questions:** what fields are forbidden; what happens on redaction
  failure?
- **Required evidence:** audit fail-closed proof design.
- **Stop condition:** no approved audit / redaction model ⇒ STOP.
- **Future owner / review:** audit / redaction reviewer.

### 8. Kill-switch gaps

- **Current state:** kill-switch concept exists in the process-isolation model;
  no kill-switch proof.
- **Missing decisions:** trigger conditions, blast radius, recovery.
- **Blocking questions:** can the kill switch fail open?
- **Required evidence:** kill-switch proof design.
- **Stop condition:** no approved kill switch ⇒ STOP.
- **Future owner / review:** production safety reviewer.

### 9. UI / review-flow gaps

- **Current state:** runtime-disabled banner and NO-GO card designed; no runtime
  UI implemented.
- **Missing decisions:** approval UX, evidence attachment, risk acknowledgment.
- **Blocking questions:** what must be shown before a human approves?
- **Required evidence:** UI warning / review-flow plan.
- **Stop condition:** runtime UI shipped before approval flow ⇒ STOP.
- **Future owner / review:** UI reviewer.

### 10. Route governance gaps

- **Current state:** no new route; 34 / 34 / 5 / 0 / 1 / 1 baseline.
- **Missing decisions:** whether a future runtime needs routes; exception
  process if it does.
- **Blocking questions:** can a runtime avoid routes entirely?
- **Required evidence:** route-governance exception plan.
- **Stop condition:** any new route without approval ⇒ STOP.
- **Future owner / review:** route-governance reviewer.

### 11. Production isolation gaps

- **Current state:** no production access; production rollout NO-GO.
- **Missing decisions:** `productionAllowed=false` policy, deploy-time fail-closed.
- **Blocking questions:** what guard prevents production reach?
- **Required evidence:** production isolation proof design.
- **Stop condition:** any production impact ⇒ STOP.
- **Future owner / review:** production safety reviewer.

### 12. Testing strategy gaps

- **Current state:** test categories enumerated in Phase 3F planning; no runtime
  tests added.
- **Missing decisions:** which categories gate which stage; failure thresholds.
- **Blocking questions:** what test must fail if an unauthorized route appears?
- **Required evidence:** approved test strategy.
- **Stop condition:** no approved test strategy ⇒ STOP.
- **Future owner / review:** implementation owner + security reviewer.

### 13. Human approval gaps

- **Current state:** review roles and evidence defined in Phase 3F planning; no
  signoff exists.
- **Missing decisions:** quorum, evidence checklist, acknowledgment of STOP
  conditions.
- **Blocking questions:** who approves a future runtime?
- **Required evidence:** human-review signoff.
- **Stop condition:** no human-review signoff ⇒ STOP.
- **Future owner / review:** project owner.

### 14. Rollback / incident-response gaps

- **Current state:** rollback concept exists; no plan approved for
  implementation.
- **Missing decisions:** rollback triggers, monitoring, alerting.
- **Blocking questions:** how is a bad runtime deployment reverted?
- **Required evidence:** rollback / incident-response plan.
- **Stop condition:** no rollback plan ⇒ STOP.
- **Future owner / review:** production safety reviewer.

### 15. Developer experience gaps

- **Current state:** no developer-facing runtime workflow exists.
- **Missing decisions:** how developers author descriptors without execution;
  how they observe NO-GO state.
- **Blocking questions:** can a developer accidentally enable runtime?
- **Required evidence:** developer-experience plan.
- **Stop condition:** developer workflow bypasses review ⇒ STOP.
- **Future owner / review:** UI reviewer + implementation owner.

### 16. Documentation and traceability gaps

- **Current state:** Phase 3E archived; Phase 3F planning in progress.
- **Missing decisions:** how future implementation traces back to approved
  models and gates.
- **Blocking questions:** is every future code change traceable to an approval?
- **Required evidence:** traceability matrix design.
- **Stop condition:** untraceable implementation ⇒ STOP.
- **Future owner / review:** project owner.

## C. Top unresolved blockers

```
no executable sandbox proof
no worker lifecycle plan approved for implementation
no file/network enforcement proof
no secret handling proof
no package provenance proof
no runtime audit storage plan approved for implementation
no route-governance exception process for runtime endpoints
no production isolation proof
no kill-switch proof
no end-to-end failure-mode test plan
```

## D. Gap disposition

```
Every listed gap is planning-only.
No gap is resolved by this document.
Any future resolution requires separate explicit authorization.
```

## Cross-references

- [Phase 3F planning](phase-3f-planning.md)
- [Phase 3F readiness roadmap](phase-3f-readiness-roadmap.md)
- [Phase 3F P0 gate consolidation](phase-3f-p0-gate-consolidation.md)
- [Phase 3F implementation entry review](phase-3f-implementation-entry-review.md)
- [Phase 3F test strategy planning](phase-3f-test-strategy-planning.md)
- [Phase 3F risk register](phase-3f-risk-register.md)
- [Phase 3E risk register](phase-3e-risk-register.md)
- [Phase 3E implementation entry criteria](phase-3e-implementation-entry-criteria.md)
