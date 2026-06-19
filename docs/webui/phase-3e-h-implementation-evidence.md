# Phase 3E–3H Missing-Implementation Recovery — Implementation Evidence

| Field | Value |
|-------|-------|
| Title | Phase 3E–3H Missing Implementation Recovery — Code Evidence |
| Kind | **Code evidence, not governance.** This is not a closeout, signoff, archive, review-board decision, or go/no-go ledger. |
| Branch | `dev-huangruibang` |
| Inherited P0 gate set | `PHASE-3F-P0-GATES-001` (24 gates) |
| Implementation Authorization | **NO-GO** (unchanged) |
| Real plugin runtime | **NO-GO** (unchanged) |
| Production rollout | **NO-GO** (unchanged) |
| New route | **NO-GO** (unchanged) |
| Phase 3I | **NOT AUTHORIZED** unless separately requested |

> This document records **code + test evidence** produced by the Phase 3E–3H
> missing-implementation recovery task. It does **not** close, sign off,
> archive, or authorize anything. It maps the implemented safety baseline and
> the dev-only sandbox proof skeleton to *partial* evidence against the
> inherited P0 gates. No P0 gate is resolved or approved here — gate approval
> requires human reviewers / project-owner authorization that this task is
> explicitly forbidden to perform.

## 1. What landed as code (primary product)

The primary product of this task is **code and tests**, not docs. Five new
dev-only, stdlib-only, side-effect-free modules, plus two test files.

### 1.1 Safety baseline (Phase 3F/3G requirements → code)

`hermes_cli/dev_web_safety_baseline.py`

- **Route governance** — `route_governance_counts(app)` counts the frozen
  `34/34/5/0/1/1` baseline directly off a FastAPI app (mirrors
  `handle_route_governance_read`); `assert_route_governance_unchanged`,
  `route_governance_new_route_flags()` (all zero).
- **Production isolation** — `classify_hermes_home`, `is_production_home`,
  `is_production_state_db`, `assert_dev_environment`. Pure string analysis;
  `~/.hermes` and production `state.db` are referenced only as denial targets
  and never opened.
- **Forbidden-path protection** — `evaluate_path_safety`,
  `evaluate_runtime_store_write`: deny `~/.hermes`, production db, traversal
  escape, symlink escape (against resolvable temp roots only), home fallback,
  unknown write location, runtime-store names.
- **Runtime-store protection** — `find_runtime_store_artifacts` (scan helper),
  `FORBIDDEN_RUNTIME_STORE_NAMES`.
- **`.claude` exclusion** — `check_dotclaude_not_staged`: read-only
  `git status` / `git diff --cached` / `git ls-files` (never `add` / `commit` /
  `reset` / `clean`).
- **No-side-effect surface** — frozen flags + `assert_no_side_effect_surface`.

### 1.2 Dev-only sandbox proof skeleton (Phase 3H requirements → code)

A **skeleton**, not a runtime. Never executes a plugin, never loads a plugin,
never dynamic-imports, never networks, never reads a real secret, never
introduces a route, never touches production. Not imported by `dev_web_api.py`.

- `hermes_cli/dev_web_sandbox_guards.py` — filesystem boundary guard,
  network deny guard, secrets-unavailable/redaction guard
  (`evaluate_filesystem_path`, `evaluate_network_target`,
  `evaluate_secret_request`, `redact_sandbox_text/payload`, `contains_secret`).
- `hermes_cli/dev_web_sandbox_policy.py` — capability default-deny evaluator
  (14 labels; 3 proof-label-only allowed), kill-switch policy (fail-closed),
  descriptor-only enforcement (`evaluate_capability`, `evaluate_kill_switch`,
  `evaluate_descriptor`; reuses the Phase 3D recursive forbidden-field scanner).
- `hermes_cli/dev_web_sandbox_audit.py` — in-memory redacted audit record
  builder (`build_sandbox_audit_record`, `is_audit_record_safe`). Never writes
  JSONL/DB/file; final defensive re-redaction; fail-closed on redaction failure.
- `hermes_cli/dev_web_sandbox_proof.py` — `SandboxProofRequest` /
  `SandboxProofResult` / `evaluate_sandbox_proof` orchestrator. Evidence flags
  frozen `False` (no route change / production access / external network / real
  secret / runtime execution). References the Phase 3D descriptor registry
  read-only for descriptor-only enforcement.

## 2. Tests added

- `tests/test_dev_web_phase_3e_h_safety_baseline.py` — route governance
  unchanged (`34/34/5/0/1/1`), new-route flags zero, production isolation,
  forbidden-path denial (traversal / symlink / `~/.hermes` / state.db / home
  fallback / write-outside-root / runtime-store), `.claude` not staged/tracked,
  runtime-store scan, source-level boundary (no dynamic loading / network;
  subprocess confined to read-only git).
- `tests/test_dev_web_phase_3h_sandbox_proof_skeleton.py` — descriptor-only
  enforcement (every forbidden field denied), capability default-deny (unknown
  + all 10 dangerous labels), filesystem/network/secret guards, kill-switch
  fail-closed, in-memory redacted audit (no raw secret / production path),
  failure modes (malformed / oversized / redaction-failure), no persistent
  artifacts, source boundary (no dynamic loading / network), proof module not
  imported by the API (no new route).

Combined: **144 tests pass.**

## 3. P0 gate evidence summary

Inherited: **24 P0 gates** (`PHASE-3F-P0-GATES-001`). Gate approval requires
human reviewers / project-owner authorization. This task produces **partial
code evidence** only — it does **not** resolve or approve any gate. Count:
**0 fully resolved**, **0 approved**.

### 3.1 Gates with partial code evidence (behavior demonstrated by tests)

| Gate | Name | Partial evidence | Supporting tests |
|------|------|------------------|------------------|
| PHASE3F-P0-01 | Sandbox model | dev-only sandbox proof skeleton implemented (not a runtime) | sandbox proof suite |
| PHASE3F-P0-02 | Process isolation | no plugin execution / dynamic loading / subprocess code exec (read-only git only) | source-boundary tests |
| PHASE3F-P0-03 | Filesystem boundary | filesystem boundary guard (traversal / symlink / prod / write) | `TestFilesystemGuard` |
| PHASE3F-P0-04 | Network boundary | network deny guard (every external intent) | `TestNetworkGuard` |
| PHASE3F-P0-06 | Permission model | capability default-deny evaluator (14 labels) | `TestCapabilityDeny` |
| PHASE3F-P0-07 | Audit / redaction model | in-memory redacted audit + redaction utility | `TestAuditRecord`, `TestSecretGuard` |
| PHASE3F-P0-08 | Kill switch | kill-switch policy, fail-closed when active | `TestKillSwitch` |
| PHASE3F-P0-09 | Production isolation | production-home/db detection by string analysis; never opened | `TestProductionIsolation` |
| PHASE3F-P0-10 | Secret handling ambiguity | secrets default-deny + redaction (no ambiguity) | `TestSecretGuard` |
| PHASE3F-P0-11 | Filesystem / network ambiguity | default-deny guards, no ambiguity | `TestFilesystemGuard`, `TestNetworkGuard` |
| PHASE3F-P0-12 | Unapproved execution path | descriptor-only; no execution path | `TestDescriptorOnly` |
| PHASE3F-P0-13 | Production impact | no production access / state.db / signal (source-checked) | `TestNoSideEffectSurface`, `TestProductionIsolation` |
| PHASE3F-P0-14 | Route governance | `34/34/5/0/1/1` unchanged; no new route | `TestRouteGovernance` |
| PHASE3F-P0-20 | No failure-mode approval | failure-mode tests added (approval not granted) | orchestrator + audit failure-mode tests |
| PHASE3F-P0-24 | No test strategy approval | tests added (approval not granted) | both test files |

### 3.2 Gates still unresolved (require governance, not code)

These are approval / authorization / signoff gates. They cannot be advanced by
code and remain **unresolved / NO-GO**:

- PHASE3F-P0-05 Supply-chain policy (security reviewer approval)
- PHASE3F-P0-15 No implementation authorization (project owner) — **NO-GO**
- PHASE3F-P0-16 No runtime endpoint authorization (route-governance reviewer)
- PHASE3F-P0-17 No runtime artifact storage authorization (audit reviewer)
- PHASE3F-P0-18 No plugin source trust decision (security reviewer)
- PHASE3F-P0-19 No worker lifecycle approval (security reviewer)
- PHASE3F-P0-21 No rollback plan (production safety reviewer)
- PHASE3F-P0-22 No human review signoff (project owner)
- PHASE3F-P0-23 No incident response plan (production safety reviewer)

## 4. Route governance (exact counts)

| Figure | Count |
|--------|-------|
| OpenAPI paths | 34 |
| Runtime routes | 34 |
| Tool GET | 5 |
| Tool write HTTP route | 0 |
| Tool dry-run route | 1 |
| Tool execution route | 1 |
| New HTTP route | 0 |
| New Tool write route | 0 |
| New Provider route | 0 |
| New plugin route | 0 |
| New runtime route | 0 |

Verified by `TestRouteGovernance` against a live `TestClient` app and by
`assert_route_governance_unchanged`.

## 5. Boundary (verified by tests + source checks)

- No `importlib` loader / `__import__(` / dynamic loading.
- No subprocess code execution (the single `subprocess.run` is the read-only
  `.claude` git helper; audited).
- No shell execution.
- No `requests` / `httpx` / `aiohttp` / socket / DNS / live network.
- No real API key / `Authorization` / `Bearer` / `sk-` / `ghp_` / `xox` / PEM
  read; secrets are denied and redacted.
- No `~/.hermes` access; no production `state.db` access.
- No plugin loader / plugin execution path.
- No marketplace / remote registry / external plugin fetch.
- No provider-generated / LLM-generated plugin install.
- No new route definition; no OpenAPI path added.
- `.claude` not staged / not committed.

## 6. Production safety (unchanged by this task)

- Production Gateway PID 28428 — untouched (not stopped / restarted /
  replaced / signaled).
- Production Gateway count — 1 before and after.
- Dev Gateway — stopped; Dashboard — not started; ports 5180/5181 — free.
- No `~/.hermes` access; no production `state.db` access.

## 7. Next step

Continue converging the P0 gates from the **partial-evidence** side: extend
the sandbox proof tests, then seek the human reviewer / project-owner
authorization that gates PHASE3F-P0-15 (implementation authorization) and the
approval gates (P0-05, P0-18–P0-23) actually require. Until those are granted,
**Implementation Authorization, real plugin runtime, production rollout, and
any new route remain NO-GO.**
