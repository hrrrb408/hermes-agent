# Phase 3D — Human Review Release Package

| Field | Value |
|-------|-------|
| Phase | 3D (Closeout) |
| Title | Static Plugin Descriptor Registry — Human Review Release Package |
| Status | Ready for human review |
| Date | 2026-06-19 |
| Package ID | `PHASE-3D-HUMAN-REVIEW-RELEASE-PACKAGE-001` |

> The final decision package for the human reviewer of the Phase 3D closeout. It
> states what was implemented, what was hardened, what remains forbidden, what is
> safe to review, what is not production-ready, what a future runtime requires,
> and the decisions the reviewer must make.

## 1. Executive summary

Phase 3D delivered a **static dev-only Plugin Descriptor Registry** —
descriptor-only, disabled-by-default, capability-bound, read-only. It describes
12 descriptors (3 visible, 4 disabled, 5 blocked) that bind only to existing
Phase 3C capabilityIds. It implements no plugin runtime, no loader, no dynamic
loading, no local plugin directory loading, no remote registry, no marketplace,
no external plugin fetch, no provider-generated plugin, no LLM-generated plugin
install, no shell / DB / external-HTTP / production execution, no provider write,
no autonomous write, no new route, and no production access. Phase 3D-H1
hardened it across 12 lenses; **no implementation code changed** — no defect
required a fix. P0 = 0; P1 = 0. Route governance is unchanged (34 / 34 / 5 / 0 /
1 / 1); Production Gateway PID `28428` is untouched.

## 2. What was implemented

- Static plugin descriptor schema + manifest (12 descriptors; pure data).
- Descriptor validation + recursive forbidden-field rejection (canonical + alias
  + nested + scalar-string type guard).
- Capability binding to existing Phase 3C capabilityIds; most-restrictive
  permission inheritance; trust-boundary classification.
- Static descriptor registry loader / read model / `/status` block builder
  (fail-closed).
- `pluginDescriptorRegistry` added to the **existing** `/status` response (no
  new route).
- `plugin_descriptor_*` audit bridge (redacted, no-leak, fail-safe).
- Read-only Dev WebUI Plugin Descriptor panel (summary / table / drawer / badges
  + runtime-disabled banner + `plugins` nav).

## 3. What was hardened (Phase 3D-H1)

12 lenses, all PASS: manifest consistency; forbidden fields; capability binding;
permission inheritance; trust boundary; non-execution; no dynamic loading;
provider / workflow boundary; audit no-leak; status API; UI a11y / no-leak;
smoke / preservation / production isolation. The hardening pass added 10 backend
+ 8 frontend hardening tests, the H1 smoke profile + spec, and the hardening
audit script (20 / 20 gates). No implementation code changed.

## 4. What remains forbidden

```
Real plugin runtime
Plugin loader execution
Plugin execution
Dynamic loading (importlib / __import__ / path load / directory scan)
Local plugin directory loading
Remote registry
Marketplace
External plugin fetch
Provider-generated plugin
LLM-generated plugin install
Shell / database / external-HTTP / production execution
Provider write
Autonomous write
Production rollout
New HTTP route
~/.hermes access
Production state.db access
```

## 5. What is safe to review

- The registry is exposed only through a value-free `/status` block and a
  read-only, no-leak, accessible Dev WebUI panel.
- `plugin_descriptor_*` audit is redacted and no-leak.
- There is **no execution surface** for a reviewer to trigger.
- The closeout documents state exactly what was implemented, hardened, and
  forbidden, with cross-linked evidence.

## 6. What is not production-ready

Phase 3D is **dev-only by design**. Every descriptor carries `devOnly = true`
and `productionAllowed = false`; the registry is gated by
`enforce_dev_environment()` and refuses the production HERMES_HOME. There is no
plan, authorization, or path to promote it to production. Production rollout is
NO-GO.

## 7. What a future runtime requires

A new planning phase, a runtime threat-model refresh, a sandbox model, a
process-isolation model, a filesystem-boundary model, a network-boundary model,
a supply-chain policy, a permission-model review, an audit-model review, a UI
review, a route-governance review, a production-isolation review, and explicit
user approval. None exists today; the runtime remains NO-GO.

## 8. Human reviewer decisions

The reviewer must answer each (yes / no):

1. Approve closing Phase 3D as a **dev-only static descriptor registry**
   milestone?
2. Keep **real plugin runtime** execution NO-GO?
3. Keep **plugin loader** execution NO-GO?
4. Keep **dynamic loading** NO-GO?
5. Keep **local plugin directory loading** NO-GO?
6. Keep **remote registry** NO-GO?
7. Keep **marketplace** NO-GO?
8. Keep **external plugin fetch** NO-GO?
9. Keep **provider-generated plugin** NO-GO?
10. Keep **LLM-generated plugin install** NO-GO?
11. Keep **shell / DB / external-HTTP / production operation** forbidden?
12. Keep **new route by default** forbidden?
13. Keep **production rollout** NO-GO?
14. Allow **Phase 3E Planning** (docs-only) to be considered later, only after
    explicit approval?

## 9. Recommended decision

```
APPROVE Phase 3D closeout as a dev-only static descriptor registry milestone.
DO NOT approve real plugin runtime execution.
DO NOT approve dynamic loading.
DO NOT approve remote registry.
DO NOT approve marketplace.
DO NOT approve production rollout.
```

## 10. Approval / rejection wording

- **Approval wording** (copy into the human approver record):

  > APPROVED: Close Phase 3D as a dev-only static Plugin Descriptor Registry
  > milestone. This approval does not authorize real plugin runtime execution,
  > plugin loader execution, dynamic loading, local plugin directory loading,
  > remote registry, marketplace, external plugin fetch, provider-generated
  > plugin, LLM-generated plugin install, new route, or production rollout.

- **Rejection wording**:

  > REJECTED: Do not close Phase 3D. Address listed review findings before
  > closeout.

## 11. Evidence index

- [Closeout](phase-3d-closeout.md)
- [Release readiness](phase-3d-release-readiness.md)
- [Final acceptance](phase-3d-final-acceptance.md)
- [Final security boundary after H1](phase-3d-final-security-boundary-after-h1.md)
- [Risk closure after H1](phase-3d-risk-closure-after-h1.md)
- [Test gate summary after H1](phase-3d-test-gate-summary-after-h1.md)
- [Production isolation summary](phase-3d-production-isolation-summary.md)
- [Route governance summary](phase-3d-route-governance-summary.md)
- [Known limitations / deferred work](phase-3d-known-limitations-and-deferred-work.md)
- [Real runtime NO-GO](phase-3d-real-runtime-no-go.md)
- [Phase 3E entry criteria](phase-3d-phase-3e-entry-criteria.md)
- [Implementation](phase-3d-static-plugin-descriptor-registry-implementation.md)
- [H1 hardening](phase-3d-h1-plugin-descriptor-registry-hardening.md)
- [H1 test report](phase-3d-h1-test-report.md)

## 12. Cross-references

- [Human review readiness (planning)](phase-3d-human-review-readiness.md)
- [Human approver checklist](phase-3d-human-approver-checklist.md)
- [Review board decision template](phase-3d-review-board-decision-template.md)
- [Final GO / NO-GO](phase-3d-final-go-no-go.md)
