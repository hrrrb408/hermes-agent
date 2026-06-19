# Phase 3E–3H P0 Evidence Matrix

| Field | Value |
|-------|-------|
| Title | Phase 3E–3H P0 Evidence Consolidation & Hardening — Evidence Matrix |
| Kind | **Evidence matrix, not governance.** This is not a closeout, signoff, archive, review-board decision, go/no-go ledger, or authorization. |
| Branch | `dev-huangruibang` |
| Inherited P0 gate set | `PHASE-3F-P0-GATES-001` (24 gates) |
| Latest update | Remaining P0 Gate Reduction (P0-05/15/16/17/18/19/21/22/23 reclassified; see §H) |
| Resolved / approved gates | **0** (unchanged) |
| Implementation Authorization | **NO-GO** (unchanged) |
| Real plugin runtime | **NO-GO** (unchanged) |
| Production rollout | **NO-GO** (unchanged) |
| New route | **NO-GO** (unchanged) |
| Phase 3I | **NOT AUTHORIZED** unless separately requested |

## A. Scope

This matrix records the P0 evidence state **after** the Phase 3E–3H Missing
Implementation Recovery task, the follow-on P0 Evidence Consolidation &
Hardening pass, **and** the Remaining P0 Gate Reduction pass (§H). It references
**code and test evidence only**. It does **not**:

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
- `hermes_cli/dev_web_p0_evidence.py` — fail-closed P0 gate evidence
  aggregator: the frozen 24-gate registry, a conservative status taxonomy, the
  `evaluate_p0_evidence` summary (resolved_count always 0), unforgeable
  `HumanApprovalRecord`, authorization-bypass prevention, and the
  provenance / route-exception / rollback / evidence-quality evaluators. Not
  imported by the FastAPI app.

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
- `tests/test_dev_web_phase_3e_h_remaining_p0_reduction.py` (85 tests) — the
  remaining-P0 reduction pass: 24-gate aggregator counts, authorization-bypass
  attempts, unforgeable human approval, supply-chain provenance, route
  exception gap, rollback/incident gap, evidence reproducibility, source
  boundary, dev-web API isolation, route counts.

## D. P0 Evidence Matrix

Statuses: `PARTIAL EVIDENCE` (code/test exists but no approval), `GOVERNANCE
ONLY` (no code evidence; policy/not-granted), `BLOCKED BY HUMAN REVIEW` (can
only advance via an explicit human/project-owner action), `UNRESOLVED` (open).
Nothing is `RESOLVED`.

| P0 ID | Gate theme | Status | Code evidence | Test evidence | Remaining gap | Verdict |
|-------|-----------|--------|---------------|---------------|---------------|---------|
| P0-01 | Sandbox model | PARTIAL EVIDENCE | `dev_web_sandbox_proof.py` skeleton (fail-closed, default-deny) | sandbox-proof skeleton suite | skeleton ≠ an approved sandbox model; no runtime | NOT RESOLVED |
| P0-02 | Process isolation | PARTIAL EVIDENCE | `process.spawn` denied; no subprocess in sandbox modules | capability + source-boundary tests | no approved process-isolation model | NOT RESOLVED |
| P0-03 | Filesystem boundary | PARTIAL EVIDENCE | `evaluate_path_safety`, `evaluate_filesystem_path`, traversal/symlink/case/runtime-store denial | filesystem guard + hardening suites | not an approved boundary model; production never opened | NOT RESOLVED |
| P0-04 | Network boundary | PARTIAL EVIDENCE | `evaluate_network_target` (always denies); no socket/requests/httpx | network guard + hardening suites | intent-level deny only; no approved network policy | NOT RESOLVED |
| P0-05 | Supply-chain policy | PARTIAL EVIDENCE | `classify_plugin_source` provenance classifier (deny-by-default; descriptor-only readable as metadata) | remaining-p0-reduction suite | provenance classifier denies untrusted sources; no approved supply-chain policy | NOT RESOLVED |
| P0-06 | Permission model | PARTIAL EVIDENCE | `CAPABILITY_LABELS`, `evaluate_capability` (default-deny, labels only) | capability deny + hardening suites | labels grant nothing at runtime; no real permission model | NOT RESOLVED |
| P0-07 | Audit / redaction model | PARTIAL EVIDENCE | `dev_web_sandbox_audit.py` (in-memory, redacted), redaction utilities | audit + redaction + hardening suites | in-memory only; no durable audit approved | NOT RESOLVED |
| P0-08 | Kill switch | PARTIAL EVIDENCE | `evaluate_kill_switch` (fail-closed; invalid-state fail-closed; no process signal) | kill-switch + hardening suites | dev-only flag; not a production kill switch | NOT RESOLVED |
| P0-09 | Production isolation | PARTIAL EVIDENCE | `classify_hermes_home`, `is_production_home/state_db` (string-only) | production-isolation suite | not an approved isolation boundary; no runtime | NOT RESOLVED |
| P0-10 | Secret handling ambiguity | PARTIAL EVIDENCE | redaction patterns (sk-/ghp_/xox/Bearer/PEM/env-line); `evaluate_secret_request` always denies | redaction + hardening suites | defense-in-depth only; no approved secret model; no real secret read | NOT RESOLVED |
| P0-11 | Filesystem / network ambiguity | PARTIAL EVIDENCE | pure deterministic evaluators; unambiguous deny | edge-case suites | not approved by reviewers | NOT RESOLVED |
| P0-12 | Unapproved execution path | PARTIAL EVIDENCE (not introduced) | descriptor-only enforcement; no plugin execution/loader/import path exists | source-boundary tests | proven absent; remains "not introduced" | NOT RESOLVED |
| P0-13 | Production impact | PARTIAL EVIDENCE (not introduced) | `~/.hermes` referenced only as a denial target; no production access | production-isolation + no-artifacts suites | none introduced | NOT RESOLVED |
| P0-14 | Route governance | PARTIAL EVIDENCE | `route_governance_counts`, `assert_route_governance_unchanged` (`34/34/5/0/1/1`) | route-governance + hardening suites | baseline frozen unchanged; no exception approval granted | NOT RESOLVED |
| P0-15 | No implementation authorization | BLOCKED BY HUMAN REVIEW | `evaluate_p0_evidence` / `evaluate_authorization_request` (authorization cannot be automated; metadata ignored) | remaining-p0-reduction bypass suite | requires project-owner authorization; cannot be granted by code or metadata | NOT RESOLVED |
| P0-16 | No runtime endpoint authorization | BLOCKED BY HUMAN REVIEW | route exception evaluator (`route_exception_approved` always False); no endpoint wired | remaining-p0-reduction route suite | no runtime endpoint wired; endpoint authorization requires route-governance reviewer | NOT RESOLVED |
| P0-17 | No runtime artifact storage authorization | PARTIAL EVIDENCE | `dev_web_sandbox_audit.py` (in-memory only; no durable store) | no-persistent-artifacts + hardening suites | no persistent artifact store exists; approved storage model still required | NOT RESOLVED |
| P0-18 | No plugin source trust decision | BLOCKED BY HUMAN REVIEW | `classify_plugin_source` deny-by-default (no source trusted for execution) | remaining-p0-reduction provenance suite | deny-by-default provenance; an explicit trust decision requires security reviewer | NOT RESOLVED |
| P0-19 | No worker lifecycle approval | BLOCKED BY HUMAN REVIEW | `process.spawn` denied; no worker lifecycle code | capability + source-boundary suites | no worker lifecycle code; approval requires security reviewer | NOT RESOLVED |
| P0-20 | No failure-mode approval | PARTIAL EVIDENCE | fail-closed defaults (kill-switch, redaction, decision coercion, invalid-state) | failure-mode + hardening suites | not an approved failure-mode plan | NOT RESOLVED |
| P0-21 | No rollback plan | PARTIAL EVIDENCE | `evaluate_rollback_readiness` (temp/fake cleanup targets only; production path denied) | remaining-p0-reduction rollback suite | rollback readiness evaluator added; approved plan still required | NOT RESOLVED |
| P0-22 | No human review signoff | BLOCKED BY HUMAN REVIEW | `HumanApprovalRecord` cannot be faked (no trust token in dev skeleton) | remaining-p0-reduction unforgeable-approval suite | signoff not started; cannot be synthesized from metadata | NOT RESOLVED |
| P0-23 | No incident response plan | PARTIAL EVIDENCE | incident owner + redaction helper (`evaluate_rollback_readiness`); fake owner rejected | remaining-p0-reduction rollback suite | incident owner/redaction helper added; approved plan still required | NOT RESOLVED |
| P0-24 | No test strategy approval | PARTIAL EVIDENCE | 144 prior tests + hardening suite | all targeted suites pass | not an approved strategy by reviewers | NOT RESOLVED |

## E. Evidence-to-test mapping

- `test_dev_web_phase_3e_h_safety_baseline.py` → P0-03, P0-09, P0-13, P0-14.
- `test_dev_web_phase_3h_sandbox_proof_skeleton.py` → P0-01, P0-03, P0-04,
  P0-06, P0-07, P0-08, P0-10, P0-11, P0-12, P0-20, P0-24.
- `test_dev_web_phase_3e_h_p0_evidence_hardening.py` → P0-01, P0-03, P0-04,
  P0-06, P0-07, P0-08, P0-10, P0-11, P0-12, P0-14, P0-17, P0-20, P0-24
  (and re-asserts every NO-GO).
- `test_dev_web_phase_3e_h_remaining_p0_reduction.py` → P0-05, P0-15, P0-16,
  P0-17, P0-18, P0-19, P0-21, P0-22, P0-23, P0-24 (and re-asserts every
  NO-GO + resolved_count == 0).

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

## H. Remaining P0 Gate Reduction (this update)

### H.1 Update summary

The Remaining P0 Gate Reduction pass targeted the 9 gates that were previously
`GOVERNANCE ONLY / UNRESOLVED`. It added a fail-closed evidence aggregator
(`hermes_cli/dev_web_p0_evidence.py`) plus an 85-test suite
(`tests/test_dev_web_phase_3e_h_remaining_p0_reduction.py`), and reclassified
the 9 gates more precisely — **without resolving any of them**:

- 4 gates advanced from governance-only to `PARTIAL EVIDENCE` because this
  codebase now supplies real dev-only code evidence for them
  (P0-05, P0-17, P0-21, P0-23).
- 5 gates are now `BLOCKED BY HUMAN REVIEW` — they can only advance via an
  explicit human / project-owner action, and the aggregator proves code and
  request metadata cannot move them (P0-15, P0-16, P0-18, P0-19, P0-22).

### H.2 Remaining 9 gate detail

| P0 ID | Theme | Previous status | New code evidence | New test evidence | Remaining gap | Verdict |
|-------|-------|------------------|-------------------|-------------------|---------------|---------|
| P0-05 | Supply-chain policy | GOVERNANCE ONLY | `classify_plugin_source` provenance classifier (deny-by-default; descriptor-only/local-static readable as metadata) | remaining-p0-reduction provenance suite | no approved supply-chain policy; classifier is dev-only | NOT RESOLVED |
| P0-15 | No implementation authorization | GOVERNANCE ONLY | `evaluate_authorization_request` ignores metadata; impl auth frozen NO-GO | bypass-attempt suite | requires project-owner authorization | NOT RESOLVED |
| P0-16 | No runtime endpoint authorization | GOVERNANCE ONLY | `evaluate_route_exception` (`route_exception_approved` always False) | route-exception suite | endpoint authorization requires route-governance reviewer | NOT RESOLVED |
| P0-17 | No runtime artifact storage authorization | GOVERNANCE ONLY | in-memory audit only (no durable store) — now formally mapped | no-persistent-artifacts suite | approved storage model still required | NOT RESOLVED |
| P0-18 | No plugin source trust decision | GOVERNANCE ONLY | `classify_plugin_source` deny-by-default; no source trusted for execution | provenance suite | explicit trust decision requires security reviewer | NOT RESOLVED |
| P0-19 | No worker lifecycle approval | GOVERNANCE ONLY | `process.spawn` denied; no worker lifecycle code | capability suite | approval requires security reviewer | NOT RESOLVED |
| P0-21 | No rollback plan | GOVERNANCE ONLY | `evaluate_rollback_readiness` (temp/fake targets; production path denied) | rollback suite | approved rollback plan still required | NOT RESOLVED |
| P0-22 | No human review signoff | GOVERNANCE ONLY | `HumanApprovalRecord` unforgeable (no trust token in dev skeleton) | unforgeable-approval suite | signoff not started; cannot be synthesized from metadata | NOT RESOLVED |
| P0-23 | No incident response plan | GOVERNANCE ONLY | incident owner + redaction helper; fake owner rejected | rollback/incident suite | approved incident-response plan still required | NOT RESOLVED |

### H.3 Updated summary

- total P0 gates: **24**
- fully resolved / approved: **0**
- partially evidenced: **19** (15 prior + P0-05, P0-17, P0-21, P0-23)
- candidate for review: **0** (taxonomy supported; none assigned, to avoid any
  implication of readiness)
- blocked by human review: **5** (P0-15, P0-16, P0-18, P0-19, P0-22)
- governance-only / no-evidence: **0**
- Implementation Authorization: **NO-GO**
- Phase 3I: **NOT AUTHORIZED**
- Real runtime: **NO-GO**
- New route: **NO-GO**
- Production rollout: **NO-GO**

### H.4 Why no gate is marked resolved

`resolved_count` is **0** and stays 0 because:

- **No human approval was performed.** A gate can only become `RESOLVED` via a
  valid `HumanApprovalRecord`, and the dev skeleton holds no out-of-band trust
  token (`_REAL_TRUST_TOKEN is None`), so no valid approval can be created —
  not from request metadata, and not by constructing the record directly.
- **No implementation authorization was performed.** `evaluate_authorization_request`
  ignores every bypass-shaped metadata key and returns the frozen NO-GO verdict.
- **No real runtime proof was performed.** The aggregator never executes a
  plugin, never loads a plugin, never dynamic-imports; provenance denies every
  executable source.
- **No production proof was performed.** `~/.hermes` and production `state.db`
  are referenced only as denial-target strings; rollback cleanup targets are
  temp/fake only.
- **No route-governance exception approval was performed.** `route_exception_approved`
  is always False; route counts stay `34/34/5/0/1/1`.

Therefore `resolved_count` remains 0 unless project policy explicitly
provisions a real trust token and a human signs off — both of which are out of
scope for this task and explicitly not authorized here.
