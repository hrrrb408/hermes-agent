# Phase 3F Test Strategy Planning

| Field | Value |
|-------|-------|
| Phase | 3F (Planning) |
| Title | Real Plugin Runtime — Test Strategy Planning |
| Test-Strategy ID | `PHASE-3F-TEST-STRATEGY-001` |
| Date | 2026-06-19 |
| Branch | `dev-huangruibang` |
| Status | Docs-only test planning — does **not** add tests |

> This document is docs-only.
> This document plans future test categories only.
> This document does not authorize implementation.
> This document does not authorize real plugin runtime.
> This document does not authorize plugin execution.
> This document does not authorize dynamic loading.
> This document does not authorize production rollout.
> This document does not authorize new routes.

## A. Test planning summary

No tests are added by this document. This document enumerates the test
categories a **future** implementation would need, and the evidence each would
have to produce, so reviewers can see what "tested" would mean before any code
exists.

```
No tests added.
Test implementation: NO-GO.
```

## B. Required future test categories

```
sandbox enforcement tests
process isolation tests
filesystem boundary tests
network boundary tests
secret redaction tests
permission / capability tests
audit fail-closed tests
kill-switch tests
route governance tests
UI warning / review tests
supply-chain integrity tests
failure-mode tests
rollback tests
production isolation tests
```

## C. Future test evidence table

| Category | Objective | Future test type | Expected evidence | Failure condition | Required approval |
| -------- | --------- | ---------------- | ----------------- | ----------------- | ----------------- |
| Sandbox enforcement | worker cannot escape the sandbox | boundary / escape test | escape-attempt blocked log | any escape succeeds ⇒ FAIL | security reviewer |
| Process isolation | worker is supervised and teardown is deterministic | lifecycle test | clean teardown on kill | leaked worker ⇒ FAIL | security reviewer |
| Filesystem boundary | worker cannot reach forbidden paths | path-access test | denied path list | any forbidden path reached ⇒ FAIL | security reviewer |
| Network boundary | worker cannot make outbound calls | egress test | blocked egress log | any outbound call ⇒ FAIL | security reviewer |
| Secret redaction | no secret reaches an audit/UI/log surface | redaction test | redacted record | any secret leak ⇒ FAIL | audit reviewer |
| Permission / capability | plugin cannot escalate beyond its capability | escalation test | denied escalation | any escalation ⇒ FAIL | capability reviewer |
| Audit fail-closed | audit failure blocks the action | fail-closed test | blocked-action record | fail-open ⇒ FAIL | audit reviewer |
| Kill switch | kill switch halts the runtime deterministically | kill-switch test | halted state | kill switch fails ⇒ FAIL | production safety reviewer |
| Route governance | no unauthorized route appears | route-count test | count = 34/34/5/0/1/1 | any drift ⇒ FAIL | route-governance reviewer |
| UI warning / review | runtime-disabled banner and NO-GO card shown | UI smoke | banner present | banner absent ⇒ FAIL | UI reviewer |
| Supply-chain integrity | untrusted source is refused | provenance test | refused-source record | untrusted source accepted ⇒ FAIL | security reviewer |
| Failure-mode | each failure mode is handled safely | failure-injection test | safe-handling record | unsafe handling ⇒ FAIL | security reviewer |
| Rollback | a bad deployment reverts cleanly | rollback test | reverted state | rollback fails ⇒ FAIL | production safety reviewer |
| Production isolation | production is unreachable | production-reach test | unreachable record | any production reach ⇒ FAIL | production safety reviewer |

## D. Current verdict

```
Test Strategy    = PLANNING ONLY
Test implementation = NO-GO
```

## Cross-references

- [Phase 3F planning](phase-3f-planning.md)
- [Phase 3F P0 gate consolidation](phase-3f-p0-gate-consolidation.md)
- [Phase 3F implementation entry review](phase-3f-implementation-entry-review.md)
- [Phase 3F audit and redaction planning](phase-3f-audit-redaction-planning.md)
- [Phase 3F route governance planning](phase-3f-route-governance-planning.md)
- [Phase 3F GO / NO-GO](phase-3f-go-no-go.md)
