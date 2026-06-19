# Phase 3H Dev-only Proof Runner Harness — Evidence

| Field | Value |
|-------|-------|
| Title | Phase 3H Dev-only Sandbox Proof Runner Harness — Evidence |
| Kind | **Evidence note, not governance.** Not a closeout, signoff, archive, review-board decision, go/no-go ledger, or authorization. |
| Branch | `dev-huangruibang` |
| Inherited P0 gate set | `PHASE-3F-P0-GATES-001` (24 gates) |
| Resolved / approved gates | **0** (unchanged) |
| Implementation Authorization | **NO-GO** (unchanged) |
| Phase 3I | **NOT AUTHORIZED** (unchanged) |
| Real plugin runtime | **NO-GO** (unchanged) |
| Production rollout | **NO-GO** (unchanged) |
| New route | **NO-GO** (unchanged) |

## A. What this adds

A small, dev-only **proof runner harness** that promotes the Phase 3H
single-evaluation sandbox proof skeleton into a reproducible runner over a
**fixed, in-memory, test-only** set of proof scenarios. New modules:

- `hermes_cli/dev_web_sandbox_runner.py` — `ProofScenario` / `ProofScenarioResult`
  / `ProofRunSummary` models, `run_proof_scenario()`, `run_proof_scenarios()`.
- `hermes_cli/dev_web_sandbox_scenarios.py` — the fixed 10-scenario library.
- `tests/test_dev_web_phase_3h_proof_runner_harness.py` — 84 tests.

The runner only **calls existing** policy / guard / audit / evidence logic
(`evaluate_sandbox_proof`, `classify_evidence_quality`,
`evaluate_authorization_request`, `evaluate_route_exception`,
`evaluate_p0_evidence`). It adds no new evaluation surface.

## B. What the proof runner is NOT

- It does **not** execute a plugin, **not** load a plugin, **not** dynamic-import.
- It does **not** access the network, **not** read a real secret / env / `.env`
  / API key.
- It does **not** access `~/.hermes`, **not** access production `state.db`, **not**
  open/stat any real filesystem path (every path is a fake / temp / string-policy
  target).
- It does **not** add a route, **not** write a runtime store, **not** write an
  audit JSONL, **not** write a DB, **not** mutate production state.
- It is **not** imported by `dev_web_api.py` and registers **no** HTTP route.
- It produces **in-memory, redacted** results only.

## C. What a scenario pass means (and does not)

A scenario **pass is dev-only evidence only**. It:

- is **not** a P0 resolution (`resolved_count` stays **0**);
- is **not** Implementation Authorization GO (stays **NO-GO**);
- is **not** Phase 3I authorization (stays **NOT AUTHORIZED**);
- is **not** real-runtime authorization (stays **NO-GO**);
- is **not** a new-route or production-rollout authorization (both stay **NO-GO**).

Every result's evidence flags are frozen `False`: no route change, no production
access, no external network, no real secret, no runtime execution, and no
persistent artifact. Fake human-approval / authorization metadata smuggled into
a scenario is detected and ignored.

## D. Fixed scenario summary

| scenario_id | expected decision | linked P0 gates |
|-------------|-------------------|-----------------|
| descriptor_only_safe_read | allowed | P0-12 |
| executable_descriptor_denied | denied | P0-12, P0-18 |
| network_request_denied | denied | P0-04 |
| secret_request_redacted_and_denied | denied | P0-10 |
| filesystem_forbidden_paths_denied | denied | P0-03, P0-09 |
| kill_switch_active_fail_closed | denied | P0-08 |
| route_change_attempt_denied | denied | P0-14, P0-16 |
| production_access_attempt_denied | denied | P0-09, P0-13 |
| p0_human_review_required | allowed (authorization stays NO-GO) | P0-15, P0-22 |
| evidence_candidate_but_not_resolved | allowed (candidate, not resolved) | P0-24 |

All 10 baseline scenarios pass; `resolved_count` remains **0** and every authorization
flag remains **NO-GO / NOT AUTHORIZED**.

## D-bis. Adversarial scenario hardening (added)

A second pass hardened the runner against bypass-shaped inputs. 12 **fixed,
in-memory** adversarial scenarios were added to `dev_web_sandbox_scenarios.py`
(no external load, no executable content):

| scenario_id | expected decision | linked P0 gates |
|-------------|-------------------|-----------------|
| adversarial_metadata_smuggling_denied | allowed (auth stays NO-GO) | P0-15, P0-22 |
| adversarial_nested_descriptor_execution_denied | denied | P0-12, P0-18 |
| adversarial_secret_laundering_redacted | denied (redacted) | P0-10 |
| adversarial_path_smuggling_denied | denied (redacted) | P0-03, P0-09 |
| adversarial_route_exception_smuggling_denied | denied | P0-14, P0-16 |
| adversarial_fake_human_approval_denied | allowed (auth stays NO-GO) | P0-15, P0-22 |
| adversarial_summary_tampering_resisted | allowed (auth stays NO-GO) | P0-15, P0-22 |
| adversarial_capability_alias_denied | denied | P0-06, P0-12 |
| adversarial_network_url_laundering_denied | denied | P0-04 |
| adversarial_kill_switch_override_denied | denied | P0-08 |
| adversarial_descriptor_id_smuggling_denied | denied | P0-12 |
| adversarial_capability_oversized_denied | denied | P0-06 |

A scenario **pass is still not a P0 resolution**, still not Implementation
Authorization GO, still not Phase 3I authorization, still not real-runtime
authorization. `resolved_count` stays **0** regardless.

### Bypasses found and fixed (adversarial self-review)

Three audit / boundary-correctness gaps were found by direct probing and fixed
(none enabled real execution — the runner has no loader / runtime; they were
descriptor-only / redaction correctness gaps):

1. **Nested descriptor injection** — execution-surface keys that tokenized to a
   non-stem compound (`importlib`, `plugin.load`, dotted `os`/`system`,
   `container`, `webhook`, `callback`, `registry`, `marketplace`,
   `providerGenerated`, `llmGenerated`) slipped past descriptor-only
   enforcement. Fixed in `dev_web_sandbox_policy.py` by extending the exec-stem
   set and adding a normalized-compound dangerous-key scan; recursive nesting
   and list-of-dict smuggling are now denied.
2. **Secret-shaped key leak** — a dict key that itself embedded a secret token
   (`sk-…`, `Bearer …`, `KEY=value`) was not redacted by `redact_sandbox_payload`
   and not caught by `contains_secret`. Fixed in `dev_web_sandbox_guards.py`:
   keys are now scanned like values and masked wholesale.
3. **Runtime-store path leak** — runtime-store-shaped paths
   (`plugin_runtime.jsonl`, `*-store.json`, `runtime-store` / `plugin-store`
   dirs, traversal `..`) were not masked in scenario audit projections. Fixed in
   `dev_web_sandbox_guards.py` (`RUNTIME_STORE_PATH_MARKERS` /
   `path_mentions_runtime_store`) and `dev_web_sandbox_runner.py`
   (`_redact_filesystem_path`); case-insensitive `.HERMES` / `state.db` masking
   and traversal masking were also added.

Additional hardening (defense-in-depth, no bypass required):

- `_UNTRUSTED_METADATA_KEYS` widened to cover `signed_by` / `trust_token` /
  `approval_token` / `real_trust_token` / `p0_resolved` / `resolved_ids` /
  `project_owner` / `review_board_decision` / `approved_by_ai` / route-change /
  runtime / production variants, so the ignored-key diagnostic is complete
  (authorization was already a frozen constant regardless).
- `ProofScenarioResult.redacted_audit` and `ProofRunSummary.redacted_audit_records`
  are now stored as read-only `MappingProxyType` views, so in-place tampering of
  a returned record raises and cannot pollute a later safe projection.

### Hardening tests added

`tests/test_dev_web_phase_3h_proof_runner_adversarial_hardening.py` — 183 tests
covering the adversarial scenario library, metadata smuggling, nested
descriptor injection, secret laundering, path smuggling, route-exception bypass,
fake human approval, summary tampering, capability aliases, network URL
laundering, kill-switch override, descriptor-id smuggling, source-boundary /
dev_web_api isolation, route-count invariants, no-production-access,
no-`~/.hermes`-access, and no-runtime-artifact invariants.

## E. Route governance (unchanged)

`34/34/5/0/1/1` — openapi paths / runtime routes / tool GET / tool write HTTP /
tool dry-run / tool execution. New HTTP route = 0, new tool-write route = 0,
new provider route = 0, new plugin route = 0, new runtime route = 0.

## F. Status

Implementation Authorization **NO-GO**; Phase 3I **NOT AUTHORIZED**; real plugin
runtime **NO-GO**; new route **NO-GO**; production rollout **NO-GO**. This note
starts no docs-only governance loop and authorizes nothing.
