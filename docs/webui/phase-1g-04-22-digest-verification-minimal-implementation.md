# Phase 1G-04-22: Digest Verification Minimal Implementation

## Document Information

| Field | Value |
|-------|-------|
| Phase | 1G-04-22 |
| Title | Digest Verification Minimal Implementation / Still Blocked-Only |
| Status | Completed locally / Not pushed |
| Date | 2026-06-13 |
| Dependencies | Phase 1G-04-21 (scope freeze), Phase 1G-04-20 (confirmation token) |
| Branch | dev-huangruibang |
| Base commit | `1e8ba414227cd2085946284ac94598b25831d095` |

---

## 1. Phase Definition

Phase 1G-04-22 implements minimal digest verification while preserving the still-blocked-only execution boundary.

This phase implements:
- Digest package builder
- Canonical JSON serialization
- SHA-256 hex digest computation
- Dry-run decision digest generation during dry-run
- Dry-run decision digest persistence into dry-run audit events
- Dry-run response digest fields (dryRunDecisionDigest, digestAlgorithm, digestPackageVersion, canonicalizationVersion)
- Confirmation token issuance requiring non-null dryRunDecisionDigest
- Confirmation token verification checking digest binding
- Execute route digest verification gates (historical, token-bound, request, execute-derived)
- Valid token + valid digest final block at pre-execution audit boundary
- OpenAPI schema-only updates
- Backend tests
- Documentation

This phase does NOT implement:
- Pre-execution audit
- Post-execution audit
- Handler lookup
- Tool Handler call
- Tool Dispatch
- Tool Execution
- Provider Schema sending
- Provider API call
- Frontend execute flow
- Audit read API
- Audit viewer
- Real Controlled Execution

---

## 2. Baseline

| Metric | Value |
|--------|-------|
| Base commit | `1e8ba414227cd2085946284ac94598b25831d095` |
| OpenAPI paths | 33 |
| Runtime routes | 33 |
| Tool GET routes | 4 |
| Tool write routes | 0 |
| Tool dry-run routes | 1 |
| Tool execution routes | 1 |
| STATIC_ALLOWLIST | `frozenset({"clarify"})` |
| Valid token final block before this phase | `blocked_digest_verification_not_implemented` |
| Digest Verification | Not implemented |
| Pre-execution Audit | Not implemented |
| Real Controlled Execution | Not started |

---

## 3. Implementation Summary

### 3.1 New Module: `dev_web_tool_execute_digest.py`

Pure backend helper module implementing:

- `build_dry_run_decision_digest_package()` — builds canonical 14-field digest package from safe dry-run decision fields
- `canonicalize_digest_package()` — deterministic sorted-key JSON serialization
- `compute_digest()` — SHA-256 hex digest computation with `sha256:` prefix
- `build_arguments_digest()` — stable digest from redacted arguments
- `verify_dry_run_decision_digest()` — multi-source digest verification (historical, token-bound, request, execute-derived)
- `safe_digest_summary()` — safe truncation for logging

Constants:
- `DIGEST_PACKAGE_VERSION = "1"`
- `CANONICALIZATION_VERSION = "json-sort-v1"`
- `DIGEST_ALGORITHM = "sha256"`
- `DIGEST_PREFIX = "sha256:"`

### 3.2 Dry-run Digest Generation

The dry-run API handler (`dev_web_api.py`) now:
1. Computes `dryRunDecisionDigest` after the dry-run policy decision
2. Passes digest fields to `build_dry_run_audit_event()`
3. Persists digest in the audit JSONL event
4. Returns `dryRunDecisionDigest`, `digestAlgorithm`, `digestPackageVersion`, `canonicalizationVersion` in the response

### 3.3 Dry-run Audit Persistence

`build_dry_run_audit_event()` now accepts and stores:
- `dryRunDecisionDigest`
- `digestAlgorithm`
- `digestPackageVersion`
- `canonicalizationVersion`

### 3.4 Preflight Lookup Enhancement

`_build_found_result()` in `dev_web_tool_execute_preflight.py` now extracts `dryRunDecisionDigest` from the audit event record.

### 3.5 Confirmation Token Digest Binding

`issue_confirmation_token()` now binds the non-null `dryRunDecisionDigest` to the token record.

`verify_confirmation_token()` now:
- Fails closed if token-bound digest is None (legacy token)
- Fails closed if token-bound digest mismatches request digest

### 3.6 Execute Route Digest Gates

The execute route (`dev_web_tool_execute.py`) now implements Gates 28–37:

| Gate | Description |
|------|-------------|
| 28 | Digest package available (historical digest present) |
| 29 | Token-bound digest present |
| 30 | Request digest matches historical (if provided) |
| 31 | Token-bound digest matches historical |
| 32 | Execute-derived digest matches historical (recomputed) |
| 33 | Digest staleness/expiry check |
| 34 | Pre-execution audit not implemented (final block) |

Valid token + valid digest now blocks at:
```
blocked_pre_execution_audit_not_implemented
```

---

## 4. Security Boundary

| Item | Status |
|------|--------|
| OpenAPI path count changed | No — remains 33 |
| Runtime route count changed | No — remains 33 |
| Frontend changed | No |
| STATIC_ALLOWLIST changed | No — remains `frozenset({"clarify"})` |
| Allowlist expanded | No |
| Raw token stored | No |
| Raw token logged | No |
| TokenHash exposed | No |
| Raw arguments stored | No |
| Raw arguments logged | No |
| Secrets stored | No |
| Production home accessed | No |
| Pre-execution audit implemented | No |
| Post-execution audit implemented | No |
| Handler lookup enabled | No |
| Tool Handler called | No |
| Tool Dispatch | No |
| Tool Execution | No |
| Provider Schema sent | No |
| Provider API called | No |
| Real Controlled Execution started | No |

---

## 5. Route Governance

| Metric | Value |
|--------|-------|
| OpenAPI paths | 33 |
| Runtime routes | 33 |
| Tool GET routes | 4 |
| Tool write routes | 0 |
| Tool dry-run routes | 1 |
| Tool execution routes | 1 |
| STATIC_ALLOWLIST | `frozenset({"clarify"})` |

---

## 6. Tests

| Test Suite | Count | Status |
|------------|-------|--------|
| `test_dev_web_tool_execute_digest.py` | 45 | Pass |
| `test_dev_web_tool_execute_confirmation.py` | 56 | Pass |
| `test_dev_web_tool_execute_preflight.py` | — | Pass |
| `test_dev_web_tool_dry_run.py` | — | Pass |
| `test_dev_web_tool_dry_run_api.py` | — | Pass |
| `test_dev_web_tool_dry_run_audit.py` | — | Pass |
| `test_dev_web_tool_execute.py` | 89 | Pass |
| `test_dev_web_tool_execute_api.py` | — | Pass |
| `test_dev_check_webui.py` | — | Pass |
| `test_dev_web_0c06_closure.py` | — | Pass |
| Full regression | 1096 | Pass |

---

## 7. Known Limitations

- Pre-execution audit not yet implemented
- Post-execution audit not yet implemented
- Execute route still does not execute tools
- Handler lookup not yet enabled
- Frontend execute UI not implemented
- Historical audit events before Phase 1G-04-22 may not contain `dryRunDecisionDigest` — preflight lookup returns `None` for these, which causes digest verification to fail (by design)
- Legacy tokens without digest binding fail closed
- Append-only JSONL audit and token stores may have race conditions in concurrent scenarios (acceptable for local dev)

---

## 8. Acceptance Criteria

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Digest module implemented | ✅ |
| 2 | Digest package builder implemented | ✅ |
| 3 | Canonicalization implemented | ✅ |
| 4 | SHA-256 hex digest computation implemented | ✅ |
| 5 | Dry-run decision digest generated | ✅ |
| 6 | Digest persisted in audit event | ✅ |
| 7 | Digest returned in dry-run response | ✅ |
| 8 | Confirmation token binds non-null digest | ✅ |
| 9 | Legacy null-digest token fails closed | ✅ |
| 10 | Execute digest verification gates implemented | ✅ |
| 11 | Valid token + valid digest blocks at pre-execution audit | ✅ |
| 12 | OpenAPI paths = 33 | ✅ |
| 13 | Runtime routes = 33 | ✅ |
| 14 | STATIC_ALLOWLIST unchanged | ✅ |
| 15 | Production gateway unaffected | ✅ |
| 16 | Local commit, not pushed | ✅ |

---

*Phase 1G-04-22 Digest Verification Minimal Implementation: digest package building, canonicalization, sha256:hex dryRunDecisionDigest computation, dry-run response digest fields, dry-run audit digest persistence, confirmation token non-null digest binding, legacy null digest fail-closed behavior, and execute digest verification gates implemented. Execute remains blocked-only at the pre-execution audit boundary. No real Controlled Execution started.*

---

## 9. Next Dependency

Phase 1G-04-23 freezes the pre-execution audit boundary.

Phase 1G-04-23 still does not implement pre-execution audit, post-execution audit, handler lookup, dispatch, execution, provider calls, or real Controlled Execution.
