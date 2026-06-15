# Phase 2D-H1 — Audit Storage Hardening

## Identification

| Field | Value |
|-------|-------|
| Phase | 2D-H1 — Audit Storage Hardening |
| Hardening ID | `HARDENING-2D-H1-001` |
| Audit Consistency ID | `AUDIT-CONSISTENCY-2D-H1-001` |
| Audit Stress ID | `AUDIT-STRESS-2D-H1-001` |
| Audit Security Closure ID | `AUDIT-SECURITY-CLOSURE-2D-H1-001` |
| Input HEAD | `4836aca4ced0a345098de450876178541e227295` |
| Input HEAD message | `feat(webui): add advanced audit storage indexing` |
| Status | completed and pushed |
| Branch | `dev-huangruibang` |

## Purpose

Harden the Phase 2D durable dev audit store from MVP to a stable audit
infrastructure that can carry Phase 2E / Phase 3. This is a hardening phase —
not Phase 2E. It does not add product capability, does not add routes, does not
enable production rollout, and does not call real Provider vendors.

## Scope

- **In scope:** deterministic 10-lens review of the Phase 2D audit store
  (schema, sanitizer, append store, index, query, rotation, recovery,
  dual-write bridge, API + Viewer no-leak, production isolation); stress and
  consistency test coverage; one real latent-bug fix; hardening audit script;
  hardening documentation; risk-register + plan addenda.
- **Out of scope (deferred P2):** production audit rollout, encryption at rest,
  multi-user audit namespace, retention deletion, compression, advanced
  full-text indexing, cross-device sync, real provider vendor integration,
  frontend UX polish.

## Input capability (Phase 2D, unchanged)

Dev-only durable audit store at `$HERMES_HOME/gateway/dev/audit-store`:

- canonical `audit_schema_v2`
- unified audit sanitizer (closes the Phase 2A `str(object)` gap)
- append-only durable writer (file lock + on-disk sequence floor)
- audit index (build / update / rebuild / repair)
- cursor pagination + offset backward compatibility
- filters + safe substring search
- rotation by size / event count
- corruption detection + quarantine (non-destructive)
- legacy → canonical dual-write bridge (7 audit kinds)
- enhanced Audit Viewer (store-mode toggle, status badges)

## Hardening model — deterministic 10-lens review

Each lens was reviewed with explicit scope, evidence (commands run), findings,
fixes, a PASS/WARN/FAIL verdict, and residual risk.

### Lens 1 — Audit Schema / Canonical Event Boundary

- **Scope:** `audit_schema_v2` is stable; every event is JSON-native; required
  fields present; enumerations legal; unsafe fields rejected.
- **Evidence:** `tests/test_dev_web_phase_2d_audit_schema.py`,
  `tests/test_dev_web_phase_2d_h1_audit_security.py` (TestSchemaRejectsUnsafeEvents,
  TestCanonicalPreservesCorrelationFields).
- **Findings:** schema rejects missing `eventId` / `sequence`, non-JSON
  metadata, wrong `schemaVersion`; unsafe `rawArguments` / `fullTokenHash` are
  redacted to `[REDACTED]` before persistence; provider / write / rollback /
  confirmation correlation fields are preserved without leaking payloads.
- **Fixes:** none required.
- **Verdict:** PASS.
- **Residual risk:** none.

### Lens 2 — Unified Sanitizer / Redaction Boundary

- **Scope:** single redaction surface; no `str(object)` / `repr(object)` /
  `default=str` fallback; callable / object / bytes / exception collapse to
  sentinels; secret values, forbidden fields, full hashes, production paths
  redacted.
- **Evidence:** `tests/test_dev_web_phase_2d_audit_sanitizer.py`,
  `tests/test_dev_web_phase_2d_audit_security.py`,
  `tests/test_dev_web_phase_2d_h1_audit_security.py` (TestSanitizerNoStrFallback,
  TestSanitizerScrubbedStrings, TestSanitizerSecretMatrix,
  TestSanitizerSourceNoStrFallback).
- **Commands:** source grep confirms the non-JSON-native branch returns
  `NON_JSON_VALUE_SENTINEL`; no `default=str` in the sanitizer module.
- **Findings:** the Phase 2A `str(object)` gap remains closed. Every non-JSON-
  native type (callable, function, bound method, object instance, class,
  module, bytes, exception) collapses to a safe sentinel or class-name summary.
  Secret value patterns (`sk-*`, `Bearer`, `Authorization`, `api_key=`, PEM
  blocks, git-URL credentials) and forbidden field stems (api_key, password,
  secret, credential, tokenSecret, confirmationToken, rawArguments, fileContent,
  fullTokenHash, providerPayload, …) are redacted.
- **Fixes:** one latent inconsistency (see Lens 10 fix log).
- **Verdict:** PASS.
- **Residual risk:** none.

### Lens 3 — Append-only Store / Sequence Consistency

- **Scope:** append-only durability; monotonic gap-free sequence; unique
  `eventId`; no lost events under concurrency; the on-disk sequence floor
  recovers from stale / deleted / corrupt store-meta.
- **Evidence:** `tests/test_dev_web_phase_2d_audit_store.py`,
  `tests/test_dev_web_phase_2d_h1_audit_store_hardening.py`
  (TestHighConcurrencyAppend 32-thread, TestSequenceFlooring,
  TestAppendNeverCorruptsActiveSegment, TestLargeBatchAndOversized,
  TestWriterLockLocation, TestRepeatedRunStability).
- **Commands:** `for i in 1..5; run hardening tests` → 5/5 pass.
- **Findings:** 32-thread × 40-event stress yields unique contiguous sequences
  1..1280 with zero lost events. Deleting / stale-low-corrupting `store-meta.json`
  never produces a colliding sequence (the floor against the on-disk maximum
  recovers). Large batches (200 events) are contiguous. The oversized-line guard
  (`ERROR_EVENT_TOO_LARGE`) rejects a >64 KiB synthetic payload. The writer lock
  file lives only under the dev audit-store meta dir.
- **Fixes:** none required.
- **Verdict:** PASS.
- **Residual risk:** none.

### Lens 4 — Index Build / Update / Repair Consistency

- **Scope:** index build from empty and multi-segment stores; equality query
  equals a full segment scan for every indexed field; missing / corrupt / stale
  index repaired; index carries no secrets / raw args.
- **Evidence:** `tests/test_dev_web_phase_2d_audit_index.py`,
  `tests/test_dev_web_phase_2d_h1_audit_consistency.py` (TestIndexBuildFromEmpty,
  TestIndexQueryEqualsScan, TestIndexRepair, TestIndexHasNoSecrets).
- **Findings:** for every indexed field (eventType / toolId / status / auditKind /
  source / providerMode / readOnly / writeRequired / createdDate) the index
  bucket set equals the full-scan bucket set. Missing index → rebuild; corrupt
  sequence marker → rebuild; stale index (event appended without rebuild) →
  repair. Index files contain no secrets or raw arguments.
- **Fixes:** none required.
- **Verdict:** PASS.
- **Residual risk:** none.

### Lens 5 — Cursor Query / Filter / Search Stability

- **Scope:** opaque tamper-resistant cursor pagination; asc / desc windowing;
  filters; safe substring search; validation rejects oversized / negative
  limits, invalid dates, unsafe search, invalid enumerations; cursor carries no
  path / secret / index internal.
- **Evidence:** `tests/test_dev_web_phase_2d_audit_query.py`,
  `tests/test_dev_web_phase_2d_audit_api.py`,
  `tests/test_dev_web_phase_2d_h1_audit_consistency.py` (TestCursorWindowing,
  TestCursorTamperAndMismatch, TestQueryValidation, TestFiltersAndSearch,
  TestLegacyOffsetCompat, TestCursorTokenNoLeak).
- **Findings:** cursor next (asc / desc) windows correctly; query hash is stable
  (ignores limit / cursor); tampered / mismatched / direction-mismatched cursors
  are blocked with explicit codes; oversized / negative / non-integer limits,
  invalid dates, unsafe / oversized search, and invalid enumerations are
  blocked. Legacy bare-integer offset cursor remains backward compatible. The
  cursor token decodes to a strict field whitelist (`v`, `lastSequence`,
  `direction`, `queryHash`, `issuedAt`) — no path, secret, or index internal.
- **Fixes:** none required.
- **Verdict:** PASS.
- **Residual risk:** backward pagination (`previousCursor`) is intentionally
  `None` in Phase 2D (documented); not a regression.

### Lens 6 — Rotation / Segment Recovery Boundary

- **Scope:** rotation by size and by event count; monotonic zero-padded segment
  names; rotation never overwrites or deletes; queries + indexes span segments;
  partial / interrupted rotation recovers.
- **Evidence:** `tests/test_dev_web_phase_2d_audit_rotation.py`,
  `tests/test_dev_web_phase_2d_h1_audit_store_hardening.py`
  (TestRotationByCount, TestQueryAndIndexAcrossSegments,
  TestPartialRotationRecovery).
- **Findings:** rotation by size and by count is deterministic; segment numbers
  are strictly monotonic and zero-padded; original segment content is preserved
  across rotations (append-only); queries and index rebuilds transparently span
  multiple segments; an interrupted rotation (rotation-state pointing at a
  not-yet-existing segment) is reconciled on the next append; old segments are
  never deleted.
- **Fixes:** none required.
- **Verdict:** PASS.
- **Residual risk:** none.

### Lens 7 — Corruption Detection / Quarantine Boundary

- **Scope:** every corruption class is detected, copied to a dev-local
  quarantine, and skipped by the query path; repair rebuilds the index without
  losing valid events; a corrupt line never crashes the API.
- **Evidence:** `tests/test_dev_web_phase_2d_audit_recovery.py`,
  `tests/test_dev_web_phase_2d_h1_audit_store_hardening.py`
  (TestCorruptionDetectionAllClasses, TestQuarantineNonDestructive,
  TestCorruptLineNeverCrashesQuery).
- **Findings:** invalid JSON, not-an-object, missing required field, schema
  version mismatch, non-JSON-native value, unsafe secret, duplicate sequence,
  duplicate eventId, and partial-write (no trailing newline) are all detected.
  Quarantine is non-destructive (source segment left intact) and lives only
  under the dev audit store. The query path skips corrupt lines and reports
  `skippedMalformed`; repair rebuilds the index while keeping valid events.
- **Fixes:** none required.
- **Verdict:** PASS.
- **Residual risk:** none.

### Lens 8 — Legacy Dual-write / Compatibility Boundary

- **Scope:** all 7 legacy audit kinds flow into the canonical store via the
  dual-write bridge; legacy offset read still works; no duplicate event
  display.
- **Evidence:** `tests/test_dev_web_phase_2d_audit_integration.py`,
  `tests/test_dev_web_tool_audit_read.py`,
  `tests/test_dev_web_tool_audit_read_api.py`,
  `tests/test_dev_web_phase_2d_h1_audit_consistency.py`
  (TestDualWriteAllKinds, TestLegacyReadCompat, TestBridgeRobustness).
- **Findings:** dry-run / pre-execution / post-execution / provider / write /
  rollback / confirmation all bridge to the store exactly once per eventId;
  re-bridging the same eventId is rejected (no duplicate); legacy offset
  pagination and the legacy per-kind JSONL read path remain intact; the bridge
  never raises on bad input.
- **Fixes:** none required.
- **Verdict:** PASS.
- **Residual risk:** none.

### Lens 9 — Audit API / Viewer No-leak Boundary

- **Scope:** API and Audit Viewer output never carries raw arguments, plain
  tokens, full token hashes, API keys, callable reprs, or production paths —
  across all 7 audit kinds.
- **Evidence:** `tests/test_dev_web_phase_2d_audit_api.py`,
  `tests/test_dev_web_phase_2d_audit_security.py`,
  `tests/test_dev_web_phase_2d_h1_audit_security.py` (TestApiOutputNoLeak,
  TestCursorTokenStrictWhitelist); live smoke
  `phase2d_audit_store_indexing` (9 Playwright tests, all PASS).
- **Findings:** store-mode output is secret-free on disk and in API output
  across all kinds; index files carry no secrets; the cursor token field set is
  a strict whitelist. The live Playwright smoke confirms store query returns
  the enriched shape, filters work, cursor pagination advances,
  `redactionApplied` is surfaced, no secret / callable / raw-args leaks,
  cursor tamper is rejected, and the route stays read-only (POST → 405).
- **Fixes:** none required.
- **Verdict:** PASS.
- **Residual risk:** none.

### Lens 10 — Production Isolation / Runtime Artifact Boundary

- **Scope:** no `~/.hermes` access; no production `state.db` access; no
  production rollout; runtime audit artifacts never committed.
- **Evidence:** `tests/test_dev_web_phase_2d_h1_audit_security.py`
  (TestQuarantineDevLocalOnly, TestRuntimeArtifactsGitignored,
  TestMinimalSafeEventFallback); hardening script production-safety lens; git
  boundary searches.
- **Commands:** production gateway observed at PID 28428 (count 1) throughout;
  ports 5180 / 5181 free at start and end; `git diff` boundary search returns
  no runtime artifacts, no secrets, no production access.
- **Findings:** quarantine lives only under the dev audit store; runtime
  artifacts (audit-store / token / rollback manifest / audit JSONL) are
  gitignored and never staged; `.claude/` is never committed.
- **Fixes:** one latent inconsistency closed (see fix log).
- **Verdict:** PASS.
- **Residual risk:** future host-reboot PID drift may require an authorized
  baseline refresh (P2, unchanged from Phase 2D).

## Fix log (product code)

Exactly one product-code change was made — a real latent inconsistency, not a
security boundary change:

- **`hermes_cli/dev_web_audit_sanitizer.py` — `_minimal_safe_event`:** the
  fallback event carried `sequence: -1`, but `validate_canonical_event` rejects
  negative sequences, so the fallback could never persist through the store —
  contradicting its own docstring ("still validates against the schema so the
  store writer can persist a breadcrumb"). Changed `sequence: -1` → `sequence: 0`
  (0 is non-negative and passes validation; the store writer stamps the real
  monotonic sequence on append anyway). Security-neutral: no boundary is
  loosened, no field is newly accepted, no secret path is changed. Existing
  sanitizer + security tests continue to pass.

No other product code was changed. The hardening phase is otherwise test /
script / documentation only.

## 10-lens summary

| Lens | Name | Status | Findings | Fixes |
|------|------|--------|----------|-------|
| 1 | Audit Schema / Canonical Event Boundary | PASS | schema stable; unsafe fields redacted | none |
| 2 | Unified Sanitizer / Redaction Boundary | PASS | str() fallback closed; full redaction matrix | sanitizer sequence fix (shared w/ Lens 10) |
| 3 | Append-only Store / Sequence Consistency | PASS | 32-thread, no lost events, sequence floor | none |
| 4 | Index Build / Update / Repair Consistency | PASS | index == scan for all fields; repair works | none |
| 5 | Cursor Query / Filter / Search Stability | PASS | pagination stable; tamper/mismatch blocked | none |
| 6 | Rotation / Segment Recovery Boundary | PASS | rotate by size/count; no overwrite; spans segments | none |
| 7 | Corruption Detection / Quarantine Boundary | PASS | all classes detected; query skips; non-destructive | none |
| 8 | Legacy Dual-write / Compatibility Boundary | PASS | 7 kinds once; legacy read intact | none |
| 9 | Audit API / Viewer No-leak Boundary | PASS | no secret/args/callable/path; live smoke PASS | none |
| 10 | Production Isolation / Runtime Artifact Boundary | PASS | no prod access; artifacts uncommitted | sanitizer sequence fix (shared w/ Lens 2) |

**10 / 10 lenses PASS. 0 P0. 0 P1.**

## Conclusion

Phase 2D's durable dev audit store is hardened. The store survives concurrency,
stale meta, rotation, corruption, and dual-write under deterministic stress;
the sanitizer closes the `str(object)` leak with no residual fallback; the API
and Viewer leak nothing; runtime artifacts stay uncommitted; production is
untouched. Phase 2E remains eligible as the separately authorized next phase.

See companion docs:
- [Consistency report](phase-2d-h1-audit-consistency-report.md)
- [Stress report](phase-2d-h1-audit-stress-test-report.md)
- [Security closure](phase-2d-h1-audit-security-closure.md)
- [Test report](phase-2d-h1-test-report.md)

## Next phase — Phase 2E (Frontend UX Polish)

Phase 2E follows as the frontend product-workflow / operator-polish slice. It is
frontend-only: a unified developer console at `/#/console` that surfaces the
hardened Phase 2D audit store (plus the Phase 2A–2C-H1 capabilities) as coherent
workflows. It adds **no** backend capability, route, or boundary change — the
durable audit store and its 10-lens hardening (schema, sanitizer, append-only
consistency, index, cursor query, rotation/recovery, corruption quarantine,
legacy dual-write, no-leak API, production isolation) are consumed read-only by
the new Audit Viewer section and Overview dashboard. See
[phase-2e-frontend-ux-polish](phase-2e-frontend-ux-polish.md).
