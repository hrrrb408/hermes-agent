# Phase 1G-04-17: Preflight Production Path Guard Hardening

## Document Information

| Field | Value |
|-------|-------|
| Phase | 1G-04-17 |
| Title | Preflight Production Path Guard Hardening / Still Blocked-Only |
| Status | Completed locally / Not pushed |
| Date | 2026-06-13 |
| Author | Dev Agent (Phase 1G-04-17 implementation) |
| Dependencies | Phase 1G-04-16 completed locally |
| Branch | dev-huangruibang |
| Base commit | `48053820295aa11fa15e931152d19164e8473830` |
| Implementation | Backend path guard hardening + tests + docs |

---

## 1. Phase Definition

Phase 1G-04-17 = Preflight Production Path Guard Hardening / Still Blocked-Only.

This phase hardens the dry-run execute preflight lookup's production path guard from equality-only checks to containment-based checks using `Path.relative_to()`.

This phase does **not** implement confirmation token issuance.
This phase does **not** implement confirmation token verification.
This phase does **not** implement digest verification.
This phase does **not** implement token store.
This phase does **not** implement pre-execution audit.
This phase does **not** implement post-execution audit.
This phase does **not** enable handler lookup.
This phase does **not** dispatch tools.
This phase does **not** execute tools.
This phase does **not** call providers.
This phase does **not** start real Controlled Execution.

---

## 2. Baseline

| Metric | Value |
|--------|-------|
| Base HEAD | `48053820295aa11fa15e931152d19164e8473830` |
| OpenAPI paths | 33 |
| Runtime routes | 33 |
| Tool GET routes | 4 |
| Tool write routes | 0 |
| Tool dry-run routes | 1 |
| Tool execution routes | 1 |
| STATIC_ALLOWLIST | `frozenset({"clarify"})` |
| Execute Route | Blocked-only |
| Production Guard | Equality-only (`home == prod_home`) |

---

## 3. Problem Statement

Phase 1G-04-16 implemented a production path guard in `_resolve_audit_path()` that rejected HERMES_HOME exactly matching production home:

```python
prod_home = Path(_PRODUCTION_HERMES_HOME).resolve()
if home == prod_home:
    return Path(), ERROR_DRY_RUN_LOOKUP_UNAVAILABLE
```

This equality-only guard had two weaknesses:

1. **Production subtree not blocked**: HERMES_HOME set to `/Users/huangruibang/.hermes/gateway` or any subdirectory of `~/.hermes` would pass the equality check.
2. **Symlink/path traversal not fully covered**: While the resolved audit path was checked against `home`, there was no explicit check for the resolved audit path being inside production home, and no check for the resolved audit path escaping the expected dev audit directory.

The operation was already safe because:
- The lookup is read-only (no writes).
- Production subtree lookups would fail-closed on missing files.
- The resolved audit path was validated against home.

However, defense-in-depth requires that production paths are rejected at the path resolution stage, before any filesystem access.

---

## 4. Implemented Hardening

### 4.1 New Helper: `_is_relative_to()`

Added a path containment helper using `Path.relative_to()`:

```python
def _is_relative_to(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False
```

This uses proper path containment semantics (not string prefix matching), avoiding false positives on paths like `/Users/.../.hermes-dev` which share a string prefix with `/Users/.../.hermes` but are not inside it.

### 4.2 Production Home Containment Guard

The old equality-only guard:

```python
if home == prod_home:
    return Path(), ERROR_DRY_RUN_LOOKUP_UNAVAILABLE
```

Was replaced with containment-based guard:

```python
if home == prod_home or _is_relative_to(home, prod_home):
    return Path(), ERROR_DRY_RUN_LOOKUP_UNAVAILABLE
```

This blocks:
- HERMES_HOME = `/Users/huangruibang/.hermes` (exact match)
- HERMES_HOME = `/Users/huangruibang/.hermes/gateway` (subtree)
- HERMES_HOME = `/Users/huangruibang/.hermes/gateway/dev/audit` (deep subtree)

### 4.3 Resolved Audit Path Production Containment

After building the audit path, the resolved audit path is also checked:

```python
resolved_audit = audit_path.resolve()
if resolved_audit == prod_home or _is_relative_to(resolved_audit, prod_home):
    return Path(), ERROR_DRY_RUN_LOOKUP_UNAVAILABLE
```

This catches:
- Symlinks in the audit path that resolve into production home
- Path traversal components that resolve into production home

### 4.4 Dev Audit Directory Containment

A new check ensures the resolved audit path stays inside the expected dev audit directory:

```python
expected_audit_dir = (home / _AUDIT_DIR_RELATIVE).resolve()
if not _is_relative_to(resolved_audit, expected_audit_dir):
    return Path(), ERROR_DRY_RUN_LOOKUP_UNAVAILABLE
```

This catches:
- Symlinks inside the audit directory pointing outside it
- Path traversal (`../../..`) that escapes the audit directory

### 4.5 No File Open Before Guard

All containment checks are performed before any file is opened. The guard returns early with `ERROR_DRY_RUN_LOOKUP_UNAVAILABLE` if any check fails.

---

## 5. Fail-Closed Behavior

Production containment violations:
- Do not throw uncaught exceptions
- Do not open any audit file
- Return `found=False` with `error_code=dry_run_lookup_unavailable`
- All side-effect flags remain false:
  - `toolHandlerCalled=false`
  - `providerApiCalled=false`
  - `executionStarted=false`

---

## 6. No Behavior Expansion

The lookup success path semantics are unchanged:
- Valid dry-run lookup + all binding checks pass → still blocked at confirmation token boundary
- No request enters handler lookup, dispatch, execution, provider schema sending, or provider API call

---

## 7. Blocked-Only Guarantee

The execute route remains blocked-only:
- `executionAllowed` is always `False`
- `dispatchAllowed` is always `False`
- `providerSchemaAllowed` is always `False`
- `toolHandlerCalled` is always `False`
- `providerApiCalled` is always `False`
- `executionStarted` is always `False`
- `executionCompleted` is always `False`
- `executionAttempted` is always `False`

---

## 8. Route Governance

No routes were added, removed, or modified:

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

## 9. Security Boundary

| Item | Status |
|------|--------|
| OpenAPI file changed | No |
| OpenAPI path count changed | No |
| Frontend changed | No |
| Routes changed | No |
| Tool write route changed | No |
| STATIC_ALLOWLIST changed | No |
| Allowlist expanded | No |
| Confirmation token implemented | No |
| Digest verification implemented | No |
| Token store implemented | No |
| Pre/post execution audit implemented | No |
| Handler lookup enabled | No |
| Tool Handler called | No |
| Tool Dispatch | No |
| Tool Execution | No |
| Provider Schema sent | No |
| Provider API called | No |
| Real Controlled Execution started | No |

---

## 10. Tests

### 10.1 Preflight Reader Tests (test_dev_web_tool_execute_preflight.py)

New test classes added:

| Class | Tests | Coverage |
|-------|-------|----------|
| `TestProductionPathContainmentGuard` | 7 | Exact production home, production subtree (2 levels), .hermes-dev not falsely blocked, no file open on violation (exact + subtree), valid dev home still works |
| `TestIsRelativeToHelper` | 7 | child inside parent, child equals parent, child outside parent, sibling, .hermes-dev vs .hermes, production subtree, deep subtree |
| `TestResolveAuditPathContainment` | 9 | Direct `_resolve_audit_path` tests for production home, production subtree, valid dev home, missing env, empty env, path traversal escaping audit dir, symlink to production, .hermes-dev path |

### 10.2 Execute Model Tests (test_dev_web_tool_execute.py)

New tests added:
- `test_production_home_hermes_home_blocks_before_lookup`
- `test_production_subtree_hermes_home_blocks`
- `test_production_guard_failure_keeps_side_effect_flags_false`
- `test_valid_dev_lookup_still_blocks_at_confirmation`
- `test_fake_confirmation_token_still_blocks`

### 10.3 Execute API Tests (test_dev_web_tool_execute_api.py)

New test class:
- `TestProductionContainmentAPI` with 4 tests for API-level production guard verification

### 10.4 Test Results

All tests pass:
- Preflight reader: 57 passed
- Execute model: 87 passed
- Execute API: 60 passed
- Route governance: 328 passed (combined)
- Dry-run regressions: 528 passed, 2 skipped

---

## 11. Known Limitations

- Symlink tests are skipped on systems that don't support symlinks
- The production home path is hardcoded to `/Users/huangruibang/.hermes` (matching the development environment)
- Confirmation token issuance/verification is not implemented
- Digest verification is not implemented
- Token store is not implemented

---

## 12. Risks

### P0
- None identified.

### P1
- None identified.

### P2
- Confirmation token issuance/verification not yet implemented
- Token store not yet implemented
- Digest verification not yet implemented
- Pre/post execution audit not yet implemented
- Execute route still does not execute tools
- Handler lookup not yet enabled
- Frontend execute UI not implemented
- Browser smoke not re-run
- Clarify handler-level audit still needs future phase
- Lookup performance can be optimized later
- Multi-file audit rotation support may be future work

---

## 13. Acceptance Criteria

- [x] Production path guard changed from equality-only to containment-based
- [x] Exact production home blocks before file open
- [x] Production subtree blocks before file open
- [x] Audit path inside production home blocks
- [x] Path traversal outside dev audit directory blocks
- [x] Symlink resolving into production home blocks where feasible
- [x] `.hermes-dev` style path not falsely blocked
- [x] Valid dev HERMES_HOME still works
- [x] No production file read
- [x] No production file write
- [x] Lookup remains read-only
- [x] Execute route remains blocked-only
- [x] Valid lookup still blocks at confirmation token boundary
- [x] Fake confirmation token still blocks
- [x] No confirmation token implementation
- [x] No digest verification implementation
- [x] No token store
- [x] No pre/post execution audit
- [x] No handler lookup
- [x] No Tool Handler call
- [x] No dispatch
- [x] No execution
- [x] No Provider Schema
- [x] No Provider API
- [x] STATIC_ALLOWLIST remains `frozenset({"clarify"})`
- [x] No allowlist expansion
- [x] OpenAPI paths = 33
- [x] Runtime routes = 33
- [x] Tool GET = 4, Tool write = 0, Tool dry-run = 1, Tool execution = 1
- [x] Tests pass
- [x] memory-check PASS
- [x] dev-check PASS
- [x] Production Gateway unaffected
- [x] Local commit created
- [x] No push
- [x] Phase 1G-04-18 not started
- [x] Real Controlled Execution not started
