# Phase 3H Risk Register — Sandbox Proof Planning

| Field | Value |
|-------|-------|
| Phase | 3H (Sandbox Proof Planning — Risk Register) |
| Title | Real Plugin Runtime — Phase 3H Sandbox Proof Planning Risk Register |
| Risk Register ID | `PHASE-3H-PLANNING-RISK-REGISTER-001` |
| Date | 2026-06-19 |
| Branch | `dev-huangruibang` |
| Status | Docs-only planning — records planning risks only |

> This document is docs-only.
> This document records planning risks only.
> This document does not authorize implementation.
> This document does not authorize sandbox proof implementation.
> This document does not authorize real plugin runtime.
> This document does not authorize production rollout.
> This document does not authorize new routes.

## Summary

This register records Phase 3H Sandbox Proof Planning risks. Each risk is a planning risk. The
mitigation for every risk is the same inherited boundary: this is docs-only planning,
implementation remains NO-GO, and any unresolved P0 means STOP toward implementation.

Severity scale: Low / Medium / High. Likelihood scale: Low / Medium / High.

```
This register resolves no P0 gate.
This register authorizes no implementation.
```

## PHASE3H-RISK-01 — Planning mistaken for implementation authorization

- Description: a reader could mistake this planning package for authorization to implement a
  sandbox proof.
- Severity: High.
- Likelihood: Medium.
- Impact: implementation started without a separate explicit authorization; NO-GO boundary
  violated.
- Mitigation: every Phase 3H document declares docs-only and that it does not authorize
  implementation; Phase 3H Sandbox Proof Implementation remains NO-GO.
- Stop condition: any implementation activity based on this planning means STOP.
- Owner / reviewer: Phase 3H human reviewer / review board.

## PHASE3H-RISK-02 — Sandbox proof implemented early

- Description: the sandbox proof could be implemented before any proof implementation is
  authorized.
- Severity: High.
- Likelihood: Low.
- Impact: code, runtime, loader, or execution introduced in violation of the NO-GO boundary.
- Mitigation: Phase 3H Sandbox Proof Implementation remains NO-GO; no worker, runtime, loader,
  or store is created by this planning.
- Stop condition: any sandbox proof artifact created means STOP.
- Owner / reviewer: Phase 3H human reviewer / review board.

## PHASE3H-RISK-03 — Process isolation underestimated

- Description: a future proof could under-specify process isolation and treat an in-process
  simulation as real isolation.
- Severity: High.
- Likelihood: Medium.
- Impact: an unbounded worker that can affect the main process or gateway.
- Mitigation: process isolation planning requires a real process boundary; in-process
  simulation is unacceptable evidence; any process-boundary ambiguity means STOP.
- Stop condition: process boundary or main-process impact unclear means STOP.
- Owner / reviewer: Phase 3H human reviewer / review board.

## PHASE3H-RISK-04 — Filesystem boundary ambiguity

- Description: a future proof could leave ambiguity around `~/.hermes`, production `state.db`,
  or production config.
- Severity: High.
- Likelihood: Medium.
- Impact: production data accessed or mutated.
- Mitigation: filesystem boundary planning forbids `~/.hermes`, production `state.db`,
  production config, and secret files; any path ambiguity means STOP.
- Stop condition: any `~/.hermes` or production `state.db` ambiguity means STOP.
- Owner / reviewer: Phase 3H human reviewer / review board.

## PHASE3H-RISK-05 — Network denial hard to prove

- Description: a future proof could struggle to demonstrate that no outbound network can
  occur.
- Severity: High.
- Likelihood: Medium.
- Impact: external network or provider request becomes possible.
- Mitigation: network boundary planning requires network-disabled and outbound-denial
  demonstration; any external network allowed means STOP.
- Stop condition: any external network or provider request possible means STOP.
- Owner / reviewer: Phase 3H human reviewer / review board.

## PHASE3H-RISK-06 — Secret exposure

- Description: a future proof could expose a real API key, token, Authorization header, or
  Bearer value.
- Severity: High.
- Likelihood: Low.
- Impact: secret leakage in logs, stdout, stderr, or error messages.
- Mitigation: audit / redaction planning requires full redaction; no-secret-read proof goal;
  any real secret read or exposed means STOP.
- Stop condition: any real secret read or exposed means STOP.
- Owner / reviewer: Phase 3H human reviewer / review board.

## PHASE3H-RISK-07 — Route governance bypass

- Description: a future proof could propose a new HTTP / Tool / Provider / plugin / runtime
  route.
- Severity: High.
- Likelihood: Low.
- Impact: route governance drifts from 34 / 34 / 5 / 0 / 1 / 1.
- Mitigation: route governance impact planning forbids route additions or changes; any route
  proposal requires a separate route-governance review; route count change means STOP.
- Stop condition: route count or definition change means STOP.
- Owner / reviewer: Phase 3H human reviewer / review board.

## PHASE3H-RISK-08 — Production bleed-through

- Description: a future proof could affect Production Gateway PID 28428 or access production
  state.
- Severity: High.
- Likelihood: Low.
- Impact: production process stopped, restarted, replaced, signaled, or production state
  accessed.
- Mitigation: production isolation constraints require dev-only operation; no production
  access; PID 28428 must remain unaffected; any production PID change or access means STOP.
- Stop condition: production PID change, `~/.hermes` access, or production `state.db` access
  means STOP.
- Owner / reviewer: Phase 3H human reviewer / review board.

## PHASE3H-RISK-09 — Supply-chain trust ambiguity

- Description: a future proof could leave plugin source identity or provenance ambiguous.
- Severity: High.
- Likelihood: Medium.
- Impact: an unknown or unreviewed source is treated as trusted.
- Mitigation: supply-chain trust planning forbids remote registry, marketplace, external fetch,
  provider-generated plugin, and LLM-generated plugin install; unknown source means STOP.
- Stop condition: unknown source, generated-plugin install, or external fetch means STOP.
- Owner / reviewer: Phase 3H human reviewer / review board.

## PHASE3H-RISK-10 — Capability escalation

- Description: a future capability model could allow escalation or default-allow.
- Severity: High.
- Likelihood: Medium.
- Impact: a capability grants more than intended, bypassing human review.
- Mitigation: permission / capability planning requires default-deny, auditable denied
  attempts, and no escalation; default allow or escalation ambiguity means STOP.
- Stop condition: default allow or capability escalation ambiguity means STOP.
- Owner / reviewer: Phase 3H human reviewer / review board.

## PHASE3H-RISK-11 — Audit / redaction leakage

- Description: a future audit trail could leak secret values, tokens, or production paths.
- Severity: High.
- Likelihood: Medium.
- Impact: secret or production-path leakage in audit records.
- Mitigation: audit / redaction planning requires redaction of secrets, tokens, headers, API
  keys, paths, credentials, stdout, stderr, and error messages; unredacted secret possibility
  means STOP.
- Stop condition: unredacted secret possibility or missing denied-attempt audit means STOP.
- Owner / reviewer: Phase 3H human reviewer / review board.

## PHASE3H-RISK-12 — Kill-switch incomplete

- Description: a future kill-switch could lack fail-closed behavior, audit, or human boundary.
- Severity: High.
- Likelihood: Medium.
- Impact: a proof that cannot be safely disabled.
- Mitigation: kill-switch planning requires fail-closed design, audit event, human override
  boundary, and rollback linkage; missing any of these means STOP.
- Stop condition: no fail-closed design, no audit, no human boundary, or no rollback plan
  means STOP.
- Owner / reviewer: Phase 3H human reviewer / review board.

## PHASE3H-RISK-13 — Failure-mode coverage insufficient

- Description: a future proof could under-cover failure categories.
- Severity: Medium.
- Likelihood: Medium.
- Impact: an untested failure mode escapes into production impact or redaction bypass.
- Mitigation: failure-mode test planning requires coverage of all listed failure categories;
  any failure that can affect production, is not auditable, bypasses redaction, or changes
  routes means STOP.
- Stop condition: any uncovered production-affecting or redaction-bypassing failure means
  STOP.
- Owner / reviewer: Phase 3H human reviewer / review board.

## PHASE3H-RISK-14 — Rollback incomplete

- Description: a future proof could lack a complete rollback or incident-response plan.
- Severity: High.
- Likelihood: Medium.
- Impact: a failed proof cannot be cleanly disabled or recovered.
- Mitigation: rollback / incident-response planning requires a rollback plan, incident owner,
  production-isolation verification, and route verification; missing any of these means STOP.
- Stop condition: no rollback plan, no incident owner, or no verification means STOP.
- Owner / reviewer: Phase 3H human reviewer / review board.

## PHASE3H-RISK-15 — Human review overconfidence

- Description: a future reviewer could over-trust planning and treat it as readiness for
  implementation.
- Severity: High.
- Likelihood: Medium.
- Impact: implementation authorized on planning alone.
- Mitigation: human review plan requires that signoff does not by default authorize
  implementation; Implementation Authorization remains NO-GO; this planning is "ready" only
  for a future docs-only closeout / human review.
- Stop condition: implementation authorized on planning alone means STOP.
- Owner / reviewer: Phase 3H human reviewer / review board.

## PHASE3H-RISK-16 — Generated plugin risk

- Description: a future proof could permit provider-generated or LLM-generated plugin install.
- Severity: High.
- Likelihood: Low.
- Impact: unreviewed generated code introduced as a plugin.
- Mitigation: supply-chain trust planning forbids provider-generated plugin and LLM-generated
  plugin install; generated-plugin install means STOP.
- Stop condition: any generated-plugin install means STOP.
- Owner / reviewer: Phase 3H human reviewer / review board.

## PHASE3H-RISK-17 — External fetch risk

- Description: a future proof could permit external plugin fetch, remote registry, or
  marketplace.
- Severity: High.
- Likelihood: Low.
- Impact: external code fetched and introduced.
- Mitigation: supply-chain and network planning forbid external fetch, remote registry, and
  marketplace; external fetch means STOP.
- Stop condition: any external fetch means STOP.
- Owner / reviewer: Phase 3H human reviewer / review board.

## PHASE3H-RISK-18 — Phase 3H follow-up task boundary unclear

- Description: the boundary between Phase 3H planning, Phase 3H closeout, Phase 3H signoff,
  and Phase 3H sandbox proof implementation could become unclear.
- Severity: Medium.
- Likelihood: Medium.
- Impact: a later task proceeds past its docs-only boundary.
- Mitigation: every Phase 3H document declares its scope and the inherited NO-GO boundaries;
  closeout, signoff, and implementation are each NOT STARTED or NO-GO and require separate
  explicit user requests; any scope creep means STOP.
- Stop condition: any follow-up task exceeding its docs-only boundary means STOP.
- Owner / reviewer: Phase 3H human reviewer / review board.

## Aggregate risk posture

```
Total risks recorded: 18
Risks that authorize implementation: 0
Risks resolved toward implementation: 0
```

```
This risk register does not authorize implementation.
This risk register does not authorize sandbox proof implementation.
This risk register does not authorize real plugin runtime.
This risk register does not authorize production rollout.
This risk register does not authorize new routes.
```

## Cross-references

- [Phase 3H sandbox proof planning](phase-3h-sandbox-proof-planning.md)
- [Phase 3H proof goals and non-goals](phase-3h-proof-goals-and-non-goals.md)
- [Phase 3H GO / NO-GO](phase-3h-go-no-go.md)
- [Phase 3F risk register](phase-3f-risk-register.md)
- [Phase 3G risk review](phase-3g-risk-review.md)
