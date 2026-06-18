# Phase 3H Sandbox Proof Goals and Non-Goals

| Field | Value |
|-------|-------|
| Phase | 3H (Sandbox Proof Planning — Goals and Non-Goals) |
| Title | Real Plugin Runtime — Phase 3H Sandbox Proof Goals and Non-Goals |
| Planning ID | `PHASE-3H-PLANNING-001` |
| Date | 2026-06-19 |
| Branch | `dev-huangruibang` |
| Status | Docs-only planning — does **not** implement sandbox proof |

> This document is docs-only.
> This document defines proof goals and non-goals only.
> This document does not implement sandbox proof.
> This document does not authorize implementation.
> This document does not authorize real plugin runtime.
> This document does not authorize production rollout.
> This document does not authorize new routes.

## A. Proof purpose

The purpose of any future sandbox proof is:

- to verify whether an auditable, bounded, reversible, and killable sandbox boundary can
  exist;
- to verify whether such a boundary can be planned without touching production, without
  adding a route, without reading real secrets, and without executing a real plugin;
- to prepare the evidence requirements that a future Implementation Authorization Review
  would consult.

A future sandbox proof is a verification activity. It is not an authorization to run a real
plugin runtime. It is "ready" only for a future docs-only closeout / human review, not for
implementation.

```
This document defines goals.
This document does not satisfy any goal.
This document does not authorize any goal to be implemented.
```

## B. Proof goals

Each goal below is a planning goal. Each defines the evidence a future proof would need, the
evidence it may never accept, a stop condition, and a future review owner. None of these goals
is satisfied by this document.

### B.1 Process isolation proof goal

- Goal statement: a future proof must demonstrate that any worker is isolated from the main
  process and the gateway, with controlled lifecycle and bounded resource use.
- Required evidence (future): reproducible, dev-only process-boundary demonstration, worker
  lifecycle control, timeout / cancellation demonstration, redacted stdout / stderr.
- Unacceptable evidence: in-process simulation presented as real isolation; any main-process
  or gateway impact.
- Stop condition: worker lifecycle, process boundary, or main-process impact unclear.
- Future review owner: Phase 3H human reviewer / review board.

### B.2 Filesystem boundary proof goal

- Goal statement: a future proof must demonstrate a read-only or temporary-isolated
  filesystem boundary that can never reach `~/.hermes`, production `state.db`, production
  config, or secret files.
- Required evidence (future): path boundary definition, forbidden-path verification,
  temporary-directory cleanup, write-denial demonstration, symlink / traversal risk handling.
- Unacceptable evidence: any uncontrolled write path; any path ambiguity around `~/.hermes`
  or production `state.db`.
- Stop condition: any forbidden-path ambiguity or uncontrolled write path.
- Future review owner: Phase 3H human reviewer / review board.

### B.3 Network boundary proof goal

- Goal statement: a future proof must demonstrate that no external HTTP, provider request,
  remote registry, marketplace, telemetry, callback, or DNS dependency can occur.
- Required evidence (future): network-disabled demonstration, outbound-denial demonstration,
  provider-request-absence demonstration, denied-call audit trail.
- Unacceptable evidence: any allowed outbound network; any real API key exposure.
- Stop condition: any external network allowed or any provider request possible.
- Future review owner: Phase 3H human reviewer / review board.

### B.4 Permission / capability proof goal

- Goal statement: a future proof must demonstrate default-deny capability enforcement with
  auditable denied attempts and no capability escalation.
- Required evidence (future): default-deny demonstration, denied-attempt audit, no-escalation
  demonstration, human-review and kill-switch binding.
- Unacceptable evidence: default-allow; capability escalation; missing audit.
- Stop condition: default allow, escalation ambiguity, or missing audit.
- Future review owner: Phase 3H human reviewer / review board.

### B.5 Supply-chain trust proof goal

- Goal statement: a future proof must demonstrate that no remote registry, marketplace,
  external fetch, provider-generated plugin, or LLM-generated plugin install can occur, and
  that any reviewed source has provenance and a review record.
- Required evidence (future): source identity, provenance, static-review record, checksum /
  signature, dependency boundary, revocation plan.
- Unacceptable evidence: unknown source; generated-plugin install; external fetch; unsigned
  or unreviewed dependency.
- Stop condition: unknown source, generated-plugin install, external fetch, or
  unsigned / unreviewed dependency.
- Future review owner: Phase 3H human reviewer / review board.

### B.6 Audit / redaction proof goal

- Goal statement: a future proof must demonstrate that all relevant events are logged and all
  logs are redacted of secrets, tokens, Authorization headers, and real API keys.
- Required evidence (future): event-coverage demonstration, denied-attempt logging,
  redaction demonstration, no-secret-values demonstration.
- Unacceptable evidence: any unredacted secret possibility; missing denied-attempt audit;
  missing proof metadata.
- Stop condition: unredacted secret possibility, missing denied-attempt audit, or missing
  proof metadata.
- Future review owner: Phase 3H human reviewer / review board.

### B.7 Kill-switch proof goal

- Goal statement: a future proof must demonstrate a fail-closed kill-switch with visible
  disabled state, audit event, human-review boundary, and rollback linkage.
- Required evidence (future): fail-closed demonstration, disabled-state visibility,
  kill-switch audit event, rollback linkage.
- Unacceptable evidence: no fail-closed design; no audit; no human override boundary; no
  rollback plan.
- Stop condition: no fail-closed design, no audit, no human boundary, or no rollback plan.
- Future review owner: Phase 3H human reviewer / review board.

### B.8 Failure-mode proof goal

- Goal statement: a future proof must demonstrate bounded, auditable, redaction-safe behavior
  across defined failure categories (timeout, crash, denied write, denied network, denied
  secret read, malformed descriptor, oversized input, audit failure, redaction failure,
  kill-switch active, route absence, production isolation).
- Required evidence (future): per-category failure demonstration, no-production-impact
  demonstration, auditable failure demonstration.
- Unacceptable evidence: any failure that can affect the production gateway; any failure that
  bypasses redaction; any failure that changes routes.
- Stop condition: failure can affect production, is not auditable, bypasses redaction, or
  changes routes.
- Future review owner: Phase 3H human reviewer / review board.

### B.9 Rollback / incident-response proof goal

- Goal statement: a future proof must demonstrate how to disable proof, remove proof
  artifacts, verify no production impact, verify route count unchanged, verify no secrets
  touched, and recover from a failed proof.
- Required evidence (future): rollback plan, incident owner, production-isolation
  verification, route verification, recovery demonstration.
- Unacceptable evidence: no rollback plan; no incident owner; no production-isolation or
  route verification.
- Stop condition: no rollback plan, no incident owner, no production-isolation verification,
  or no route verification.
- Future review owner: Phase 3H human reviewer / review board.

### B.10 No-production-impact proof goal

- Goal statement: a future proof must demonstrate zero impact on Production Gateway PID
  28428, zero access to `~/.hermes`, and zero access to production `state.db`.
- Required evidence (future): production-PID unchanged demonstration, no-`~/.hermes`-access
  demonstration, no-production-`state.db`-access demonstration.
- Unacceptable evidence: any production PID change; any `~/.hermes` access; any production
  `state.db` access.
- Stop condition: production PID change, `~/.hermes` access, or production `state.db` access.
- Future review owner: Phase 3H human reviewer / review board.

### B.11 No-route-change proof goal

- Goal statement: a future proof must demonstrate route governance unchanged at
  34 / 34 / 5 / 0 / 1 / 1 and no new HTTP / Tool / Provider / plugin / runtime route.
- Required evidence (future): route-count-unchanged demonstration, route-definition-unchanged
  demonstration.
- Unacceptable evidence: any route count change; any route definition change; any new route.
- Stop condition: route count change, route definition change, or any new route.
- Future review owner: Phase 3H human reviewer / review board.

### B.12 No-secret-read proof goal

- Goal statement: a future proof must demonstrate that no real API key, token, credential,
  Authorization header, or Bearer value is read or exposed.
- Required evidence (future): no-secret-read demonstration, redacted-output demonstration.
- Unacceptable evidence: any real secret read or exposed.
- Stop condition: any real secret read or exposed.
- Future review owner: Phase 3H human reviewer / review board.

### B.13 Human-review proof goal

- Goal statement: a future proof must be human-reviewable, with planning that remains
  docs-only, all NO-GO boundaries preserved, and implementation still blocked.
- Required evidence (future): docs-only-confirmation, NO-GO-preservation demonstration,
  P0-unresolved-state confirmation, implementation-still-blocked confirmation.
- Unacceptable evidence: implementation started; any NO-GO reversed.
- Stop condition: implementation started or any NO-GO reversed.
- Future review owner: Phase 3H human reviewer / review board.

## C. Non-goals

A future sandbox proof must **not** prove or include:

- real plugin execution;
- production rollout;
- route addition;
- live provider execution;
- real API key access;
- external network call;
- database mutation;
- filesystem mutation outside an approved test boundary;
- dynamic loading of real plugins;
- marketplace / registry fetch;
- user-generated or LLM-generated plugin install.

```
These non-goals are non-authorizing by construction.
Each remains NO-GO / not approved.
```

## D. Evidence expectations

Any future evidence must be:

- reproducible;
- dev-only;
- non-production;
- no secret exposure;
- route-stable;
- no runtime persistence unless separately authorized;
- auditable;
- redaction-safe;
- human-reviewable.

```
Evidence that violates any of these expectations is unacceptable.
```

## E. Goal acceptance summary

This section defines planning-level acceptance only. It is **not** implementation acceptance.

- Planning acceptance: every goal above has a goal statement, required evidence, unacceptable
  evidence, a stop condition, and a future review owner.
- Planning acceptance does **not** mean any goal is satisfied.
- Goal satisfaction would require a separately authorized Phase 3H Sandbox Proof
  Implementation task, which remains NO-GO.
- Implementation Authorization remains NO-GO.

```
Planning acceptance = each goal is documented and bounded.
Implementation acceptance = NO-GO until separately and explicitly authorized.
```

## Cross-references

- [Phase 3H sandbox proof planning](phase-3h-sandbox-proof-planning.md)
- [Phase 3H boundary and inherited constraints](phase-3h-boundary-and-inherited-constraints.md)
- [Phase 3H sandbox model options](phase-3h-sandbox-model-options.md)
- [Phase 3H GO / NO-GO](phase-3h-go-no-go.md)
- [Phase 3H risk register](phase-3h-risk-register.md)
