# Phase 3E–3H P0 Evidence Matrix

| Field | Value |
|-------|-------|
| Title | Phase 3E–3H P0 Evidence Consolidation & Hardening — Evidence Matrix |
| Kind | **Evidence matrix, not governance.** This is not a closeout, signoff, archive, review-board decision, go/no-go ledger, or authorization. |
| Branch | `dev-huangruibang` |
| Inherited P0 gate set | `PHASE-3F-P0-GATES-001` (24 gates) |
| Implementation Authorization | **NO-GO** (unchanged) |
| Real plugin runtime | **NO-GO** (unchanged) |
| Production rollout | **NO-GO** (unchanged) |
| New route | **NO-GO** (unchanged) |
| Phase 3I | **NOT AUTHORIZED** unless separately requested |

## A. Scope

This matrix records the P0 evidence state **after** the Phase 3E–3H Missing
Implementation Recovery task **and** the follow-on P0 Evidence Consolidation &
Hardening pass. It references **code and test evidence only**. It does **not**:

- authorize implementation,
- authorize a real plugin runtime,
- authorize Phase 3I,
- authorize a production rollout,
- authorize a new route,
- close, sign off, archive, or make a review-board decision,
- start a new docs-only governance loop.

It exists solely to trace the implemented safety baseline + dev-only sandbox
proof skeleton (and the hardening pass over them) to the inherited 24 P0 gates.
**No P0 gate is marked RESOLVED.** Gate approval requires human reviewers and
project-owner authorization that this work is explicitly forbidden to perform.

## B. Current code evidence

Dev-only, stdlib-only, side-effect-free modules (none imported by the FastAPI
app; none execute a plugin, load a plugin, dynamic-import, network, read a real
secret, or touch production):

- `hermes_cli/dev_web_safety_baseline.py` — route governance introspection,
  production isolation (string-only), forbidden-path protection, runtime-store
  scan, read-only `.claude` git check, no-side-effect flags.
- `hermes_cli/dev_web_sandbox_guards.py` — filesystem boundary guard, network
  deny guard, secrets-unavailable/redaction guard.
- `hermes_cli/dev_web_sandbox_policy.py` — capability default-deny evaluator,
  kill-switch policy, descriptor-only enforcement.
- `hermes_cli/dev_web_sandbox_audit.py` — in-memory redacted audit record.
- `hermes_cli/dev_web_sandbox_proof.py` — `SandboxProofRequest` /
  `SandboxProofResult` orchestrator (skeleton, not a runtime).

Hardening pass added: backslash-traversal normalization + case-insensitive
`.hermes` detection (baseline); network scheme markers + IPv6 loopback +
`.env`-style secret detection (guards); descriptor-id safety +
capability-injection rejection + kill-switch fail-closed-on-invalid-state
(policy); redacted `errorDetail` (audit); request/result defensive deep-copies
(proof).

## C. Current test evidence

- `tests/test_dev_web_phase_3e_h_safety_baseline.py` (37 tests) — route
  governance, production isolation, forbidden-path protection, runtime-store
  scan, `.claude` exclusion.
- `tests/test_dev_web_phase_3h_sandbox_proof_skeleton.py` (107 tests) —
  descriptor-only, capability deny, guards, kill-switch, audit, source boundary.
- `tests/test_dev_web_phase_3e_h_p0_evidence_hardening.py` — this hardening
  pass: P0 matrix, immutability, descriptor/capability/filesystem/network/
  secret edge cases, kill-switch override denial, audit in-memory, source
  boundary, dev-web API isolation, route counts, no persistent artifacts.

## D. P0 Evidence Matrix

Statuses: `PARTIAL EVIDENCE` (code/test exists but no approval), `GOVERNANCE
ONLY` (no code evidence; policy/not-granted), `UNRESOLVED` (open). Nothing is
`RESOLVED`.

| P0 ID | Gate theme | Status | Code evidence | Test evidence | Remaining gap | Verdict |
|-------|-----------|--------|---------------|---------------|---------------|---------|
| P0-01 | Sandbox model | PARTIAL EVIDENCE | `dev_web_sandbox_proof.py` skeleton (fail-closed, default-deny) | sandbox-proof skeleton suite | skeleton ≠ an approved sandbox model; no runtime | NOT RESOLVED |
| P0-02 | Process isolation | PARTIAL EVIDENCE | `process.spawn` denied; no subprocess in sandbox modules | capability + source-boundary tests | no approved process-isolation model | NOT RESOLVED |
| P0-03 | Filesystem boundary | PARTIAL EVIDENCE | `evaluate_path_safety`, `evaluate_filesystem_path`, traversal/symlink/case/runtime-store denial | filesystem guard + hardening suites | not an approved boundary model; production never opened | NOT RESOLVED |
| P0-04 | Network boundary | PARTIAL EVIDENCE | `evaluate_network_target` (always denies); no socket/requests/httpx | network guard + hardening suites | intent-level deny only; no approved network policy | NOT RESOLVED |
| P0-05 | Supply-chain policy | GOVERNANCE ONLY | none | none | no supply-chain policy introduced | UNRESOLVED |
| P0-06 | Permission model | PARTIAL EVIDENCE | `CAPABILITY_LABELS`, `evaluate_capability` (default-deny, labels only) | capability deny + hardening suites | labels grant nothing at runtime; no real permission model | NOT RESOLVED |
| P0-07 | Audit / redaction model | PARTIAL EVIDENCE | `dev_web_sandbox_audit.py` (in-memory, redacted), redaction utilities | audit + redaction + hardening suites | in-memory only; no durable audit approved | NOT RESOLVED |
| P0-08 | Kill switch | PARTIAL EVIDENCE | `evaluate_kill_switch` (fail-closed; invalid-state fail-closed; no process signal) | kill-switch + hardening suites | dev-only flag; not a production kill switch | NOT RESOLVED |
| P0-09 | Production isolation | PARTIAL EVIDENCE | `classify_hermes_home`, `is_production_home/state_db` (string-only) | production-isolation suite | not an approved isolation boundary; no runtime | NOT RESOLVED |
| P0-10 | Secret handling ambiguity | PARTIAL EVIDENCE | redaction patterns (sk-/ghp_/xox/Bearer/PEM/env-line); `evaluate_secret_request` always denies | redaction + hardening suites | defense-in-depth only; no approved secret model; no real secret read | NOT RESOLVED |
| P0-11 | Filesystem / network ambiguity | PARTIAL EVIDENCE | pure deterministic evaluators; unambiguous deny | edge-case suites | not approved by reviewers | NOT RESOLVED |
| P0-12 | Unapproved execution path | PARTIAL EVIDENCE (not introduced) | descriptor-only enforcement; no plugin execution/loader/import path exists | source-boundary tests | proven absent; remains "not introduced" | NOT RESOLVED |
| P0-13 | Production impact | PARTIAL EVIDENCE (not introduced) | `~/.hermes` referenced only as a denial target; no production access | production-isolation + no-artifacts suites | none introduced | NOT RESOLVED |
| P0-14 | Route governance | PARTIAL EVIDENCE | `route_governance_counts`, `assert_route_governance_unchanged` (`34/34/5/0/1/1`) | route-governance + hardening suites | baseline frozen unchanged; no exception approval granted | NOT RESOLVED |
| P0-15 | No implementation authorization | GOVERNANCE ONLY | n/a (authorization is not code) | matrix asserts NO-GO | authorization not granted | UNRESOLVED |
| P0-16 | No runtime endpoint authorization | GOVERNANCE ONLY | no runtime endpoint wired | dev-web API isolation tests | not granted | UNRESOLVED |
| P0-17 | No runtime artifact storage authorization | GOVERNANCE ONLY | in-memory audit only; no durable store | no-persistent-artifacts tests | no durable store approved | UNRESOLVED |
| P0-18 | No plugin source trust decision | GOVERNANCE ONLY | descriptor-only denies executable surfaces; no trust decision made | descriptor + source-boundary tests | no trust decision made | UNRESOLVED |
| P0-19 | No worker lifecycle approval | GOVERNANCE ONLY | no worker lifecycle code | none | not granted | UNRESOLVED |
| P0-20 | No failure-mode approval | PARTIAL EVIDENCE | fail-closed defaults (kill-switch, redaction, decision coercion, invalid-state) | failure-mode + hardening suites | not an approved failure-mode plan | NOT RESOLVED |
| P0-21 | No rollback plan | GOVERNANCE ONLY | none | none | not approved | UNRESOLVED |
| P0-22 | No human review signoff | GOVERNANCE ONLY | n/a | none | not started | UNRESOLVED |
| P0-23 | No incident response plan | GOVERNANCE ONLY | none | none | not approved | UNRESOLVED |
| P0-24 | No test strategy approval | PARTIAL EVIDENCE | 144 prior tests + hardening suite | all targeted suites pass | not an approved strategy by reviewers | NOT RESOLVED |

## E. Evidence-to-test mapping

- `test_dev_web_phase_3e_h_safety_baseline.py` → P0-03, P0-09, P0-13, P0-14.
- `test_dev_web_phase_3h_sandbox_proof_skeleton.py` → P0-01, P0-03, P0-04,
  P0-06, P0-07, P0-08, P0-10, P0-11, P0-12, P0-20, P0-24.
- `test_dev_web_phase_3e_h_p0_evidence_hardening.py` → P0-01, P0-03, P0-04,
  P0-06, P0-07, P0-08, P0-10, P0-11, P0-12, P0-14, P0-17, P0-20, P0-24
  (and re-asserts every NO-GO).

## F. Remaining gaps

Still missing before any gate could advance:

- human approval / review-board signoff,
- an actual executable sandbox proof (not a skeleton),
- real isolation proof (process / filesystem / network) under an approved model,
- production-grade rollback validation,
- route-governance exception approval (not needed; baseline unchanged),
- implementation-authorization review,
- real-runtime authorization,
- production authorization,
- an approved test strategy, failure-mode plan, rollback plan, and incident-response plan.

## G. Conservative conclusion

- Implementation Authorization remains **NO-GO**.
- Real plugin runtime remains **NO-GO**.
- The sandbox proof is **dev-only** (a skeleton; not a runtime).
- Phase 3I remains **not authorized**.
- New route remains **NO-GO**.
- Production rollout remains **NO-GO**.

No P0 gate is resolved. Zero gates are approved. This matrix records partial
code/test evidence only; it grants nothing.
