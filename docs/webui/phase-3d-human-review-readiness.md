# Phase 3D — Human Review Readiness

| Field | Value |
|-------|-------|
| Phase | 3D (Planning Closeout) |
| Title | Plugin Runtime Planning — Human Review Readiness Package |
| Status | Ready for human review |
| Date | 2026-06-18 |
| Planning ID | `PHASE-3D-PLANNING-001` |
| Closeout ID | `PHASE-3D-PLANNING-CLOSEOUT-001` |

> A decision package for the human reviewer of the Phase 3D Planning closeout. It
> states what was decided, what was deliberately **not** authorized, and what
> decisions the reviewer must make.

## 1. Executive summary

Phase 3D Planning froze the architecture of a future Plugin Runtime as a
**dev-only, static, reviewed, capability-bound** plugin descriptor runtime
skeleton — **descriptor-only, no execution**. It is a docs-only milestone. No
plugin runtime, loader, dynamic loading, remote registry, marketplace, external
plugin fetch, provider-generated plugin, LLM-generated plugin install, shell / DB
/ external-HTTP / production execution, provider write, autonomous write,
production rollout, new route, `~/.hermes` access, production `state.db` access,
API-key read, or network call was introduced. Route governance is unchanged
(34 / 34 / 5 / 0 / 1 / 1); Production Gateway PID `28428` is untouched.

## 2. What Phase 3D Planning decided

- A future Plugin Runtime, if ever authorized, is **descriptor-only** (no
  execution), **dev-only**, **capability-bound** to existing Phase 3C IDs,
  **disabled-by-default**, and **audit-only-dry-run**.
- It must start from **static reviewed descriptors**, not executable external
  plugins.
- The trust boundary, manifest contract, lifecycle, execution isolation, audit
  policy, UI, test strategy, threat model, and risk register are frozen.

## 3. What Phase 3D Planning did NOT authorize

Implementation execution; plugin runtime; plugin loader; dynamic loading; local
plugin directory loading; remote registry; marketplace; external plugin fetch;
provider-generated plugin; LLM-generated plugin install; shell execution; DB
mutation; external HTTP execution; production operation; provider write;
autonomous write; production rollout; new route; `~/.hermes` access; production
`state.db` access; API-key read; network call; live provider execution (which
remains separately gated).

## 4. Required human decisions

The reviewer must answer each (yes / no):

1. Allow entry into Phase 3D Implementation **prompt preparation**?
2. Keep Implementation **execution NO-GO**?
3. Accept a **descriptor-only** first version?
4. Continue to forbid plugin **runtime execution**?
5. Continue to forbid **dynamic loading**?
6. Continue to forbid **local plugin directory loading**?
7. Continue to forbid **remote registry**?
8. Continue to forbid **marketplace**?
9. Continue to forbid **external plugin fetch**?
10. Continue to forbid **provider-generated plugin**?
11. Continue to forbid **shell / DB / external HTTP / production operation**?
12. Continue to forbid **new route by default**?

## 5. Implementation readiness

- **Implementation prompt preparation readiness: CONDITIONAL GO** (only after an
  explicit user request).
- **Implementation execution readiness: NO-GO** (requires separate explicit
  approval + all 13 entry criteria; see
  [phase-3d-implementation-readiness-review.md](phase-3d-implementation-readiness-review.md)).

## 6. Review focus areas

- **Security review focus:** no execution surface; forbidden-fields rejection;
  no-leak across descriptor / read model / audit / UI; capability-bound permission
  inheritance (no escalation). See
  [phase-3d-final-security-boundary.md](phase-3d-final-security-boundary.md).
- **Route governance focus:** no new route; status rides the existing `/status`
  block; 34 / 34 / 5 / 0 / 1 / 1. See [phase-3d-final-security-boundary.md](phase-3d-final-security-boundary.md).
- **Production isolation focus:** PID `28428` untouched; no `~/.hermes` access;
  no production `state.db` access; dev `HERMES_HOME` only.

## 7. Risk posture

22 P0 stop conditions, 8 P1 push-gates (govern a **future** implementation; none
introduced by planning), 5 P2 deferrals (intentional, non-blocking). See
[phase-3d-risk-closure.md](phase-3d-risk-closure.md).

## 8. Recommended review conclusion

```
GO for implementation prompt preparation only.
NO-GO for implementation execution until explicit user approval.
NO-GO for plugin runtime execution.
NO-GO for dynamic loading.
NO-GO for remote registry.
NO-GO for marketplace.
NO-GO for production rollout.
```

## 9. Approval / rejection wording

- **Approval wording** (copy into the human approver checklist,
  [phase-3d-human-approver-checklist.md](phase-3d-human-approver-checklist.md)):

  > APPROVED: Prepare a Phase 3D Implementation prompt for a static dev-only
  > plugin descriptor registry skeleton only. This approval does not authorize
  > implementation execution, dynamic loading, plugin execution, remote registry,
  > marketplace, external plugin fetch, provider-generated plugin, new route, or
  > production rollout.

- **Rejection wording**:

  > REJECTED: Do not prepare Phase 3D Implementation prompt. Keep Phase 3D at
  > planning-closeout state.

## 10. Cross-references

- [Phase 3D planning closeout](phase-3d-planning-closeout.md)
- [Final GO / NO-GO](phase-3d-final-go-no-go.md)
- [Implementation readiness review](phase-3d-implementation-readiness-review.md)
- [Human approver checklist](phase-3d-human-approver-checklist.md)
- [Implementation prompt candidate](phase-3d-implementation-prompt-candidate.md)
