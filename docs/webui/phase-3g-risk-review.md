# Phase 3G Risk Review — Implementation Authorization

| Field | Value |
|-------|-------|
| Phase | 3G (Implementation Authorization Review) |
| Title | Real Plugin Runtime — Phase 3G Risk Review (Implementation Authorization) |
| Risk-Review ID | `PHASE-3G-RISK-REVIEW-001` |
| Date | 2026-06-19 |
| Branch | `dev-huangruibang` |
| Source commit | `f9de4c395f4eb05b2f3285cb254d8b46fcd568d7` |
| Status | Docs-only risk review — does **not** authorize implementation |

> This document is docs-only.
> This document reviews authorization risk only.
> This document does not authorize implementation.
> This document does not authorize real plugin runtime.
> This document does not authorize production rollout.
> This document does not authorize new routes.

## A. Risk review summary

Implementation authorization risk remains high if granted now.

```
Granting implementation authorization now would carry high residual risk.
The recommended posture is to keep Implementation Authorization = NO-GO.
```

This is a review of authorization risk only. It does not authorize
implementation, runtime, routes, or production rollout.

## B. Risk table

| Risk ID | Description | Severity | Likelihood | Implementation authorization impact | Mitigation | Stop condition | Reviewer |
| ------- | ----------- | -------- | ---------- | ---------------------------------- | ---------- | -------------- | -------- |
| PHASE3G-RISK-01 | Premature implementation authorization granted before gates clear | Critical | Medium | Would bypass every P0 gate and enable unproven runtime | Keep Implementation Authorization = NO-GO; require explicit authorization only after gates clear | Any authorization issued before P0 gates clear ⇒ STOP | project owner |
| PHASE3G-RISK-02 | False confidence from planning artifacts being read as readiness | High | Medium | Planning maturity mistaken for implementation readiness | Treat all Phase 3F artifacts as non-authorizing planning; require proof artifacts, not plans | Any planning artifact cited as authorization ⇒ STOP | project owner |
| PHASE3G-RISK-03 | Unresolved P0 gates ignored | Critical | Low | All 24 P0 gates remain unresolved | Keep all 24 gates blocking; resolve zero by this review | Any P0 gate treated as resolved without proof ⇒ STOP | security reviewer |
| PHASE3G-RISK-04 | Sandbox model under-proven (planned, not proven) | Critical | Medium | No executable sandbox proof approved | Require executable sandbox proof before any loader/execution consideration | Any sandbox claim without executable proof ⇒ STOP | security reviewer |
| PHASE3G-RISK-05 | Process isolation ambiguity (in-process vs out-of-process) | High | Medium | Ambiguous isolation boundary could allow in-process execution | Reject in-process execution for real runtime; require out-of-process baseline proof | Any in-process execution of untrusted code ⇒ STOP | security reviewer |
| PHASE3G-RISK-06 | Filesystem/network enforcement ambiguity | High | Medium | Unclear boundaries could permit unintended filesystem/network access | Require approved filesystem-boundary and network-boundary proofs | Any ambiguity in filesystem/network access ⇒ STOP | security reviewer |
| PHASE3G-RISK-07 | Secret (API key) exposure during runtime | Critical | Medium | Runtime could read or leak real API keys | Keep real API key reading NO-GO; require zero-ambiguity secret handling | Any real API key read or leak path ⇒ STOP | security reviewer |
| PHASE3G-RISK-08 | Route governance bypass introduces an unapproved route | High | Low | An unapproved route could enable runtime endpoints | Keep route governance unchanged (34/34/5/0/1/1); require explicit route approval | Any new route without route-governance approval ⇒ STOP | route-governance reviewer |
| PHASE3G-RISK-09 | Production bleed-through from dev runtime touching production state | Critical | Low | Runtime could affect production Gateway or production `state.db` | Keep production isolation; never access `~/.hermes` or production `state.db` | Any production impact ⇒ STOP | production safety reviewer |
| PHASE3G-RISK-10 | Audit/redaction leakage (planned, not implemented) | High | Medium | No approved audit/redaction store could allow unaudited or leaked actions | Require approved audit/redaction model before implementation | Any action without approved audit/redaction ⇒ STOP | audit reviewer |
| PHASE3G-RISK-11 | Human review overconfidence (planning signoff read as implementation signoff) | High | Medium | Planning-closeout signoff mistaken for implementation signoff | Keep human review signoff for implementation NOT STARTED | Any implementation begun on a planning-only signoff ⇒ STOP | project owner |
| PHASE3G-RISK-12 | Future subphase ambiguity (Phase 3H+ scope misunderstood as authorized) | Medium | Medium | Future subphases could be misread as authorized implementation | Keep all future subphases docs-only and explicit-request-only | Any future subphase started without explicit authorization ⇒ STOP | project owner |

```
Critical risks: PHASE3G-RISK-01, 03, 04, 07, 09.
High risks:     PHASE3G-RISK-02, 05, 06, 08, 10, 11.
Medium risks:   PHASE3G-RISK-12.
Each risk supports keeping Implementation Authorization = NO-GO.
```

## C. Risk conclusion

Risks support denying implementation authorization at this time.

```
Residual risk of authorizing implementation now: HIGH.
Recommended decision: Implementation Authorization = NO-GO.
Risks are documented, not retired against an implementation.
No risk is accepted as resolved for implementation purposes.
```

## Cross-references

- [Phase 3G implementation authorization review](phase-3g-implementation-authorization-review.md)
- [Phase 3G implementation authorization decision](phase-3g-implementation-authorization-decision.md)
- [Phase 3G P0 gate resolution review](phase-3g-p0-gate-resolution-review.md)
- [Phase 3G readiness evidence review](phase-3g-readiness-evidence-review.md)
- [Phase 3F risk register](phase-3f-risk-register.md)
- [Phase 3E risk register](phase-3e-risk-register.md)
