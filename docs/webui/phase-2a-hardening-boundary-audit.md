# Phase 2A-H1 — Hardening: Boundary Audit

## Document Information

| Field | Value |
|-------|-------|
| Phase | 2A-H1 |
| Title | Boundary Audit (deterministic) |
| Status | Completed |
| Date | 2026-06-14 |
| Boundary Audit ID | `BOUNDARY-AUDIT-2A-H1-001` |
| Hardening ID | `HARDENING-2A-H1-001` |
| Input HEAD | `0527d6c892b24afde03ff9259a612b2f59ee8018` |
| Scope | Re-verify every Phase 2A boundary as a deterministic, agent-independent record. |

---

## 1. Allowlist Boundary

| Check | Expected | Observed | Verdict |
|-------|----------|----------|---------|
| `STATIC_ALLOWLIST` membership | exactly 6 tools | `{clarify, tool_policy_read, route_governance_read, audit_events_read, dev_environment_read, release_status_read}` | PASS |
| `STATIC_ALLOWLIST` size | 6 | 6 | PASS |
| `PHASE_2A_READ_ONLY_TOOL_IDS` | exactly 5 (excludes clarify) | 5 | PASS |
| Registry ⊆ STATIC_ALLOWLIST | yes | yes | PASS |
| STATIC ⊆ CANDIDATE | yes | yes | PASS |
| STATIC ∩ DENYLIST | ∅ | ∅ | PASS |
| Per-tool safety profile | all read-only / no-provider / no-write / no-side-effects / requires-confirmation | all hold | PASS |
| Single source of truth | `STATIC_ALLOWLIST` defined once in `dev_web_tool_policy.py`, re-exported by the registry | confirmed | PASS |

Enforcement: `dev_web_tool_policy.py` import-time validator pins
`STATIC_ALLOWLIST == expected 6-set`; the registry's
`_verify_registry_consistency()` runs at import and raises on any drift.

---

## 2. Route Governance Boundary

| Metric | Expected | Observed | Verdict |
|--------|----------|----------|---------|
| OpenAPI paths | 34 | 34 | PASS |
| Runtime routes | 34 | 34 | PASS |
| OpenAPI == runtime | equal | equal | PASS |
| Tool GET routes | 5 | 5 | PASS |
| Tool write routes | 0 | 0 | PASS |
| Tool dry-run routes | 1 | 1 | PASS |
| Tool execution routes | 1 | 1 | PASS |
| Second execution route | none | none | PASS |
| Provider route | none | none | PASS |

Phase 2A added **zero** HTTP routes. The allowlist expansion is membership-only;
the single `/tools/dry-run` and `/tools/execute` routes serve all six tools.

---

## 3. Provider Boundary

| Check | Expected | Observed | Verdict |
|-------|----------|----------|---------|
| `providerSchemaSent` | always False | hardcoded `False` in handler-call + post-execution-audit + read-only handlers | PASS |
| `providerApiCalled` | always False | hardcoded `False` in the same modules; top-level result flag False for every tool | PASS |
| `provider_required` per tool | False for all 5 | False for all 5 | PASS |
| Provider Schema actual send | never | never | PASS |
| Provider API actual call | never | never | PASS |

No Provider completion state exists anywhere on the controlled path. Provider
integration remains deferred to Phase 2B.

---

## 4. Write Boundary

| Check | Expected | Observed | Verdict |
|-------|----------|----------|---------|
| Tool write routes | 0 | 0 | PASS |
| `write_required` per tool | False for all 5 | False for all 5 | PASS |
| `filesystemChanged` (execution) | always False | always False | PASS |
| Write-like tools (`write_file`, `patch`, `memory`, `skill_manage`) | blocked / not in allowlist | blocked | PASS |
| Shell tools (`terminal`, `process`, `execute_code`) | blocked | blocked | PASS |

No write capability exists on the Phase 2A surface. Tool write is deferred to
Phase 2C.

---

## 5. Audit Redaction Boundary

| Check | Expected | Observed | Verdict |
|-------|----------|----------|---------|
| Raw token in result / audit | never | never | PASS |
| Full tokenHash | never | never | PASS |
| Raw arguments | never | never | PASS |
| Secret patterns (`Bearer `, `sk-`, `BEGIN PRIVATE KEY`) | never | never | PASS |
| Callable / function repr (`<function`, `<bound method`, `object at 0x`) | never | never | PASS |
| Per-tool `toolId` audit filter | isolates one tool | isolates one tool | PASS |

Three independent redaction layers (dry-run, digest, handler-call) plus the
post-execution audit `_sanitize_event` keep every artifact clean. Verified for
all five tools across result envelopes and all three audit JSONL stores.

---

## 6. Production Isolation Boundary

| Check | Expected | Observed | Verdict |
|-------|----------|----------|---------|
| Production Gateway expected PID | 1962 | 1962 (constant) | PASS |
| Production Gateway observed PID | 1962 | 1962 | PASS |
| Production Gateway process count | 1 | 1 | PASS |
| Gateway stop / restart / replace / signal | never | never | PASS |
| `~/.hermes` access | never | never | PASS |
| Production `state.db` access | never | never | PASS |
| Gateway signaling APIs (`os.kill`, `signal`, `.terminate`, `os.system`, `Popen`) in controlled-path source | absent | absent | PASS |
| Dev services bind | 127.0.0.1 only | 127.0.0.1 only | PASS |
| Ports 5180 / 5181 final | free | free | PASS |

The only subprocess use is bounded, `shutil.which`-guarded, read-only `pgrep`
(production gateway PID/count observation) and `lsof` (port observation), each
with a 5s timeout and errors swallowed to safe defaults. The `prod_path`
reference in `dev_environment_read` is a pure path **equality comparison** — it
never opens, reads, or writes the directory.

---

## 7. Frontend Contract Boundary

| Check | Expected | Observed | Verdict |
|-------|----------|----------|---------|
| Frontend `SELECTABLE_TOOLS` ids | mirror backend `STATIC_ALLOWLIST` (6 tools) | match exactly | PASS |
| Default tool | `clarify` | `clarify` | PASS |
| Read-only safety badges | render per tool | render | PASS |
| Per-tool argument forms | match registry argument specs | match | PASS |
| `executionCompleted === true` completion signal | generic per tool | generic per tool | PASS |
| Audit `toolId` filter dropdown | present | present | PASS |
| Frontend type-check | PASS | PASS | PASS |
| Frontend lint | PASS | PASS | PASS |
| Frontend unit tests | 0 failed | 692 passed / 0 failed | PASS |
| Frontend build | PASS | 1863 modules | PASS |
| Smoke `phase2a` profile | PASS | 7 passed / 0 failed | PASS |
| Smoke `all` profiles | PASS | Overall PASS | PASS |

---

## 8. Boundary Audit Conclusion

All seven boundaries hold on the Phase 2A baseline. The Phase 2A read-only
multi-tool execution surface is **read-only, Provider-free, write-free,
production-isolated, fully redacted, route-frozen, and contract-mirrored**.
No boundary regression was introduced by Phase 2A or by this hardening phase.
