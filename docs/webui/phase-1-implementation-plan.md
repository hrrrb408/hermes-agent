# Phase 1 Implementation Plan

> **Phase 2A Update:** Phase 2A (read-only multi-tool execution MVP) implemented.
> `STATIC_ALLOWLIST` transitioned `frozenset({"clarify"})` → 6 read-only tools
> (clarify + tool_policy_read, route_governance_read, audit_events_read,
> dev_environment_read, release_status_read). Inventory 71→76, candidate 6→11,
> R0 1→3, R1 5→8. Route governance unchanged (34/34/5/0/1/1). See
> [phase-2a-real-tool-execution-mvp.md](phase-2a-real-tool-execution-mvp.md).

> **Phase 2A-H1 Update:** Phase 2A Hardening — Adversarial Review Completion &
> Boundary Stabilization. **Status: completed and pushed.** Hardening ID
> `HARDENING-2A-H1-001`; Closure ID `ADV-REVIEW-CLOSURE-2A-H1-001`; Boundary
> Audit ID `BOUNDARY-AUDIT-2A-H1-001`. Input HEAD
> `0527d6c892b24afde03ff9259a612b2f59ee8018`. Purpose: close the Phase 2A P2
> (adversarial-review agent died mid-run) by replacing the unstable agent-only
> evidence path with a deterministic, agent-independent 7-lens hardening audit
> and a full gate re-run. Result: 7 / 7 lenses PASS, 0 P0, 0 P1. Deliverables:
> `tests/test_dev_web_phase_2a_hardening_boundaries.py` (45 tests) +
> `scripts/run-dev-webui-phase2a-hardening-audit.sh` (deterministic audit,
> Overall PASS) + four hardening docs. No product-code change; route governance
> unchanged (34/34/5/0/1/1); `STATIC_ALLOWLIST` unchanged (6 read-only tools);
> Provider still deferred (Phase 2B); Tool write still deferred (Phase 2C);
> Production Gateway PID 1962 untouched; no `~/.hermes` / `state.db` access.
> **Phase 2B: completed and pushed.** Controlled Provider Schema / API
> round-trip (deterministic fake provider) implemented; real provider blocked
> by default. No new route (reuses `POST /tools/execute` with
> `mode=provider_roundtrip`); route governance unchanged (34/34/5/0/1/1);
> `STATIC_ALLOWLIST` unchanged; Tool write still deferred (Phase 2C); no
> production rollout, no `~/.hermes` / `state.db` access, no API key exposed.
> See [phase-2b-provider-schema-api-integration.md](phase-2b-provider-schema-api-integration.md).
> The original Phase 2A hardening note follows:
> [phase-2a-hardening-adversarial-review.md](phase-2a-hardening-adversarial-review.md),
> [phase-2a-hardening-boundary-audit.md](phase-2a-hardening-boundary-audit.md),
> [phase-2a-hardening-test-report.md](phase-2a-hardening-test-report.md),
> [phase-2a-hardening-closure.md](phase-2a-hardening-closure.md).

**Date:** 2026-06-08
**Status:** Phase 1-00, 1A-00, 1A, 1B-00, 1B, 1C-00, 1C, 1C-Post, 1D-00, 1D, 1E-00, 1E, 1F-00, 1F, 1G-00, 1G-01, 1G-02 Completed; 1G-03 Closed (1G-03-01 through 1G-03-07 Completed); 1G-04-00 Completed; 1G-04-01 Completed locally (not pushed); 1G-04-02 Completed locally (not pushed); 1G-04-03 Completed locally (not pushed); 1G-04-04 Completed and Pushed; 1G-04-05 Completed locally (not pushed); 1G-04-06 Completed locally (not pushed); 1G-04-07 Completed locally (not pushed); 1G-04-08 Completed locally (not pushed); 1G-04-09 Completed locally (not pushed); 1G-04-10 Completed locally (not pushed); 1G-04-11 Completed and Pushed; 1G-04-12 Completed locally (not pushed); 1G-04-13 Completed locally (not pushed); 1G-04-14 Completed locally (not pushed); 1G-04-24 Completed locally (not pushed); 1G-04-25 Completed locally (not pushed); 1G-04-26 Completed locally (not pushed); 1G-04-27 Completed locally (not pushed); 1G-04-28 Completed locally (not pushed); 1G-04-29 Completed locally (not pushed); 1G-04-30 Completed and Pushed; 1G-04-31 Sealed and Pushed — **Phase 1G-04 WebUI mainline SEALED**; 1G-05 Post-Sealing Readiness pushed — Pilot / release entry baseline; 1G-06 Pilot Release Rehearsal / Smoke Harness Hardening pushed — release rehearsal baseline; 1G-07 Release Candidate Dry Run pushed — RC `RC-1G-07-001` GO, eligible to enter Pilot acceptance; 1G-08 Pilot Acceptance Preparation completed locally (not pushed) — Pilot `PILOT-1G-08-001` prepared against RC `RC-1G-07-001`; 1G-08 Pilot Acceptance Pack **pushed** at `9812c069e`; 1G-09 Pilot Acceptance Execution **pushed** at `cd7298416` — Pilot `PILOT-1G-08-001` / execution `PILOT-EXEC-1G-09-001` executed against RC `RC-1G-07-001`, **Pilot Result: PASS**; 1G-10 Post-Pilot Closeout / Final Release Decision Preparation completed locally (not pushed) — Pilot Result remains PASS, release authorization pending human approver sign-off; 1G-10A Smoke Harness PID Baseline Refresh completed locally (not pushed) — dev-only smoke harness PID baseline refreshed `69355` → `1962` after the Phase 1G-10 host-reboot drift, fresh browser smoke PASS, no production / route / allowlist change, no release authorization; 1G-10B Human Approver Final Decision **pushed** at `3c6ae479b` — designated human approver (黄瑞邦) recorded GO (`HUMAN-DECISION-1G-10B-001`), release authorization granted, P2-09 resolved, no production / route / allowlist change; 1G-11 Final Release Seal & Phase 2 Unlock **completed and pushed** — Final Seal ID `FINAL-SEAL-1G-11-001`, Phase 2 Unlock ID `PHASE-2-UNLOCK-1G-11-001`, Phase 1G **SEALED**, Phase 2 **UNLOCKED**, Phase 2A not started, no production rollout / code / OpenAPI / test / frontend route changes
**Depends on:** Phase 0E-Release (commit `cc64aa690`)
**Governance scope:** `docs/webui/phase-1-00-planning-and-scope.md`

---

## Overview

Phase 1 transitions the Dev WebUI from a purely read-only observability dashboard to a controlled Dev Operations Console. Capabilities are introduced incrementally under strict safety gates defined in `docs/webui/phase-0e-06-phase-1-safety-boundary.md`.

**Progression principle:**

```
Read-only first → Dry-run second → Dev-only execute third → High-risk last
```

---

## Phase 1-00: Planning & Scope Freeze — Completed ✅

**Status:** Completed
**Date:** 2026-06-08

### Deliverables

- `docs/webui/phase-1-00-planning-and-scope.md` — Complete Phase 1 planning document with subphase roadmap, scope, non-goals, safety gates, acceptance criteria, risk register, and release strategy
- `docs/webui/phase-1-implementation-plan.md` — This document
- Updated `docs/webui/phase-0e-06-phase-1-safety-boundary.md` — Link to Phase 1-00
- Updated `docs/webui/phase-0e-implementation-plan.md` — Next-phase pointer

### Acceptance

- ✅ Repository state verified (branch, HEAD, remote sync, clean worktree)
- ✅ Phase 0E completion confirmed (all subphases completed and pushed at `cc64aa690`)
- ✅ Phase 1 Safety Boundary reviewed and confirmed
- ✅ Phase 1 subphase roadmap frozen (1A through 1G)
- ✅ Each subphase has scope, non-goals, write capability, safety gates, acceptance criteria
- ✅ Risk register defined (P0, P1, P2)
- ✅ No business code modified
- ✅ No new API routes added
- ✅ memory-check PASS
- ✅ dev-check PASS
- ✅ compileall PASS
- ✅ Local commit created
- ✅ Not pushed
- ✅ Production environment unaffected

---

## Phase 1A-00: Review Queue Read-Only Scope & Contract Freeze — Completed ✅

**Status:** Completed
**Date:** 2026-06-08

### Deliverables

- `docs/webui/phase-1a-00-review-queue-readonly-scope.md` — Complete scope freeze document with:
  - Review Queue data source audit (structure, storage, functions, sensitive fields)
  - Read-only API proposal frozen (3 GET routes with request/response schemas)
  - DTO whitelist frozen (16 list fields, 16+ detail fields, transformations documented)
  - Forbidden fields documented (raw content, paths, secrets, internal metadata)
  - Redaction rules defined (reusing existing `redact_local_paths()`)
  - Error model frozen (7 error codes, envelope, validation rules)
  - Pagination/filter/sort strategy frozen (offset-based, 4 filters, 2 sort orders)
  - Frontend information architecture frozen (panel layout, components, safety area)
  - OpenAPI strategy documented (11 paths unchanged, 14 after Phase 1A)
  - dev-check update strategy (11 → 14 paths)
  - Playwright smoke update strategy (10 new checks)
  - Side-effect hash validation strategy (SHA-256 before/after)

### Acceptance

- ✅ Review Queue data source audited
- ✅ Read-only API proposal frozen
- ✅ DTO whitelist and forbidden fields documented
- ✅ Error model frozen
- ✅ Frontend information architecture frozen
- ✅ OpenAPI strategy: no change to current 11-path contract
- ✅ No API implemented, no business code modified
- ✅ memory-check PASS
- ✅ dev-check PASS
- ✅ compileall PASS
- ✅ Local commit created, not pushed
- ✅ Production environment unaffected

---

## Phase 1A: Review Queue Read-Only Panel — Completed ✅

**Status:** Completed
**Priority:** P2 (Low risk, no write)
**Estimated scope:** Medium (3 new GET routes + frontend panel)
**Dependencies:** Phase 0E-Release completed
**Completion date:** 2026-06-08

### Goal

Display Memory Review Queue items in the Dev WebUI as a read-only panel.

### Modification Scope

| File | Action |
|------|--------|
| `hermes_cli/dev_web_api.py` | **Modify** — Add 3 GET review routes |
| `hermes_cli/dev_web_schemas.py` | **Modify** — Add review DTOs |
| New service file (review query service) | **New** — Read-only review queries |
| `docs/webui/openapi/dev-web-api-v1.yaml` | **Modify** — Add 3 review routes |
| Frontend Review panel | **New** — Review tab, list, detail |
| `hermes_cli/main.py` | **Modify** — Update dev-check route count |
| Test files | **New** — Route tests, DTO tests, forbidden route tests |

### New Routes

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/dev/v1/reviews/status` | Review queue status |
| GET | `/api/dev/v1/reviews` | List review items |
| GET | `/api/dev/v1/reviews/{reviewId}` | Review item detail |

### Write Capability

**None.** Strictly read-only.

### Non-Goals

- No approve, reject, or enqueue operations
- No review item modification
- No memory write/update/archive
- No agent run or tool execution

### Acceptance Criteria

1. 3 new GET routes registered and documented in OpenAPI spec
2. Route count updated in dev-check (12 → 15)
3. Forbidden route tests updated
4. Frontend Review panel displays review items
5. All 5 themes render correctly
6. No review/memory files modified (SHA-256 hash unchanged)
7. DTO whitelisting prevents raw content/prompt leakage
8. Path redaction applied
9. All quality gates PASS
10. Production untouched

---

## Phase 1B-00: Review Queue Approve/Reject Dry-Run Scope & Contract Freeze — Completed ✅

**Status:** Completed
**Date:** 2026-06-08

### Deliverables

- `docs/webui/phase-1b-00-review-queue-dry-run-scope.md` — Complete scope freeze document with:
  - Review approve/reject real side-effect audit (5 files for approve, 2 files for reject)
  - Dry-run vs execute boundary definition
  - 2 proposed dry-run POST routes with request/response contracts
  - DTO whitelist (28+ fields for approve, 20+ fields for reject)
  - Forbidden fields documentation
  - Error model (12 error codes)
  - UI information architecture (dry-run controls, result panel, safety display)
  - OpenAPI strategy (14 paths unchanged in 1B-00, 16 after 1B)
  - dev-check update strategy (14 → 16, dry-run vs execute distinction)
  - Playwright smoke update strategy (11 new checks)
  - Side-effect hash validation strategy

### Acceptance

- ✅ Review approve/reject real side effects audited
- ✅ Dry-run vs execute boundary defined
- ✅ 2 dry-run API draft routes frozen
- ✅ DTO whitelists and forbidden fields documented
- ✅ Error model frozen
- ✅ Frontend information architecture frozen
- ✅ OpenAPI strategy: no change to 14-path contract
- ✅ No API implemented, no business code modified
- ✅ memory-check PASS
- ✅ dev-check PASS
- ✅ compileall PASS
- ✅ Local commit created, not pushed
- ✅ Production environment unaffected

---

## Phase 1B: Review Queue Approve/Reject Dry-Run — Completed ✅

**Status:** Completed
**Priority:** P2 (Medium risk, no real write)
**Estimated scope:** Medium (2 dry-run routes + confirmation UI)
**Dependencies:** Phase 1A completed
**Completion date:** 2026-06-09

### Goal

Enable dry-run preview of Review Queue approve and reject operations without real state mutation.

### Modification Scope

| File | Action |
|------|--------|
| `hermes_cli/dev_web_api.py` | **Modify** — Add 2 dry-run POST routes |
| `hermes_cli/dev_web_schemas.py` | **Modify** — Add dry-run DTOs |
| Review service | **Modify** — Add dry-run logic |
| Frontend confirmation UI | **New** — Dry-run preview dialog |
| `docs/webui/openapi/dev-web-api-v1.yaml` | **Modify** — Add 2 routes |
| Test files | **New/Modify** — Dry-run tests, hash tests |

### New Routes

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/dev/v1/reviews/{reviewId}/approve/dry-run` | Preview approve |
| POST | `/api/dev/v1/reviews/{reviewId}/reject/dry-run` | Preview reject |

### Write Capability

**None.** All operations are dry-run only.

### Non-Goals

- No real approve/reject execution
- No memory write/update/archive
- No event append

### Acceptance Criteria

1. ✅ 2 new POST routes (dry-run only)
2. ✅ Dry-run response shows `wouldModify`, `wouldWriteMemory`, `wouldUpdateReview`, `wouldAppendEvent`
3. ✅ P0/permanent items blocked in dry-run
4. ✅ All hashes unchanged after dry-run
5. ✅ Safety display visible (dev-only, production blocked)
6. ✅ All quality gates PASS
7. ✅ Production untouched

---

## Phase 1C-00: Review Queue Execute Scope & Safety Boundary Freeze — Completed ✅

**Status:** Completed
**Date:** 2026-06-09

### Deliverables

- `docs/webui/phase-1c-00-review-queue-execute-scope.md` — Complete scope freeze document with:
  - Approve/reject real write-effect audit (6 files for WRITE approve, 7 for UPDATE approve, 2 for reject)
  - Failure modes and half-completion analysis
  - Lock and concurrency analysis (two-level lock: RLock + fcntl)
  - Race condition identification (TOCTOU between dry-run and execute)
  - Proposed execute API routes (2 POST routes with `/execute` suffix)
  - Request/response DTO contracts with confirmation model
  - Dry-run-first requirement
  - Kill switch strategy (disabled by default, configuration-based)
  - Dev-only environment guard strategy
  - Audit trail strategy
  - Revalidation strategy
  - Rollback/recovery strategy
  - Frontend information architecture (confirmation dialog, acknowledged effects)
  - Error model (9 new execute-specific error codes)
  - OpenAPI strategy (16 → 18 paths, Phase 1C-00 does not change current contract)
  - dev-check strategy
  - Playwright smoke strategy
  - Side-effect validation strategy (disabled mode + temporary fixture mode)

### Acceptance

- ✅ Approve/reject real write effects audited
- ✅ Failure modes and concurrency audited
- ✅ Dev-only execute scope frozen
- ✅ Execute routes草案 frozen (`/approve/execute`, `/reject/execute`)
- ✅ Explicit confirmation model frozen
- ✅ Kill switch strategy frozen (disabled by default)
- ✅ Dev-only guard strategy frozen
- ✅ Audit trail strategy frozen
- ✅ Rollback/recovery strategy frozen
- ✅ OpenAPI strategy: no change to 16-path contract
- ✅ No API implemented, no business code modified
- ✅ memory-check PASS
- ✅ dev-check PASS
- ✅ compileall PASS
- ✅ Local commit created, not pushed
- ✅ Production environment unaffected

---

## Phase 1C: Review Queue Approve/Reject Dev-Only Execute — Completed ✅

**Status:** Completed ✅
**Priority:** P1 (High risk, real write)
**Estimated scope:** Large (2 execute routes + audit + confirmation + kill switch)
**Dependencies:** Phase 1B completed

### Goal

Allow real execution of Review Queue approve/reject in dev-home only.

### Modification Scope

| File | Action |
|------|--------|
| `hermes_cli/dev_web_api.py` | **Modify** — Add 2 execute POST routes |
| `hermes_cli/dev_web_schemas.py` | **Modify** — Add execute DTOs |
| Review service | **Modify** — Add execute logic with confirmation |
| Audit service | **New** — Audit trail implementation |
| Kill switch configuration | **New** — Environment variable / config flags |
| Frontend execute flow | **New** — Confirm → execute → audit display |
| `docs/webui/openapi/dev-web-api-v1.yaml` | **Modify** — Add 2 routes |
| Test files | **New/Modify** — Execute tests, hash validation, audit tests |

### New Routes

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/dev/v1/reviews/{reviewId}/approve/execute` | Execute approve (dev-only) |
| POST | `/api/dev/v1/reviews/{reviewId}/reject/execute` | Execute reject (dev-only) |

### Write Capability

**Yes — dev-home only.** First phase with real write operations.

### Non-Goals

- No agent run
- No tool execution
- No production execution
- No batch operations

### Prerequisites (Must Complete Before Starting)

1. Phase 1B completed and accepted
2. Audit trail design completed
3. Kill switch implemented
4. Explicit confirmation mechanism implemented
5. Production fail-closed verified
6. Rollback strategy documented

### Acceptance Criteria

1. 2 new execute POST routes
2. Dry-run first: execute requires showing dry-run result first
3. Explicit confirmation: backend + UI
4. Dev-only: production paths rejected
5. Audit event: timestamp, actor, action, target, before/after, result
6. State transition verified: PENDING → APPROVED/REJECTED
7. P0/permanent items: backend rejects
8. Hash side-effects match expected
9. Rollback strategy documented
10. All quality gates PASS
11. Production untouched

---

## Phase 1D-00: Memory Writer Dry-Run Scope & Contract Freeze — Completed ✅

**Status:** Completed
**Date:** 2026-06-09

### Deliverables

- `docs/webui/phase-1d-00-memory-writer-dry-run-scope.md` — Complete scope freeze document with:
  - Memory Writer core code audit (runtime_memory_writer.py, memory_router.py, memory_review_queue.py)
  - Decision model audit (WRITE, UPDATE, REVIEW, SKIP, SKIP_DUPLICATE)
  - Similarity and duplicate detection strategy (6 thresholds documented)
  - P0/permanent/protected strategy audit
  - Side-effect matrix (5 operations × 6 resource types)
  - Safe read-only function inventory (40+ functions listed)
  - Forbidden write function inventory (20+ functions listed)
  - Hidden write risk analysis (ensure_memory_scaffold, _ensure_paths)
  - 3 dry-run POST route drafts frozen
  - Request DTOs frozen (WRITE, UPDATE, ARCHIVE)
  - Unified response DTO frozen (with field whitelist)
  - Error model frozen (16 error codes)
  - Frontend information architecture frozen (Writer Preview sub-tab)
  - OpenAPI strategy documented (18 paths unchanged, → 21 after implementation)
  - dev-check strategy, Playwright strategy, side-effect validation strategy, test fixture strategy

### Acceptance

- ✅ Memory Writer core code fully audited
- ✅ Decision model, similarity, protection, side effects documented
- ✅ 3 dry-run route drafts frozen
- ✅ DTO contracts, error model, field whitelist frozen
- ✅ OpenAPI strategy: no change to 18-path contract
- ✅ No API implemented, no business code modified
- ✅ memory-check PASS
- ✅ dev-check PASS
- ✅ compileall PASS
- ✅ Local commit created, not pushed
- ✅ Production environment unaffected

---

## Phase 1D: Memory Writer Dry-Run Panel — Completed ✅

**Status:** Completed
**Date:** 2026-06-09
**Priority:** P2 (Medium risk, no real write)
**Estimated scope:** Medium (3 dry-run routes + preview UI)
**Dependencies:** Phase 0E-Release (independent of 1A/1B/1C)

### Goal

Display Memory Writer decision previews and dry-run results.

### Modification Scope

| File | Action |
|------|--------|
| `hermes_cli/dev_web_api.py` | **Modify** — Add 3 dry-run POST routes |
| `hermes_cli/dev_web_schemas.py` | **Modify** — Add memory dry-run DTOs |
| Memory dry-run service | **New** — Memory writer dry-run wrapper |
| Frontend memory writer panel | **New** — Decision preview display |
| `docs/webui/openapi/dev-web-api-v1.yaml` | **Modify** — Add 3 routes |
| Test files | **New/Modify** — Dry-run tests, hash tests |

### New Routes

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/dev/v1/memory/write/dry-run` | Preview memory write |
| POST | `/api/dev/v1/memory/update/dry-run` | Preview memory update |
| POST | `/api/dev/v1/memory/archive/dry-run` | Preview memory archive |

### Write Capability

**None.** All operations are dry-run only.

### Non-Goals

- No real memory write/update/archive
- No auto-memory
- No event append

### Acceptance Criteria

1. 3 new POST routes (dry-run only)
2. Dry-run shows: action, content summary, category, duplicate score, protection status
3. P0/permanent items show "would be blocked"
4. All memory files hash unchanged
5. Path redaction applied
6. All quality gates PASS
7. Production untouched

---

## Phase 1E-00: Agent Prompt Preview / Dry-Run Scope & Contract Freeze — Completed ✅

**Status:** Completed
**Date:** 2026-06-09

### Deliverables

- `docs/webui/phase-1e-00-agent-prompt-preview-scope.md` — Complete scope freeze document with:
  - Agent call chain fully audited (entry points → config → session → memory → prompt → LLM → tools → persistence → memory writer → review queue)
  - Prompt assembly pipeline audited (stable/context/volatile 3-tier architecture)
  - System Prompt sources audited (SOUL.md, tool guidance, skills, environment hints, context files, memory, profile info)
  - Memory Context injection audited (read-only, no side effects)
  - Session/Message persistence audited (AIAgent auto-persists at 16+ exit points)
  - **Double-persist decision frozen:** Agent Runtime is sole persistence owner (Option A); Web API must NOT write sessions/messages directly
  - Streaming callback audit: `stream_delta_callback` and `_stream_callback` both receive identical deltas
  - **SSE callback decision frozen:** `stream_delta_callback` selected for Phase 1F (constructor-time, public API, true delta)
  - Tool execution boundary audited
  - Runtime Memory Writer trigger point audited (synchronous, after final response)
  - Review Queue trigger point audited
  - Provider/Model config audited (API keys in .env, paths in config.yaml)
  - Safe read-only functions listed (20+ functions)
  - Forbidden execution functions listed (22+ functions)
  - 2 preview route drafts frozen
  - Request DTOs frozen (Prompt Preview + Agent Run Dry-Run)
  - Unified response DTO frozen (with field whitelist)
  - System Prompt exposure strategy frozen (metadata + optional redacted preview, never full text)
  - Error model frozen (13 error codes)
  - Frontend IA frozen (3 sub-tabs: Status, Prompt Preview, Run Dry-Run)
  - Redaction and truncation rules frozen
  - OpenAPI strategy: current 21 paths → future 23 paths
  - dev-check strategy, Playwright Smoke strategy, Side-effect hash strategy, Test fixture strategy defined
  - No P0 blockers identified

### Acceptance

- ✅ Agent call chain audited with source evidence
- ✅ Prompt assembly pipeline audited (3 tiers)
- ✅ System Prompt sources and sensitive content analyzed
- ✅ Memory Context injection confirmed read-only
- ✅ Session/Message persistence ownership frozen (Agent Runtime = sole owner)
- ✅ Streaming callback mechanism selected for Phase 1F (`stream_delta_callback`)
- ✅ Safe/forbidden function lists complete
- ✅ All DTOs, error codes, field whitelists frozen
- ✅ No LLM calls, no agent runs, no tool execution, no writes
- ✅ No API implemented, no business code modified
- ✅ memory-check PASS, dev-check PASS, compileall PASS
- ✅ Production environment unaffected

---

## Phase 1E: Agent Prompt Preview / Dry-Run — Completed ✅

**Status:** Completed
**Priority:** P2 (Medium risk, no LLM)
**Estimated scope:** Medium (2 preview routes + preview UI)
**Dependencies:** Phase 0E-Release (independent of 1A/1B/1C/1D)

### Goal

Preview Agent prompt construction and context assembly without LLM calls.

### Modification Scope

| File | Action |
|------|--------|
| `hermes_cli/dev_web_api.py` | **Modify** — Add 2 preview POST routes |
| `hermes_cli/dev_web_schemas.py` | **Modify** — Add prompt preview DTOs |
| Agent preview service | **New** — Prompt construction wrapper |
| Frontend prompt preview panel | **New** — Prompt/context visualization |
| `docs/webui/openapi/dev-web-api-v1.yaml` | **Modify** — Add 2 routes |
| Test files | **New/Modify** — Preview tests, redaction tests |

### New Routes

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/dev/v1/agent/prompt-preview` | Preview prompt assembly |
| POST | `/api/dev/v1/agent/dry-run` | Simulate agent run (no LLM) |

### Write Capability

**None.** No LLM calls, no tool execution, no state mutation.

### Non-Goals

- No real agent run
- No LLM call
- No SSE streaming
- No message persistence

### Acceptance Criteria

1. 2 new POST routes (preview only)
2. No LLM calls made
3. No tool calls made
4. Prompt content redacted (no keys/secrets)
5. Memory auto-write disabled
6. Production fail-closed
7. All quality gates PASS
8. Production untouched

---

## Phase 1F-00: Agent Dev-Only Run / SSE Scope & Contract Freeze — Completed ✅

**Status:** Completed
**Date:** 2026-06-09

### Deliverables

- `docs/webui/phase-1f-00-agent-run-sse-scope.md` — Complete scope freeze document with:
  - Agent Run complete call graph audited with source evidence (Web API → Run Service → Thread → Agent Init → Config → Session → Memory → Prompt → Provider → Streaming → Tool Loop (disabled) → Persistence → Memory Writer (disabled) → Review Queue (disabled) → Completion → SSE terminal → Registry cleanup)
  - Agent initialization audit (constructor parameters, provider client, API key, tool registry, session_db, callbacks)
  - Streaming callback audit (stream_delta_callback selected, _stream_callback = None)
  - Cancellation propagation audit (interrupt() → _interrupt_requested → _set_interrupt → thread join → timeout)
  - Session/message persistence ownership re-confirmed (Agent Runtime = sole owner, _last_flushed_db_idx dedup)
  - Concurrency audit (same-session 409, global max 1, single-process only)
  - Run Registry designed (in-process, thread-safe, bounded event buffer, TTL cleanup)
  - Run State Machine designed (8 states, 12 transitions, 4 terminal states)
  - Kill Switch defined (HERMES_AGENT_RUN_ENABLED, default disabled, fail-closed)
  - Dev-only environment guard frozen (enforce_dev_environment, production fail-closed)
  - Confirmation model frozen (RUN + dryRunPreviewed + acknowledgedEffects)
  - 4 REST-style routes frozen (POST create, GET status, GET SSE events, POST cancel)
  - Request/Response DTO contracts frozen with field whitelists
  - SSE protocol frozen (10 event types, incremental delta, monotonic sequence, single terminal)
  - Reconnection strategy frozen (Last-Event-ID, 15s grace period, 410 on buffer expiry)
  - Cancel propagation and orphan thread handling frozen (10s timeout, keep reference)
  - Rate limits frozen (1 concurrent, 3/min, 20/hour)
  - Token and cost limits frozen (maxOutputTokens ≤ 4096, null if uncertain)
  - Tool boundary enforcement frozen (empty schema, unexpected tool_call → FAILED)
  - Runtime Memory Writer disable verified (config default off)
  - Review Queue disable verified (config default off)
  - Audit trail frozen (state.db agent_run_audit table, metadata only)
  - Error model frozen (20 error codes with HTTP mapping)
  - Frontend IA frozen (4-tab Agent panel with Live Run tab)
  - Accessibility frozen (ARIA, reduced motion, screen reader)
  - OpenAPI strategy frozen (23 → 27 paths)
  - dev-check strategy, Playwright smoke strategy, backend test strategy frozen
  - Fixture strategy frozen (Fake Provider, tmp_path, no real LLM)
  - No P0 blockers identified

### Acceptance

- ✅ Agent Run call chain fully audited with source evidence
- ✅ Streaming callback mechanism confirmed (stream_delta_callback only)
- ✅ Persistence ownership re-confirmed (Agent Runtime sole owner)
- ✅ Concurrency model audited and policy frozen
- ✅ Run Registry, State Machine, SSE Protocol, Kill Switch designed
- ✅ All DTOs, error codes, field whitelists frozen
- ✅ No LLM calls, no agent runs, no tool execution, no writes
- ✅ No API implemented, no business code modified
- ✅ memory-check PASS, dev-check PASS, compileall PASS
- ✅ Production environment unaffected

---

## Phase 1F: Agent Run Dev-Only Without Tools — Completed ✅

**Status:** Completed ✅
**Date:** 2026-06-09
**Priority:** P1 (High risk, real LLM)
**Estimated scope:** Large (SSE infrastructure + agent run route + audit + cancellation)
**Dependencies:** Phase 1E completed

### Release Fix History

| Fix | Date | Description |
|-----|------|-------------|
| Release Fix 1 | 2026-06-09 | Cancel timeout safety hardening |
| Release Fix 2 | 2026-06-09 | Close release safety gaps |
| Release Fix 3 | 2026-06-09 | Update route boundary assertions (27 paths, 12 POST), add Fake Provider enabled browser smoke |

### Goal

Enable real Agent execution in dev-home with tools disabled and Memory auto-write disabled.

### Modification Scope

| File | Action |
|------|--------|
| `hermes_cli/dev_web_api.py` | **Modify** — Add 4 agent run routes + SSE |
| `hermes_cli/dev_web_schemas.py` | **Modify** — Add agent run DTOs |
| Agent run service | **New** — Agent run orchestration, Run Registry, SSE bridge |
| SSE bridge | **New** — Thread pool → async queue bridge |
| Audit service | **New** — Agent run audit trail |
| Rate limiter | **New** — Request rate limiting |
| Kill switch configuration | **Modify** — Agent run kill switch (HERMES_AGENT_RUN_ENABLED) |
| Frontend agent run UI | **New** — Live Run tab with confirmation, streaming, cancellation |
| `docs/webui/openapi/dev-web-api-v1.yaml` | **Modify** — Add 4 agent run routes |
| `hermes_cli/main.py` | **Modify** — Update dev-check route count |
| Test files | **New/Modify** — Agent run tests, SSE tests, cancellation tests, audit tests |

### New Routes

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/dev/v1/agent/runs` | Create agent run (dev-only, no tools) |
| GET | `/api/dev/v1/agent/runs/{runId}` | Run status |
| GET | `/api/dev/v1/agent/runs/{runId}/events` | SSE stream |
| POST | `/api/dev/v1/agent/runs/{runId}/cancel` | Cancel run |

### Write Capability

**Yes — dev-home only, LLM call.** First phase with LLM invocation.

### P1 Must-Resolve Before Implementation

1. ~~**Double-persist question:** Does `AIAgent.chat()` auto-persist?~~ **Resolved in 1E-00:** Yes, Agent Runtime auto-persists via `_persist_session()` at 16+ exit points. Web API must NOT write sessions/messages directly. (Option A)
2. ~~**SSE mechanism choice:** `stream_delta_callback` vs `stream_callback`?~~ **Resolved in 1E-00:** `stream_delta_callback` selected. Constructor-time callback, true delta interface, public API. Must NOT register `_stream_callback` simultaneously.
3. ~~**Rate limit / timeout / cancellation:** Specific limits?~~ **Resolved in 1F-00:** 1 concurrent, 3/min, 20/hr, 120s overall timeout, 10s cancel timeout. See `phase-1f-00-agent-run-sse-scope.md`.
4. ~~**Audit trail design:** Schema for agent run events?~~ **Resolved in 1F-00:** state.db `agent_run_audit` table with metadata-only fields. See `phase-1f-00-agent-run-sse-scope.md` Section 30.
5. ~~**Kill switch:** Runtime enable/disable mechanism?~~ **Resolved in 1F-00:** `HERMES_AGENT_RUN_ENABLED` env var, default disabled, fail-closed. See `phase-1f-00-agent-run-sse-scope.md` Section 12.

### Non-Goals

- No tool execution
- No Memory auto-write
- No production execution
- No unbounded streaming

### Acceptance Criteria

1. 4 new routes (create, status, SSE events, cancel)
2. SSE follows all CLAUDE.md constraints (thread pool, bridge, single entry, done event, error propagation, disconnect handling, single-generation)
3. Explicit confirmation required (RUN + dryRunPreviewed + acknowledgedEffects)
4. Kill switch enforced (HERMES_AGENT_RUN_ENABLED, default disabled)
5. Dev-only environment guard enforced (fail-closed)
6. Timeout enforced (120s overall, 90s provider, 10s cancel wait)
7. Cancel works (interrupt + join + timeout)
8. Rate limiting enforced (1 concurrent, 3/min, 20/hr)
9. No tools in context (empty tool schema, unexpected tool_call → FAILED)
10. No memory auto-write (config disabled, verified by hash)
11. No double-persist (Agent Runtime sole owner, _last_flushed_db_idx dedup)
12. Audit event produced per Run (state.db agent_run_audit table)
13. All quality gates PASS
14. Production untouched
11. All quality gates PASS
12. Production untouched

---

## Phase 1G-00: Tool Execution Safety Framework — Scope & Contract Freeze — Completed ✅

**Status:** Completed
**Date:** 2026-06-10
**Priority:** P1 (High risk, tool execution)
**Dependencies:** Phase 1F completed and pushed

### Deliverables

- `docs/webui/phase-1g-00-tool-execution-safety-scope.md` — Complete scope freeze document with:
  - Full Tool Registry audit (71 tools, 33 toolsets, ToolEntry fields, dispatch mechanism)
  - Full Toolset audit (33 individual, 25 platform, composite toolsets)
  - Agent Tool Loop call chain (registration, execution, schema construction)
  - CLI/Gateway/Dev Web tool entry points (all confirmed disabled in WebUI)
  - Complete Tool Inventory with per-tool risk classification (R0–R5)
  - Permanent Denylist frozen (26 tools)
  - Candidate Allowlist frozen (6 candidates, 0 enabled)
  - Default-Deny Decision Chain frozen (20 steps)
  - Kill Switch contract frozen (`HERMES_TOOL_EXECUTION_ENABLED`)
  - Dev-only Environment Guard contract frozen
  - Provider Tool Schema boundary frozen
  - Tool Call Request/Response DTOs frozen
  - Parameter Validation Framework frozen (global limits, prohibited patterns)
  - File Path Security rules frozen (allowlist, limits)
  - Network Tool Security rules frozen (default deny)
  - Timeout model frozen (R0: 2s, R1: 5s, hard max: 30s)
  - Cancel model frozen (propagation chain)
  - Concurrency and Call Limits frozen (max 3 calls, global 1 concurrent)
  - Dry-Run response DTO frozen
  - Execute response DTO frozen
  - Output Validation rules frozen (64 KiB serialized, 16 KiB agent, 8 KiB preview)
  - Redaction rules frozen (paths, secrets)
  - Error Model frozen (22 error codes with HTTP mapping)
  - Audit Trail frozen (state.db table, lazy initialization)
  - Session Persistence ownership frozen (Agent Runtime sole owner)
  - Idempotency contract frozen
  - Frontend Information Architecture frozen
  - OpenAPI route roadmap frozen (4 read-only, 3 dry-run, 3 execute)
  - dev-check roadmap frozen (11 new checks)
  - Test matrix frozen (Kill Switch, Allowlist, Denylist, validation, timeout, cancel, output, audit, integration)
  - Risk Register (P0: none, P1: 11 items, P2: 6 items)
  - Sub-phase roadmap frozen (1G-01 through 1G-06)
  - Side-effect validation (zero state modification)
  - Acceptance criteria (65 items)

### Acceptance

- ✅ Git baseline verified (branch, HEAD, remote sync, clean worktree)
- ✅ Phase 1F completion confirmed
- ✅ Production Gateway unaffected (PID 1717 running)
- ✅ Dev Gateway stopped, ports 5180/5181 free
- ✅ Tool Registry fully audited (71 canonical names confirmed)
- ✅ Toolsets fully audited (33 individual toolsets documented)
- ✅ Agent Tool Loop fully audited
- ✅ Per-tool risk classification completed (R0: 1, R1: 5, R2: 19, R3: 26, R4: 17, R5: 3 = 71)
- ✅ Permanent Denylist frozen (26 tools)
- ✅ Candidate Allowlist frozen (6 candidates: 1 R0 + 5 R1, 0 enabled)
- ✅ All safety contracts frozen
- ✅ Sub-phase roadmap frozen (1G-01 through 1G-06)
- ✅ No business code modified
- ✅ No API modified (OpenAPI still 27 paths)
- ✅ No Tool Execution implemented or enabled
- ✅ No Provider Tool Schema sent
- ✅ No Session, Memory, or Review modification
- ✅ memory-check PASS
- ✅ dev-check PASS (WARN for .claude/ only)
- ✅ Production environment unaffected

---

## Phase 1G: Tool Execution Safety Framework — In Progress

**Status:** In Progress (1G-00 ✓, 1G-01 ✓, 1G-02 ✓, 1G-02 Release Test Isolation Fix ✓, 1G-02-Release Not Started, 1G-03 Closed ✓, 1G-04-00 ✓, 1G-04-01 Completed locally, 1G-04-02 Completed locally, 1G-04-03 Completed locally, 1G-04-04 Completed and Pushed, 1G-04-05 Completed locally, 1G-04-06 Completed locally, 1G-04-07 Completed locally, 1G-04-08 Completed locally, 1G-04-09 Completed locally, 1G-04-10 Completed locally, 1G-04-11 Completed and Pushed, 1G-04-12 Completed locally, 1G-04-13 Completed locally, 1G-04-14 Completed locally, 1G-04-15 Completed locally, 1G-04-16 Completed locally, 1G-04-17 Completed locally, 1G-04-18 Completed locally, 1G-04-19 Completed locally, 1G-04-20 Completed locally, 1G-04-21 Completed locally, 1G-04-22 Completed locally, 1G-04-23 Completed locally, 1G-04-24 Completed locally, 1G-04-25 Completed locally, 1G-04-26 Completed locally, 1G-04-27 Completed locally)
**Priority:** P1 (High risk, tool execution)
**Estimated scope:** Large (full tool audit + framework + allowlist + per-tool tests)
**Dependencies:** Phase 1G-00 completed

### Sub-phase Roadmap

| Phase | Name | Scope |
|-------|------|-------|
| 1G-01 | Tool Inventory + Static Policy Module | Inventory, risk classification, static Allowlist/Denylist data — ✅ Completed |
| 1G-02 | Tool Policy Read-Only API / Panel | GET /policy, GET /catalog, frontend panel — ✅ Completed |
| 1G-03 | Tool Schema Preview | Build and display minimal Schema, do NOT send to Provider — ✅ Closed (1G-03-01 through 1G-03-07 Completed) |
| 1G-04 | Tool Call Dry-Run | Validate tool name + args without dispatch — 1G-04-00 ✓, 1G-04-01 Completed locally, 1G-04-02 Completed locally, 1G-04-03 Completed locally, 1G-04-04 Completed and Pushed, 1G-04-05 Completed locally, 1G-04-06 Completed locally, 1G-04-07 Completed locally, 1G-04-08 Completed locally (gate design freeze), 1G-04-09 Completed locally (implementation scope freeze), 1G-04-10 Completed locally (execute route contract / OpenAPI scope freeze), 1G-04-11 Completed and Pushed (backend execute gate skeleton, blocked-only), 1G-04-12 Completed locally (confirmation token / digest backend scope freeze), 1G-04-13 Completed locally (first executable tool candidate / allowlist activation scope freeze), 1G-04-14 Completed locally (clarify allowlist activation, still blocked-only), 1G-04-15 Completed locally (dry-run historical lookup / confirmation-digest preflight binding scope freeze), 1G-04-16 Completed locally (dry-run historical lookup read-only implementation), 1G-04-17 Completed locally (preflight production path guard hardening), 1G-04-18 Completed locally (confirmation token scope freeze), 1G-04-19 Completed locally (confirmation token minimal backend implementation scope freeze), 1G-04-20 Completed locally (confirmation token minimal backend implementation, still blocked-only), 1G-04-21 Completed locally (digest verification scope freeze), 1G-04-22 Completed locally (digest verification minimal implementation, still blocked-only), 1G-04-23 Completed locally (pre-execution audit scope freeze), 1G-04-24 Completed locally (pre-execution audit minimal implementation, still blocked-only), 1G-04-25 Completed locally (handler lookup scope freeze), 1G-04-26 Completed locally (handler lookup minimal implementation, still blocked-only), 1G-04-27 Completed locally (dispatch scope freeze), 1G-04-28 Completed locally (dispatch minimal implementation, still blocked-only), 1G-04-29 Completed locally (clarify-only handler call + post-execution audit, default-disabled controlled execution) |
| 1G-05 | Fake Tool Fixture Execute | Temporary HERMES_HOME, fake implementations |
| 1G-06 | Dev-Only R0/R1 Execute | Final approved R0/R1 tools with full safety chain |

### Goal

Establish tool execution safety framework with allowlist, validation, audit, and kill switch.

### Modification Scope

As defined in `docs/webui/phase-1g-00-tool-execution-safety-scope.md`:

| Task | Description |
|------|-------------|
| Static Policy Module | `STATIC_DENYLIST` (26 tools), `STATIC_ALLOWLIST` (0–6 tools) |
| Kill Switch | `HERMES_TOOL_EXECUTION_ENABLED` enforcement |
| Parameter Validation | Global limits, per-tool schema validation |
| Output Validation | Size limits, redaction, serialization |
| Audit Trail | `tool_execution_audit` table in state.db |
| Tool Policy API | Read-only catalog and policy endpoints |
| Dry-Run API | Validate without dispatch |
| Frontend Tool Panel | Policy status, schema preview, dry-run interface |

### Write Capability

**Default: No.** Only explicitly allowlisted, audited tools may be experimentally enabled.

### Permanently Prohibited Tools (26)

See `docs/webui/phase-1g-00-tool-execution-safety-scope.md` Section 8 for the complete Denylist.

- Shell/Terminal: `terminal`, `process`
- Code Execution: `execute_code`
- Filesystem Write: `write_file`, `patch`, `memory`, `skill_manage`
- Subagent: `delegate_task`
- Browser: `browser_navigate`, `browser_snapshot`, `browser_click`, `browser_type`, `browser_scroll`, `browser_back`, `browser_press`, `browser_get_images`, `browser_vision`, `browser_console`, `browser_cdp`, `browser_dialog`
- Desktop: `computer_use`
- Messaging: `send_message`
- Cron: `cronjob`
- Image Gen: `image_generate`
- Admin: `discord_admin`
- IoT Control: `ha_call_service`

### Non-Goals

- No arbitrary tool execution
- No production operations
- No unvalidated tools

### Acceptance Criteria

1. Tool audit complete and documented ✅ (Phase 1G-00)
2. Default deny enforced
3. Allowlist is static
4. Each allowed tool has schema validation, timeout, output redaction, audit
5. Permanently prohibited tools cannot be enabled
6. Kill switch functional
7. All quality gates PASS
8. Production untouched

---

## Phase 1-Release: Final Verification & Push — Not Started

**Status:** Not Started
**Priority:** P0 (release gate)
**Estimated scope:** Small (verification only)
**Dependencies:** All Phase 1 subphases (1A through 1G) completed

### Goal

Run full quality gate, verify clean working tree, verify production safety, and push all Phase 1 commits to `origin/dev-huangruibang`.

### Verification Checklist

1. `memory-check` — PASS
2. `dev-check` — PASS (updated route counts, all checks)
3. `python -m compileall hermes_cli hermes_state.py agent` — PASS
4. `pnpm --filter @hermes/dev-webui test` — PASS
5. `./scripts/run_tests.sh` — PASS
6. `pnpm --filter @hermes/dev-webui exec playwright test` — PASS
7. `git status --short --branch` — Clean
8. `git log --oneline -30` — All Phase 1 commits present
9. Production Gateway PID 1717 still running
10. Production environment unchanged

### Acceptance Criteria

1. All quality gates pass
2. Working tree clean
3. Production environment unchanged
4. All Phase 1 commits on `dev-huangruibang`
5. Successfully pushed to `origin/dev-huangruibang`

---

## Summary Timeline

| Phase | Goal | Status | Dependencies | Write? |
|-------|------|--------|-------------|--------|
| 1-00 | Planning & scope freeze | ✅ Completed | 0E-Release | No |
| 1A-00 | Review Queue read-only scope & contract freeze | ✅ Completed | 1-00 | No |
| 1A | Review Queue read-only panel | ✅ Completed | 1A-00 | No |
| 1B-00 | Review Queue dry-run scope & contract freeze | ✅ Completed | 1A | No |
| 1B | Review Queue dry-run | ✅ Completed | 1B-00 | No |
| 1C-00 | Review Queue execute scope & safety boundary freeze | ✅ Completed | 1B | No |
| 1C | Review Queue execute | ✅ Completed | 1C-00 | Yes (dev) |
| 1D-00 | Memory Writer dry-run scope & contract freeze | ✅ Completed | 0E-Release | No |
| 1D | Memory Writer dry-run | ✅ Completed | 1D-00 | No |
| 1E | Agent prompt preview | ✅ Completed | 0E-Release | No |
| 1F | Agent Run without tools | ✅ Completed | 1E | Yes (dev) |
| 1G-02-00 | Tool policy read-only scope & contract freeze | ✅ Completed | 1G-01 | No |
| 1G-02 | Tool Policy Read-Only API / Panel | ✅ Completed | 1G-02-00 | No |
| 1G | Tool execution framework | In Progress (1G-04-04 pushed, 1G-04-05 completed locally, 1G-04-06 completed locally, 1G-04-07 completed locally, 1G-04-08 completed locally, 1G-04-09 completed locally, 1G-04-10 completed locally, 1G-04-11 completed and pushed, 1G-04-12 completed locally, 1G-04-13 completed locally, 1G-04-14 completed locally, 1G-04-15 completed locally, 1G-04-16 completed locally, 1G-04-17 completed locally, 1G-04-18 completed locally, 1G-04-19 completed locally, 1G-04-20 completed locally, 1G-04-21 completed locally, 1G-04-22 completed locally, 1G-04-23 completed locally, 1G-04-24 completed locally, 1G-04-25 completed locally, 1G-04-26 completed locally, 1G-04-27 completed locally) | 1F | Default No |
| 1-Release | Final verification & push | Not Started | All above | No |

---

## Dependency Graph

```
0E-Release ✅
│
├── 1-00 ✅ (planning only)
│
├── 1A-00 ✅ (review scope & contract freeze)
│
├── 1A ✅ (review read-only)
│
├── 1B-00 ✅ (review dry-run scope & contract freeze)
│
├── 1B ✅ (review dry-run)
│   └── 1C-00 ✅ (review execute scope & safety boundary freeze)
│       └── 1C ✅ (review execute)
│
├── 1D-00 ✅ (memory dry-run scope & contract freeze)
│
├── 1D (memory dry-run)
│
├── 1E (agent preview)
│   └── 1F (agent run)
│       └── 1G-00 (tool scope freeze)
│           └── 1G-01 (static policy)
│               └── 1G-02-00 (policy read-only scope freeze)
│                   └── 1G-02 (policy read-only implementation) ✅
│                       └── 1G-03 (schema preview) ✅
│                           └── 1G-04-00 (dry-run/execution design scope freeze) ✅
│                               └── 1G-04-01 (dry-run policy service model) ✅
│                                   └── 1G-04-02 (dry-run read-only API design) ✅
│                                       └── 1G-04-03 (dry-run API implementation scope freeze) ✅
│                                           └── 1G-04-04 (dry-run API implementation) ✅ Pushed
│                                               └── 1G-04-05 (dry-run browser/network/a11y verification) ✅ Completed locally
│                                                   └── 1G-04-06 (dry-run audit storage scope/design) ✅ Completed locally
│                                                       └── 1G-04-07 (dry-run internal audit writer) ✅ Completed locally
│                                                           └── 1G-04-08 (controlled execution gate scope/design freeze) ✅ Completed locally
│                                                               └── 1G-04-09 (controlled execution implementation scope freeze) ✅ Completed locally
│                                                                   └── 1G-04-10 (execute route contract / OpenAPI scope freeze) ✅ Completed locally
│                                                                       └── 1G-04-11 (backend execute gate skeleton, blocked-only) ✅ Completed and Pushed
│                                                                           └── 1G-04-12 (confirmation token / digest backend scope freeze) ✅ Completed locally
│                                                                               └── 1G-04-13 (first executable tool candidate / allowlist activation scope freeze) ✅ Completed locally
│                                                                                   └── 1G-04-14 (clarify allowlist activation, still blocked-only) ✅ Completed locally
│                                                                                       └── 1G-04-15 (dry-run historical lookup / confirmation-digest preflight binding scope freeze) ✅ Completed locally
│                                                                                           └── 1G-04-16 (dry-run historical lookup read-only implementation) ✅ Completed locally
│                                                                                               └── 1G-04-17 (preflight production path guard hardening) ✅ Completed locally
│                                                                                                   └── 1G-04-18 (confirmation token scope freeze) ✅ Completed locally
│                                                                                                       └── 1G-04-19 (confirmation token minimal backend implementation scope freeze) ✅ Completed locally
│                                                                                                       └── 1G-04-20 (confirmation token minimal backend implementation, still blocked-only) ✅ Completed locally
│                                                                                                           └── 1G-04-21 (digest verification scope freeze) ✅ Completed locally
│                                                                                                               └── 1G-04-22 (digest verification minimal implementation, still blocked-only) ✅ Completed locally
│                                                                                                                   └── 1G-04-23 (pre-execution audit scope freeze) ✅ Completed locally
│                                                                                                                       └── 1G-04-24 (pre-execution audit minimal implementation, still blocked-only) ✅ Completed locally
│                                                                                                                           └── 1G-04-25 (handler lookup scope freeze) ✅ Completed locally
│                                                                                                                           └── 1G-04-26 (handler lookup minimal implementation, still blocked-only) ✅ Completed locally
│                                                                                                                           └── 1G-04-27 (dispatch scope freeze) ✅ Completed locally
│
└── 1-Release (push all)
```

**Independent tracks:**
- Track 1: 1A → 1B-00 → 1B → 1C-00 → 1C (Review Queue)
- Track 2: 1D-00 → 1D (Memory Writer)
- Track 3: 1E → 1F → 1G (Agent + Tools)

Tracks can be developed in parallel. Within each track, phases are sequential.

---

## Phase 1 Closure

**Phase 1-00 is completed.** Planning and scope are frozen.

**Phase 1A-00 is completed.** Review Queue read-only scope and contract are frozen.

**Phase 1A is completed.** Review Queue Read-Only Panel is implemented.
- 3 GET review routes: /reviews/status, /reviews, /reviews/{reviewId}
- Frontend ReviewPanel with read-only panel in workspace
- OpenAPI 14 paths, dev-check updated, side-effect validated
- 169 backend tests, 325 frontend tests, all quality gates pass

**Phase 1B-00 is completed.** Review Queue approve/reject dry-run scope and contract are frozen.

**Phase 1B is completed.** Review Queue Approve/Reject Dry-Run is implemented.
- 2 dry-run POST routes: /reviews/{reviewId}/approve/dry-run, /reviews/{reviewId}/reject/dry-run
- Frontend dry-run UI with approve/reject buttons, result panel, safety display
- OpenAPI 16 paths, dev-check updated, side-effect validated (zero changes)
- 207 backend tests, 325 frontend tests, all quality gates pass

**Phase 1C is completed.** Review Queue dev-only approve/reject execute is implemented with kill switch, dev-only guard, explicit confirmation, and fixture-only write tests.
- Kill switch: `HERMES_REVIEW_EXECUTE_ENABLED` env var, default disabled
- Dev-only guard: rejects production HERMES_HOME
- 2 execute POST routes: /reviews/{reviewId}/approve/execute, /reviews/{reviewId}/reject/execute
- Full confirmation model: confirmationText, expectedAction, reviewUpdatedAt, dryRunPreviewed, acknowledgedEffects
- 330 backend tests (105 review), 325 frontend tests, 24 smoke tests, all quality gates pass
- OpenAPI 18 paths, dev-check updated, side-effect validated (zero changes to real dev-home)
- See `docs/webui/phase-1c-review-queue-execute.md` for full details

**Phase 1C-Post-01: Approve Execute Success-Path Test Closure — Completed ✅**
- 18 new tests covering approve WRITE/UPDATE success paths, DTO safety, and idempotency
- 348 backend tests total, all quality gates pass
- Zero side effects on formal dev-home and production
- See `docs/webui/phase-1c-post-approve-execute-test-closure.md` for full details

**Phase 1D-00 is completed.** Memory Writer dry-run panel scope, contracts, safety boundaries, and validation strategy are frozen.
- `docs/webui/phase-1d-00-memory-writer-dry-run-scope.md` — Complete scope freeze document
- Memory Writer core code fully audited (runtime_memory_writer.py, memory_router.py, memory_review_queue.py)
- Decision model: WRITE, UPDATE, REVIEW, SKIP, SKIP_DUPLICATE with threshold documentation
- Side-effect matrix: 5 operations × 6 resource types
- Safe read-only functions: 40+ functions identified as side-effect-free
- Forbidden write functions: 20+ functions identified as having write effects
- 3 dry-run route drafts frozen: /memory/write/dry-run, /memory/items/{id}/update/dry-run, /memory/items/{id}/archive/dry-run
- DTO contracts, error model (16 codes), field whitelist, redaction rules frozen
- Frontend IA: Writer Preview sub-tab within Memory panel
- No API implemented, no business code modified
- See `docs/webui/phase-1d-00-memory-writer-dry-run-scope.md` for full details

The next subphase is **Phase 1D** (Memory Writer Dry-Run Panel Implementation).

**Phase 1D is completed.** Memory Writer dry-run panel is implemented with 3 dry-run routes, preview UI, and zero side effects.
- 3 dry-run POST routes: /memory/write/dry-run, /memory/items/{id}/update/dry-run, /memory/items/{id}/archive/dry-run
- DevMemoryWriterDryRunService using only safe read-only functions
- Independently enforced P0/permanent protection for UPDATE/ARCHIVE
- Writer Preview sub-tab within Memory panel
- 51 new tests, 476 backend tests total, 325 frontend tests, 24 smoke tests
- OpenAPI 21 paths, side-effect hash validated (zero changes)
- See `docs/webui/phase-1d-memory-writer-dry-run.md` for full details

**Phase 1E-00 is completed.** Agent Prompt Preview / Dry-Run scope, contracts, persistence ownership, streaming strategy, and safety boundaries are frozen.
- `docs/webui/phase-1e-00-agent-prompt-preview-scope.md` — Complete scope freeze document
- Agent call chain fully audited (entry → config → session → memory → prompt → LLM → tools → persistence → memory writer → review queue)
- Prompt assembly pipeline audited (stable/context/volatile 3-tier architecture)
- **Double-persist decision frozen:** Agent Runtime is sole persistence owner (Option A)
- **SSE callback decision frozen:** `stream_delta_callback` selected for Phase 1F
- Safe read-only functions listed (20+), forbidden execution functions listed (22+)
- 2 preview route drafts frozen, DTOs frozen, error model frozen (13 codes)
- System Prompt exposure: metadata + optional redacted preview, never full text
- Frontend IA frozen (3 sub-tabs: Status, Prompt Preview, Run Dry-Run)
- OpenAPI: 21 paths unchanged, 23 paths after Phase 1E
- No P0 blockers identified
- No API implemented, no business code modified
- See `docs/webui/phase-1e-00-agent-prompt-preview-scope.md` for full details

The next subphase is **Phase 1E** (Agent Prompt Preview / Dry-Run Implementation).

**Phase 1F is completed.** Agent Dev-Only Run / SSE is implemented with kill-switch protection, single-session concurrency, Agent Runtime persistence ownership, tools disabled, auto-memory disabled, and formal dev-home disabled-mode validation.
- Kill switch: `HERMES_AGENT_RUN_ENABLED` env var, default disabled, fail-closed
- Dev-only guard: rejects production HERMES_HOME, resolves symlinks
- 4 REST-style run routes: POST create, GET status, GET SSE events, POST cancel
- Full SSE protocol: 10 event types, monotonic sequence, single terminal event, Last-Event-ID reconnect, 15s heartbeat
- Run Registry: in-process, thread-safe, 500 events / 1 MiB buffer, TTL cleanup
- Run State Machine: 8 states, 12 transitions, 4 terminal states
- Audit trail: state.db `agent_run_audit` table, metadata only
- Rate limiting: 1 concurrent, 3/min, 20/hr
- Overall timeout: 120s, cancel wait: 10s
- Frontend Live Run tab with confirmation, streaming, cancellation
- 47 backend tests, 30 frontend tests, all quality gates pass
- OpenAPI 27 paths, dev-check updated
- See `docs/webui/phase-1f-agent-run-sse.md` for full details

The next subphase is **Phase 1G** (Tool Execution Safety Framework).

**Phase 1F-Release Fix 4 is completed.** Cancel Transition Race is fixed, SSE lifecycle events are complete, and browser smoke enforces HTTP and event contracts.
- Root cause: cancel handler used multiple separate lock acquisitions; Worker could complete between them
- Fix: atomic `request_cancel()` in Registry — single lock for all state decisions
- Worker terminal event: now emits RUN_CANCELLED when complete_run detects cancel priority
- SSE first-connection replay: all buffered events from sequence 0 (ensures run.created / run.started)
- Cancel API: never returns 500 for normal races; idempotent for all states
- 8 new cancel race tests, 5 new SSE lifecycle tests
- 630 backend tests, 355 frontend tests, 24 default smoke, 5 enabled smoke
- See `docs/webui/phase-1f-agent-run-sse.md` Section 22 for full details

Phase 1F-Release: Pending final re-verification and push preparation.

**Phase 1G-00 is completed.** Tool Execution Safety Framework scope, inventory, risk classification, permanent denylist, candidate allowlist, validation, audit and phased implementation contracts are frozen.
- `docs/webui/phase-1g-00-tool-execution-safety-scope.md` — Complete scope freeze document
- 71 tools audited with canonical names, unique Primary Risk classification (R0: 1, R1: 5, R2: 19, R3: 26, R4: 17, R5: 3 = 71), and side-effect analysis
- 33 individual toolsets audited with full tool-to-toolset mapping
- Permanent Denylist: 26 tools frozen across 11 categories
- Candidate Allowlist: 6 tools identified (1 R0 + 5 R1), 0 enabled (Allowlist empty until Phase 1G-E)
- Default-Deny Decision Chain: 20 steps, fail-closed at every stage
- Kill Switch contract: `HERMES_TOOL_EXECUTION_ENABLED`, fail-closed semantics
- Sub-phase roadmap: 1G-01 through 1G-06 (Inventory → Policy API → Schema Preview → Dry-Run → Fixture → Execute)
- No business code modified, no API modified (OpenAPI still 27 paths)
- No Tool Execution implemented or enabled
- No Provider Tool Schema sent
- Production Gateway unaffected
- See `docs/webui/phase-1g-00-tool-execution-safety-scope.md` for full details

**Phase 1G-01 is completed.** Tool Inventory and Static Policy Module implemented as `hermes_cli/dev_web_tool_policy.py`.
- 71 canonical tools classified with unique Primary Risk (R0=1, R1=5, R2=19, R3=26, R4=17, R5=3)
- STATIC_DENYLIST: 26 permanently denied tools
- CANDIDATE_ALLOWLIST: 6 candidate tools (1 R0 + 5 R1, not enabled)
- STATIC_ALLOWLIST: empty frozenset — default deny enforced
- Pure-static, immutable, zero-import-side-effect module
- Schema safety validation, argument structure validation, policy completeness validation
- 81 unit tests, all passing — registry equality verified via AST
- No Tool API, Provider Schema, Tool Dispatch, or Tool Execution
- See `docs/webui/phase-1g-01-tool-inventory-static-policy.md` for full details

The next subphase is **Phase 1G-02** (Tool Policy Read-Only API / Panel).

**Phase 1G-02 is completed.** Tool Policy Read-Only API, Frontend Data Layer, Workspace Panel, and Browser Integration are fully implemented.
- 2 GET routes: `/api/dev/v1/tools/policy`, `/api/dev/v1/tools/catalog`
- DevToolPolicyQueryService — pure computation, no I/O, no side effects
- 6 commit chain: scope → service → api → frontend → panel → integration
- OpenAPI 27 → 29 paths, Tool GET routes = 2, Tool write routes = 0
- STATIC_ALLOWLIST remains empty, all tools `allowed=false`
- Provider Tool Schema not sent, Tool Dispatch = 0, Tool Audit absent
- Frontend safety invariants enforced in Pinia store
- 617 backend tests, 506 frontend tests, 63 smoke tests — all passing
- 5 themes × 4 viewports = 20 browser combinations verified
- Zero side effects on formal dev-home
- See `docs/webui/phase-1g-02-tool-policy-read-only-panel.md` for full details

The next subphase is **Phase 1G-04-03 implementation** (Dry-Run API Implementation). Phase 1G-04-03 (Dry-Run API Implementation Scope Freeze) is completed locally.
Phase 1G-03-04 is completed.
Phase 1G-03-04 is completed.

**Phase 1G-03-05 is completed.** Schema Preview Panel UI implemented as a read-only interface on top of the existing frontend data layer.
- `apps/hermes-dev-webui/src/components/workspace/ToolSchemaPreviewPanel.vue` — New single-file component with: read-only notice, summary cards, client-side search/filter, tool list with risk badges/availability/redaction status, detail panel with field-level info, loading/error/empty/retry states, keyboard navigation, responsive layout
- `apps/hermes-dev-webui/src/components/workspace/ToolPolicyPanel.vue` — Added Schema Preview as third sub-tab (overview / catalog / schema-preview)
- `apps/hermes-dev-webui/src/stores/toolPolicy.ts` — Added 'schema-preview' to ToolPolicySubTab union
- `apps/hermes-dev-webui/src/tests/tool-schema-preview-panel.spec.ts` — 70 component tests (render, loading/error/empty, search/filter, selection/detail, sub-tab navigation, accessibility, read-only boundary, network safety, lifecycle)
- `apps/hermes-dev-webui/src/tests/tool-policy-panel.spec.ts` — Updated sub-tab count (2→3) and keyboard navigation expectations
- Frontend unit tests: 649 passed (27 files), TypeScript type-check PASS, ESLint PASS, build PASS
- Backend governance: 261 passed, compileall PASS, memory-check PASS, dev-check PASS
- No router routes, no backend API changes, no OpenAPI changes, no hermes_cli/main.py changes
- No provider schema sending, no tool execution, no tool dispatch, no tool audit, no STATIC_ALLOWLIST change
- Phase 1G-03-06 (Browser Smoke, A11y, Network Safety) not started

**Phase 1G-03-06 is completed.** Browser smoke, a11y, network safety, and theme verification for the Schema Preview Panel.
- `apps/hermes-dev-webui/tests/smoke/phase-1g-03-schema-preview-smoke.spec.ts` — 44 Playwright browser smoke tests covering: full integration, HTTP method safety, network safety, read-only boundary, error/retry, theme/viewport matrix (5 themes × 4 viewports), accessibility
- `docs/webui/phase-1g-03-06-schema-preview-browser-smoke.md` — Full verification report
- All 44 smoke tests pass; all 39 existing tool policy smoke tests pass without regression
- Network safety confirmed: GET-only, 0 POST/PUT/PATCH/DELETE, 0 external/provider requests, 0 forbidden patterns
- A11y confirmed: tab/tabpanel/listbox/option/region roles, label associations, aria-busy, role="status", keyboard navigation
- Theme verification: obsidian, paper, song, ink, sakura-night all pass across 1440×900, 1280×800, 1024×768, 768×900
- No backend API, OpenAPI, router, or source modifications
- Phase 1G-03-07 (Closure) completed — docs-only closure commit created locally

**Phase 1G-03-07 is completed.** Final release verification and closure for Tool Schema Preview.
- `docs/webui/phase-1g-03-final-closure-report.md` — New closure report with full verification results
- `docs/webui/phase-1g-03-tool-schema-preview-scope.md` — Updated status to Closed, added closure record
- Backend governance: 707 passed, 0 failed
- Frontend: 649 passed, type-check PASS, build PASS
- dev-check: OpenAPI=31, Runtime=31, Tool GET=4, Tool write=0, STATIC_ALLOWLIST=empty, Provider Schema not sent
- No code changes, no push, Phase 1G-04 not started

**Phase 1G-04-00 is completed.** Tool Dry-Run / Controlled Execution Design Scope Freeze.
- `docs/webui/phase-1g-04-tool-dry-run-controlled-execution-scope.md` — Complete design scope freeze document
- Dry-Run semantics defined (non-executing simulation, no handler call, no provider call, no mutation)
- Controlled Execution preconditions defined (12 preconditions, all must be true)
- Risk Tier R0–R5 admission policy documented (dry-run eligibility vs execution eligibility)
- Candidate Allowlist policy documented (advisory only, not executable)
- API roadmap: 8 sub-phases (1G-04-00 through 1G-04-07 + beyond)
- UI roadmap: Dry-Run button visually distinct from Execute, no Execute button in design phase
- Audit roadmap: Dry-Run audit and Execution audit design, no implementation
- Kill switches documented: all three remain disabled
- Route governance: OpenAPI=31, Runtime=31, Tool GET=4, Tool write=0 (unchanged)
- STATIC_ALLOWLIST remains empty, Tool Execution disabled, Provider Schema not sent
- No code changes, no API changes, no OpenAPI changes, no frontend changes
- No push, Phase 1G-04-01 not started, Controlled Execution not started
- See `docs/webui/phase-1g-04-tool-dry-run-controlled-execution-scope.md` for full details

**Phase 1G-04-01 is completed locally.** Tool Dry-Run Policy Service Model.
- `hermes_cli/dev_web_tool_dry_run.py` — New pure model module with frozen dataclasses (ToolDryRunRequest, ToolDryRunResult, ToolDryRunPolicySummary), 18 reason codes, argument sanitizer (secret key/value redaction, forbidden fields, depth/string/list limits), risk-tier policy engine (dry_run_tool_policy()), catalog query (list_tool_dry_run_policies()), aggregate summary (compute_dry_run_policy_summary())
- `tests/test_dev_web_tool_dry_run.py` — 425 unit tests covering model immutability, default flags (all false), to_safe_dict JSON-safety, unknown tool blocked, denylist blocked, R0 dry-run allowed but execution false, R1 dry-run allowed/review but execution false, R2 requires review, R3 requires review/redaction, R4 blocked, R5 blocked, candidate allowlist advisory only, STATIC_ALLOWLIST empty, secret redaction (api_key, token, password, authorization, cookie, bearer, credential, private_key, access_key, refresh_token, client_secret, nested secrets), large string/list/nesting truncation, non-mapping arguments, no side effects (no handler calls, no provider, no filesystem, no network, no env mutation, no audit storage), catalog completeness (71 tools, sorted, all false), summary correctness, determinism
- Decision matrix: unknown→would_block, denylist→would_block, R5→would_block, R4→would_block, R3→requires_review/would_redact, R2→requires_review, R1→would_allow, R0→would_allow
- All results guarantee: execution_allowed=False, dispatch_allowed=False, provider_schema_allowed=False, audit_written=False
- stdlib only, zero import side effects, no file IO, no network IO, no provider imports, no tool handler imports
- Dry-run tests: 425 passed, 0 failed
- Related backend tests: all passed
- Route governance: OpenAPI=31, Runtime=31, Tool GET=4, Tool write=0 (unchanged)
- STATIC_ALLOWLIST remains empty, Tool Execution disabled, Provider Schema not sent
- No API routes added, no OpenAPI changes, no frontend changes, no router changes
- No provider schema sending, no tool dispatch, no tool execution, no audit storage
- Local commit created, not pushed
- Phase 1G-04-02 not started, Controlled Execution not started
- Dry-Run policy model exists; Dry-Run HTTP API does NOT exist; Dry-Run UI does NOT exist
- See `docs/webui/phase-1g-04-tool-dry-run-controlled-execution-scope.md` Section 19 for completion record

**Phase 1G-04-02 is completed locally.** Dry-Run Read-Only API Design.
- `docs/webui/phase-1g-04-02-dry-run-read-only-api-design.md` — API design document: endpoint, request/response DTOs, error codes, route governance impact, security boundary, input sanitization, future tests, future OpenAPI, future UI notes, audit behavior
- Recommended endpoint: `POST /api/dev/v1/tools/dry-run` — non-mutating policy decision endpoint
- Request DTO: `canonicalName` (required), `argumentsPreview` (optional object), `sourceContext`, `uiOrigin`, `requestId`
- Response DTO: standard envelope with `ok`/`data`/`error`, policy decision fields, invariant guarantees (executionAllowed=false, dispatchAllowed=false, providerSchemaAllowed=false, auditWritten=false)
- Error codes: 6 codes — `TOOL_DRY_RUN_INVALID_REQUEST`, `TOOL_DRY_RUN_INVALID_CANONICAL_NAME`, `TOOL_DRY_RUN_INVALID_ARGUMENTS`, `TOOL_DRY_RUN_TOOL_NOT_FOUND` (not used as error), `TOOL_DRY_RUN_POLICY_UNAVAILABLE`, `TOOL_DRY_RUN_INTERNAL_ERROR`
- Unknown tool behavior: HTTP 200 with `exists=false` and `decision=would_block` (frozen decision)
- Route governance impact: +1 dry-run route (32), Tool write routes remains 0, separate governance bucket
- Security boundary: no tool handler calls, no dispatch, no execution, no provider schema, no audit, no network
- Input sanitization: reuses Phase 1G-04-01 sanitizer semantics
- Future test scope: 23 planned tests (decision, validation, security, governance)
- Future OpenAPI schema names: 6 recommended (ToolDryRunRequest, ToolDryRunResponse, ToolDryRunData, ToolDryRunDecision, ToolDryRunErrorCode, ToolDryRunPolicySummary)
- Future UI: "No tool executed" notice, no Execute terminology, redaction display
- No API route added, no OpenAPI path added or modified, no runtime route changed
- No frontend source changed, no router changed, no provider schema sending
- No tool handler call, no tool dispatch, no tool execution, no audit storage
- Route governance: OpenAPI=31, Runtime=31, Tool GET=4, Tool write=0 (unchanged)
- STATIC_ALLOWLIST remains empty, Tool Execution disabled, Provider Schema not sent
- Local docs-only commit created, not pushed
- Phase 1G-04-03 not started, Controlled Execution not started
- Dry-Run API designed but NOT implemented; Dry-Run UI does NOT exist
- See `docs/webui/phase-1g-04-tool-dry-run-controlled-execution-scope.md` Section 20 for completion record

**Phase 1G-04-03 is completed locally.** Dry-Run API Implementation Scope Freeze.
- `docs/webui/phase-1g-04-03-dry-run-api-implementation-scope.md` — Implementation scope freeze document: allowed files, forbidden files, request/response/error contracts, route governance, test plan, network safety
- Implementation target frozen: `POST /api/dev/v1/tools/dry-run` — non-mutating policy decision
- Allowed backend files frozen: `dev_web_api.py` + OpenAPI YAML + test files
- Forbidden files frozen: all frontend, agent, tools, toolsets, runtime, memory, review, env, .claude
- Request validation frozen: `canonicalName` (required), `argumentsPreview` (optional object), `sourceContext`, `uiOrigin`, `requestId`
- Response contract frozen: standard envelope with invariant guarantees (executionAllowed=false, dispatchAllowed=false, providerSchemaAllowed=false, auditWritten=false)
- Error contract frozen: 6 error codes (TOOL_DRY_RUN_INVALID_REQUEST, TOOL_DRY_RUN_INVALID_CANONICAL_NAME, TOOL_DRY_RUN_INVALID_ARGUMENTS, TOOL_DRY_RUN_TOOL_NOT_FOUND reserved, TOOL_DRY_RUN_POLICY_UNAVAILABLE, TOOL_DRY_RUN_INTERNAL_ERROR)
- Unknown tool behavior frozen: HTTP 200 with exists=false and decision=would_block
- Route governance frozen: +1 dry-run route (31→32), Tool write routes remains 0, separate governance bucket
- OpenAPI change plan frozen: +1 path + 6 schemas (not modified in this phase)
- Backend implementation frozen: must use existing `dry_run_tool_policy()` only
- Test plan frozen: 29 tests across decision, validation, security, governance categories
- Network safety frozen: no external calls, no provider, no execute, no dispatch, no audit
- No API route added, no OpenAPI path added or modified, no runtime route changed
- No frontend source changed, no router changed, no provider schema sending
- No tool handler call, no tool dispatch, no tool execution, no audit storage
- Route governance: OpenAPI=31, Runtime=31, Tool GET=4, Tool write=0 (unchanged)
- STATIC_ALLOWLIST remains empty, Tool Execution disabled, Provider Schema not sent
- Local docs-only commit created, not pushed
- Phase 1G-04-03 implementation not started, Phase 1G-04-04 not started, Controlled Execution not started
- Dry-Run API scope frozen but NOT implemented; Dry-Run HTTP API does NOT exist; Dry-Run UI does NOT exist
- See `docs/webui/phase-1g-04-tool-dry-run-controlled-execution-scope.md` Section 21 for completion record

**Phase 1G-03-04 is completed.** Schema Preview frontend types, GET-only API client, and Pinia store data layer implemented.
- `apps/hermes-dev-webui/src/types/api/toolSchemaPreview.ts` — TypeScript types matching OpenAPI contract (ToolSchemaPreviewField, ToolSchemaPreviewItem, ToolSchemaPreviewCatalogData, ToolSchemaPreviewLookupData, etc.)
- `apps/hermes-dev-webui/src/api/toolSchemaPreview.ts` — GET-only API client with `fetchToolSchemaPreviewCatalog()` and `fetchToolSchemaPreviewByCanonicalName()`, both using existing `apiGet()` helper
- `apps/hermes-dev-webui/src/stores/toolSchemaPreview.ts` — Pinia store `useToolSchemaPreviewStore` with catalog/preview loading, error handling, abort/race protection, getters (items, availableItems, unavailableItems, counts), reset actions
- `apps/hermes-dev-webui/src/tests/tool-schema-preview-api.spec.ts` — 24 API client tests (GET-only, URL encoding, error handling, network safety)
- `apps/hermes-dev-webui/src/tests/tool-schema-preview-store.spec.ts` — 49 store tests (initial state, loading, error, abort, race, getters, reset, safety)
- Frontend unit tests: 579 passed (26 files), TypeScript type-check PASS, ESLint PASS, build PASS
- Backend governance: 261 passed, compileall PASS, memory-check PASS, dev-check PASS
- OpenAPI paths = 31 (unchanged), Runtime routes = 31 (unchanged), Tool GET = 4 (unchanged), Tool write = 0 (unchanged)
- No UI components, no router routes, no backend changes, no OpenAPI changes
- No provider schema sending, no tool execution, no tool dispatch, no tool audit, no STATIC_ALLOWLIST change
- Phase 1G-03-06 (Browser Smoke, A11y, Network Safety) not started

**Phase 1G-03-03 is completed.** Schema Preview GET-only API and OpenAPI implemented. OpenAPI paths and runtime routes increased from 29 to 31, Tool GET routes increased from 2 to 4, Tool write routes remained 0.

**Phase 1G-03-02 is completed.** Schema Preview Read-Only Service implemented.
- `hermes_cli/dev_web_tool_schema_preview_service.py` — New service module with dependency-injected schema source (`SchemaSourceCallable`), catalog query (`list_schema_previews()`), single-tool lookup (`get_schema_preview()`), catalog model (`ToolSchemaPreviewCatalog`), and lookup result model (`ToolSchemaPreviewLookupResult`)
- `tests/test_dev_web_tool_schema_preview_service.py` — 71 unit tests covering import safety, catalog count (71), stable sorting, single lookup (found/not-found), fake source integration, empty schema, invalid schema, source exception isolation, risk/denylist/candidate behavior, no-execution verification, JSON-safe output, summary counts, and existing API regression
- `hermes_cli/dev_web_tool_schema_preview.py` — Minimal addition: `REASON_UNAVAILABLE_SCHEMA_SOURCE_ERROR` reason code
- `tests/test_dev_web_tool_schema_preview.py` — 4 new tests for the reason code (151 total, was 147)
- Schema source is injectable; default source returns `None` (no real tool handler imports)
- Catalog total = 71, canonicalName set equals Tool Policy inventory
- With full schema source: available = 45 (R0–R3 not denied), unavailable = 26 (denylist)
- With empty source: all 71 unavailable
- Risk rules from 1G-03-01 enforced: R4/R5/denylist unavailable, R3 available with redaction, R0/R1/R2 available
- Source exceptions isolated per-tool — catalog query never fails entirely
- Exact-match lookup only — no fuzzy matching, no case folding
- stdlib only, zero import side effects, no file IO, no network IO, no provider imports, no tool handler imports
- OpenAPI paths = 29 (unchanged), Tool GET routes = 2 (unchanged), Tool write routes = 0 (unchanged)
- STATIC_ALLOWLIST empty, Tool Execution disabled, Provider Schema not sent, Tool Audit absent
- Existing Tool Policy API behavior unchanged (`schemaPreviewAvailable` still `false` in catalog)
- No API routes added, no OpenAPI changes, no frontend changes
- Phase 1G-03-03 (Schema Preview API and OpenAPI) completed — 2 GET routes, 31 OpenAPI paths, 4 Tool GET routes, 0 Tool write routes
- Phase 1G-03-04 (Frontend Data Layer) completed — types, GET-only API client, Pinia store, 73 unit tests
- Phase 1G-03-06 (Browser Smoke, A11y, Network Safety) not started

**Phase 1G-03-01 is completed.** Static Tool Schema Preview model and sanitizer implemented.
- `hermes_cli/dev_web_tool_schema_preview.py` — New module with frozen dataclasses (`SchemaPreviewField`, `SchemaPreviewAvailability`, `ToolSchemaPreview`), sanitizer (`sanitize_schema()`), risk-based availability (`determine_schema_preview_availability()`), and builder (`build_schema_preview()`)
- `tests/test_dev_web_tool_schema_preview.py` — 147 unit tests covering import safety, sanitization, forbidden field redaction, secret pattern detection, truncation, depth/field count limits, cycle safety, risk-based availability, no-execution boundaries, JSON-safe output
- stdlib only, zero import side effects, no file IO, no network IO, no provider imports, no tool handler imports
- OpenAPI paths = 29 (unchanged), Tool GET routes = 2 (unchanged), Tool write routes = 0 (unchanged)
- STATIC_ALLOWLIST empty, Tool Execution disabled, Provider Schema not sent, Tool Audit absent
- No API routes, no OpenAPI changes, no frontend changes
- Phase 1G-03-02 (Schema Preview Read-Only Service) not started
- See `docs/webui/phase-1g-03-tool-schema-preview-scope.md` Section 16 for completion record

**Phase 1G-03-00 is completed.** Tool Schema Preview scope, data model boundary, redaction rules, DTO whitelist, forbidden fields, risk-based availability, API principles, frontend principles, testing strategy, and phase breakdown are frozen.
- `docs/webui/phase-1g-03-tool-schema-preview-scope.md` — Complete scope freeze document
- Schema Preview: read-only, local-only, no Provider Schema send, no Tool Execution
- R0–R3 tools (51) eligible for preview; R4–R5 tools (20) show unavailable reason
- DTO whitelist: 9 top-level fields + 7 per-field fields
- Forbidden fields: 7 categories (callable, paths, runtime, secrets, raw data, dynamic, config)
- Sanitizer enforces: description truncation (240 chars), nested depth limit (4), enum limit (20), field count limit (100)
- API: 2 candidate GET routes (`/schemas`, `/schemas/{name}`), OpenAPI 29 → 31
- Frontend: read-only sub-tab, no execute/dry-run buttons
- Phase breakdown: 7 sub-tasks (1G-03-01 through 1G-03-07)
- No business code modified, no API modified, no frontend modified
- No Tool Execution implemented or enabled
- See `docs/webui/phase-1g-03-tool-schema-preview-scope.md` for full details

**Phase 1G-02-00 is completed.** Tool Policy Read-Only API and Panel scope, contracts, DTO whitelist, frontend information architecture, route governance, testing strategy, and zero-side-effect boundary are frozen.
- `docs/webui/phase-1g-02-00-tool-policy-read-only-scope.md` — Complete scope freeze document
- 2 GET routes frozen: `/api/dev/v1/tools/policy`, `/api/dev/v1/tools/catalog`
- OpenAPI strategy: 27 → 29 paths after implementation
- DTO whitelist: 15 fields per catalog item, 30+ forbidden fields
- Error model: 8 error codes with HTTP mapping
- Frontend IA: Tools as first-level Workspace tab with Policy Overview + Catalog sub-tabs
- Backend service: DevToolPolicyQueryService reading only from static immutable module
- No Registry, Handler, Provider, SessionDB, filesystem, or network access
- Safety flags: all 7 frozen as readOnly=true, sideEffects=false, executeAvailable=false
- 51 acceptance criteria for Phase 1G-02 implementation
- 3-commit implementation plan: Backend → Frontend → Docs
- Future phase boundaries frozen: 1G-03 (Schema Preview), 1G-04 (Dry-Run), 1G-05+ (Audit/Execute)
- No business code modified, no API modified (OpenAPI still 27 paths)
- No Tool Execution implemented or enabled
- See `docs/webui/phase-1g-02-00-tool-policy-read-only-scope.md` for full details

**Phase 1G-00 Documentation Fix is completed.** Risk classification statistics corrected to use unique Primary Risk model.
- Root cause 1: `session_search` classified as R2 in summary but R1 in Candidate Allowlist (it is local-only FTS5 → R1)
- Root cause 2: Tools with mixed capabilities (Spotify, ha_call_service, cronjob) counted in multiple risk levels, causing R0–R5 total = 73 instead of 71
- Fix: Adopted unique Primary Risk model — each tool assigned exactly one risk level = its highest actual risk
- Before: R0=1, R1=4, R2=22, R3=22, R4=20, R5=4 (total 73 ≠ 71)
- After: R0=1, R1=5, R2=19, R3=26, R4=17, R5=3 (total 71 = 71 ✓)
- Spotify section expanded from 1 grouped entry to 7 individual entries with unique risk levels
- No safety policy changes, no Denylist/Candidate composition changes, no business code changes
- See `docs/webui/phase-1g-00-tool-execution-safety-scope.md` Section 39 for full fix record

**Phase 1G-04-06 is completed locally.** Dry-Run Audit Storage Scope / Design Freeze.
- `docs/webui/phase-1g-04-06-dry-run-audit-storage-scope.md` — Audit storage scope/design freeze: event model, sensitive data policy, storage location, retention/rotation, failure modes, future allowed/forbidden files, test plan
- Audit goal: Record local, non-mutating, already-redacted Dry-Run decision results
- Non-goals: No execution recording, no raw arguments, no audit UI, no audit API
- Audit event model: 30 fields with invariant execution flags (always false)
- Sensitive data policy: Reuses existing sanitizer, 18 forbidden field names, 4 secret value patterns
- Storage location: `$HERMES_HOME/gateway/dev/audit/tool-dry-run-audit.jsonl` (dev-only, local-only)
- Retention/rotation: max 32 KiB event, max 5 MiB file, max 3 rotated files
- Failure modes: Audit failure never enables execution, never calls provider
- Future implementation phase: Phase 1G-04-07 (Internal Audit Writer)
- No audit storage implemented, no audit file created, no API code changes
- No OpenAPI changes, no route changes, no frontend changes
- Route governance: OpenAPI=32, Runtime=32, Tool GET=4, Tool write=0, Tool dry-run=1, Tool execution=0
- STATIC_ALLOWLIST remains empty, Tool Execution disabled, Provider Schema not sent
- Local docs-only commit created, not pushed
- See `docs/webui/phase-1g-04-tool-dry-run-controlled-execution-scope.md` Section 24 for completion record

**Phase 1G-04-07 is completed locally.** Internal Audit Writer Implementation.
- `hermes_cli/dev_web_tool_dry_run_audit.py` — New audit writer module: JSONL append, rotation, defensive sanitization, event builder
- `tests/test_dev_web_tool_dry_run_audit.py` — 42 audit writer unit tests
- `hermes_cli/dev_web_api.py` — Dry-Run API handler integrated with audit writer
- `tests/test_dev_web_tool_dry_run_api.py` — Updated + expanded to 61 tests (audit integration + audit failure safety)
- Audit event model: 30+ fields with hard invariants (executionAllowed/dispatchAllowed/providerSchemaAllowed always false)
- Defensive sanitization: Secondary redaction pass on all event values, forbidden field names, secret value patterns
- Storage path: `$HERMES_HOME/gateway/dev/audit/tool-dry-run-audit.jsonl` (dev-only, local-only)
- Retention/rotation: max 32 KiB event, max 5 MiB file, max 3 retained files
- `auditWritten=true` means audit event write success only — does NOT imply tool execution
- Audit write failure: Returns `auditWritten=false`, adds safe policyNote/reasonCode, never enables execution
- No new routes, no OpenAPI changes, no frontend changes, no audit viewer, no audit read API
- Route governance: OpenAPI=32, Runtime=32, Tool GET=4, Tool write=0, Tool dry-run=1, Tool execution=0
- STATIC_ALLOWLIST remains empty, Tool Execution disabled, Provider Schema not sent
- Related backend regression: 1111 passed, 2 skipped
- Local commit created, not pushed

**Phase 1G-04-08 is completed locally.** Controlled Execution Scope / Gate Design Freeze.
- `docs/webui/phase-1g-04-08-controlled-execution-gate-scope.md` — Complete gate design freeze: 15-gate stack, kill switches, allowlist strategy, human confirmation, dry-run preflight, audit preconditions, provider schema boundary, tool handler boundary, execution result boundary, future API/OpenAPI/frontend strategies, test plan (32 tests)
- Gate stack: Gate 0 (build-time) through Gate 14 (post-execution audit), failure of any gate blocks execution
- Kill switches: 3 existing + 1 future, all default false, explicit "true" required
- Allowlist strategy: STATIC_ALLOWLIST empty, R0/R1 eligible after all gates, R2 requires review, R3/R4/R5 blocked
- Human confirmation: Token bound to canonicalName, argument digest, riskTier, requestId; single-use, 5-minute expiry
- Dry-run preflight: Every execution must originate from dry-run `would_allow`; audit write must succeed
- Audit preconditions: Pre-execution audit required (blocks on failure), post-execution audit best-effort
- Provider schema boundary: Controlled Execution does not imply Provider Schema Sending; separate phase required
- Tool handler boundary: Handler called only after all gates pass; policy isolated from handler
- Execution result boundary: Sanitized, 64 KiB max, timeout per tier (R0: 2s, R1: 5s, hard max: 30s)
- Future route: `POST /api/dev/v1/tools/execute` (not added in this phase)
- Test plan: 32 future tests (kill switches, allowlist, risk tier, dry-run, confirmation, security, audit, governance)
- Risk classification: P0 (12 items), P1 (21 items), P2 (8 items)
- Docs-only, no code changes, no OpenAPI changes, no route changes, no frontend changes
- Route governance: OpenAPI=32, Runtime=32, Tool GET=4, Tool write=0, Tool dry-run=1, Tool execution=0
- STATIC_ALLOWLIST remains empty, Tool Execution disabled, Provider Schema not sent
- Controlled Execution not implemented, not started
- Local docs-only commit created, not pushed

**Phase 1G-04-09 is completed locally.** Controlled Execution Implementation Scope Freeze.
- `docs/webui/phase-1g-04-09-controlled-execution-implementation-scope.md` — Implementation scope freeze: future phase split (6 phases), first implementation target, execute route strategy, OpenAPI strategy, first tool candidate policy, allowlist activation rule, kill switch scope, dry-run preflight binding, confirmation token scope, audit preconditions, tool handler lookup scope, execution runtime boundary, failure response contract, route governance future delta, future allowed/forbidden files, test matrix (35 tests), entry/exit criteria
- Future phase split: 1G-04-10 (Execute Route Contract / OpenAPI), 1G-04-11 (Backend Gate Skeleton), 1G-04-12 (Confirmation Token / Digest), 1G-04-13 (Allowlist Staged Activation Scope), 1G-04-14 (First R0/R1 Execution POC), 1G-04-15 (Browser Safety Verification)
- First implementation target: Backend execute gate skeleton only — all requests blocked by default
- Execute route strategy: `POST /api/dev/v1/tools/execute` (not added, route governance unchanged)
- OpenAPI strategy: 8 future schema names defined (not modified in this phase)
- First tool candidate policy: R0/R1 only, local-only, deterministic, no network IO, no secrets
- Allowlist activation rule: One-by-one review, no wildcard, no automatic promotion
- Kill switch scope: Exact `"true"` only, all other values block; necessary but not sufficient
- Dry-run preflight binding: SHA-256 digest, 5-minute expiry, canonicalName/riskTier match required
- Confirmation token scope: Single-use, ≤ 5-minute expiry, binds to requestId/canonicalName/digest/riskTier/auditEventId
- Execution runtime boundary: 64 KiB max result, 5s default / 15s hard timeout
- Failure response contract: 13 blocked response types, no handler/provider/dispatch on blocked
- Test matrix: 35 future tests covering all gates
- Docs-only, no code changes, no OpenAPI changes, no route changes, no frontend changes
- Route governance: OpenAPI=32, Runtime=32, Tool GET=4, Tool write=0, Tool dry-run=1, Tool execution=0
- STATIC_ALLOWLIST remains empty, Tool Execution disabled, Provider Schema not sent
- Controlled Execution not implemented, not started
- Local docs-only commit created, not pushed
- Phase 1G-04-10 not started

**Phase 1G-04-10 is completed locally.** Execute Route Contract / OpenAPI Scope Freeze.
- `docs/webui/phase-1g-04-10-execute-route-contract-openapi-scope.md` — Execute route contract / OpenAPI scope freeze: future route definition, route governance delta, Tool write vs Tool execution classification, request/response schema drafts, decision enum draft, gate status model, audit status model, result preview model, error code draft, blocked-by-default contract, dry-run preflight contract, confirmation contract, future OpenAPI file strategy, future runtime file strategy, future forbidden files, test matrix (31 tests), entry/exit criteria
- Future route: `POST /api/dev/v1/tools/execute` (not added, classified as Tool execution route)
- Route governance delta: OpenAPI 32→33, Runtime 32→33, Tool execution 0→1 (future only, not applied)
- Tool write vs Tool execution classification: Execute route counted as execution, not write
- Request schema draft: 9 fields with required/optional/prohibited classification
- Response schema draft: Standard envelope with 17 data fields, invariant defaults all false
- Decision enum draft: 12 values covering all blocked/executed states
- Gate status model: 14 gates with per-gate pass/fail status
- Error code draft: 22 error codes
- Blocked-by-default contract: All switches unset → blocked; STATIC_ALLOWLIST empty → blocked; no blocked response calls handler
- Dry-run preflight contract: Execute must reference valid dry-run; auditWritten required
- Confirmation contract: Single-use, ≤ 5-minute expiry, binds to 7 fields; no bypass
- Test matrix: 31 future tests
- Docs-only, no code changes, no OpenAPI file changes, no route changes, no frontend changes
- Route governance: OpenAPI=32, Runtime=32, Tool GET=4, Tool write=0, Tool dry-run=1, Tool execution=0
- STATIC_ALLOWLIST remains empty, Tool Execution disabled, Provider Schema not sent
- Controlled Execution not implemented, not started
- Local docs-only commit created, not pushed
- Phase 1G-04-11 not started

**Phase 1G-04-11 is completed and pushed.** Backend Execute Gate Skeleton.
- `hermes_cli/dev_web_tool_execute.py` — New blocked-only execute gate skeleton: 9-gate evaluation (kill_switch, agent_tools, static_allowlist, known_tool, denylist, risk_tier, dry_run_preflight, digest, confirmation), decision/error/gate constants, secret + forbidden-field redaction, frozen request/result models, blocked-result builder, policy summary
- `POST /api/dev/v1/tools/execute` added and classified as a Tool execution route (not a write route)
- Skeleton digest gate accepts any non-empty digest (real verification deferred); skeleton confirmation gate checks presence only (no issuance/verification)
- Even when every gate passes, returns `decision=blocked`, `errorCode=execution_not_implemented`
- All execution flags always false (executionAllowed, dispatchAllowed, providerSchemaAllowed, toolHandlerCalled, providerApiCalled, executionStarted, executionAttempted)
- Stdlib-only module: no provider, handler, dispatch, agent, or toolsets execution imports
- OpenAPI: added 1 path + execute schemas (33 paths total)
- Route governance: OpenAPI=33, Runtime=33, Tool GET=4, Tool write=0, Tool dry-run=1, Tool execution=1
- NOT implemented: token issuance/verification, token store, digest verification, dry-run historical lookup, pre/post execution audit, Tool Handler call, dispatch, execution, Provider Schema send, STATIC_ALLOWLIST population, frontend execute UI
- Execute route remains blocked-only; Real Controlled Execution not started
- Committed and pushed in `3c9220978448d5c5f728f3bf51764378654065ab`
- Phase 1G-04-12 not started

**Phase 1G-04-12 is completed locally.** Confirmation Token / Digest Backend Scope Freeze.
- `docs/webui/phase-1g-04-12-confirmation-token-digest-scope.md` — Confirmation token / digest backend scope freeze: confirmation token goal (necessary-but-never-sufficient proof), digest binding goal (SHA-256 over canonical JSON, anti-substitution), future token lifecycle (12 steps), token payload draft (15 fields, secret-free), token storage strategy (dev-only, ephemeral, never state.db/~/.hermes/git), token expiry + replay prevention (≤ 5 min, single-use, confirmation_missing/invalid/expired/reused), digest canonicalization strategy, digest mismatch contract (blocks before handler lookup), dry-run preflight binding, audit binding, future execute route behavior delta, future OpenAPI strategy (no path change; may add confirmation_expired/reused error codes; stays 33 paths), future allowed/forbidden files, test matrix (30 tests), entry/exit criteria
- Confirmation token scope frozen; digest binding scope frozen
- NOT implemented: token issuance, token verification, token store, digest verification, dry-run historical lookup, pre/post execution audit, execute route behavior change, OpenAPI change, new route, Tool Handler call, Provider Schema send, STATIC_ALLOWLIST change, frontend, audit read API, audit viewer
- Execute route remains blocked-only; Next = future token/digest backend implementation only after user approval; Real Controlled Execution not started
- Route governance: OpenAPI=33, Runtime=33, Tool GET=4, Tool write=0, Tool dry-run=1, Tool execution=1 (unchanged from 1G-04-11)
- STATIC_ALLOWLIST remains empty, Tool Execution disabled, Provider Schema not sent
- Local docs-only commit created, not pushed
- Phase 1G-04-13 not started; real Controlled Execution not started

**Phase 1G-04-13 is completed locally.** First Executable Tool Candidate Selection / Allowlist Activation Scope Freeze.
- `docs/webui/phase-1g-04-13-first-executable-tool-allowlist-scope.md` — First executable tool candidate selection and allowlist activation scope freeze: candidate eligibility criteria (18 criteria), candidate exclusion criteria (13 exclusions), candidate selection strategy (10 steps), candidate recommendation (`clarify` R0), candidate shortlist (6 tools with safety assessment), allowlist activation goal, allowlist activation rules (17 rules), STATIC_ALLOWLIST future delta (`frozenset()` → `frozenset({"clarify"})`, not applied), kill switch relationship, dry-run/confirmation/digest relationship, execute route behavior delta, route governance strategy (no change), future OpenAPI strategy (no change), future allowed files, future forbidden files, future test matrix (28 tests), entry criteria (12 conditions), exit criteria (15 conditions)
- Candidate recommended: `clarify` (R0, pure computation, no I/O, no filesystem, no DB, no network, no state mutation)
- STATIC_ALLOWLIST remains empty — not populated, not activated in this phase
- Docs-only, no code changes, no OpenAPI file changes, no route changes, no frontend changes, no test changes
- No allowlist activation, no token implementation, no digest verification, no execute route behavior change
- No Tool Handler call, no Tool Dispatch, no Tool Execution, no Provider Schema send
- Route governance: OpenAPI=33, Runtime=33, Tool GET=4, Tool write=0, Tool dry-run=1, Tool execution=1 (unchanged)
- STATIC_ALLOWLIST remains empty, Tool Execution disabled, Provider Schema not sent
- Real Controlled Execution not started
- Local docs-only commit created, not pushed
- Phase 1G-04-14 not started; real Controlled Execution not started

**Phase 1G-04-14 is completed locally.** Clarify Allowlist Activation / Still Blocked-Only.
- `docs/webui/phase-1g-04-14-clarify-allowlist-activation.md` — Clarify allowlist gate activation documentation
- `hermes_cli/dev_web_tool_policy.py` — STATIC_ALLOWLIST changed from `frozenset()` to `frozenset({"clarify"})`, clarify entry `statically_allowed=True`, integrity checks updated, `evaluate_static_tool_policy("clarify")` now returns `allowed=True`
- `hermes_cli/dev_web_tool_execute.py` — Gate 3 changed from empty-allowlist check to membership check; `clarify` passes allowlist gate but blocked by later gates; non-`clarify` tools still blocked_by_allowlist
- `hermes_cli/main.py` — dev-check updated to verify `STATIC_ALLOWLIST == frozenset({"clarify"})`
- STATIC_ALLOWLIST = `frozenset({"clarify"})` — only `clarify` is allowlisted
- No wildcard, category, risk-tier, dynamic, or candidate-list-wide allowlist
- Execute route remains blocked-only — `clarify` blocked by later gates (dry-run, confirmation, digest)
- No Tool Handler call, no Tool Dispatch, no Tool Execution, no Provider Schema send, no Provider API call
- No confirmation token, no digest verification, no dry-run historical lookup, no pre/post execution audit
- No real Controlled Execution started
- Route governance: OpenAPI=33, Runtime=33, Tool GET=4, Tool write=0, Tool dry-run=1, Tool execution=1 (unchanged)
- 1141 tests passed, 0 failed
- Local commit created, not pushed
- Next = future dry-run historical lookup / confirmation token / digest implementation or handler audit only after user approval

**Phase 1G-04-15 is completed locally.** Dry-Run Historical Lookup / Confirmation-Digest Preflight Binding Scope Freeze.
- `docs/webui/phase-1g-04-15-dry-run-historical-lookup-preflight-binding-scope.md` — Dry-run historical lookup / confirmation-digest preflight binding scope freeze: dry-run historical lookup goal (read-only retrieval via dryRunRequestId, necessary but never sufficient), historical record source (dev-only audit JSONL, forbidden: ~/.hermes/production/state.db/frontend/provider logs), lookup input contract (7 fields, dryRunRequestId required, policyVersion must match or fail closed), lookup output contract (15 fields, excludes raw arguments/secrets/credentials), lookup failure contract (12 error codes, all block before handler lookup, all keep executionAllowed=false), preflight gate order (21 gates frozen), confirmation token binding goal (binds to dryRunRequestId/digest/canonicalName/arguments/policyVersion/riskTier), digest binding goal (sha256 over 8 canonical fields, prevents substitution/drift), expiry strategy (dry-run TTL ≤ 5 min, token TTL ≤ dry-run TTL), replay prevention strategy (single-use tokens, consumed blocks on reuse), audit binding strategy (lookup references audit event, pre/post audit include digest, never raw secrets), execute route behavior delta (current blocked-only vs. future lookup+binding, may still remain blocked), route governance strategy (no count change, 33/33/4/0/1/1), future OpenAPI strategy (no path change, may refine schemas, 33 paths), future allowed files (10 existing + 4 optional new), future forbidden files (13 categories), future test matrix (33 tests), entry criteria (13 conditions), exit criteria (19 conditions)
- Dry-run historical lookup scope frozen; confirmation-digest preflight binding scope frozen
- NOT implemented: dry-run historical lookup, confirmation token issuance/verification, token store, digest verification, pre/post execution audit, execute route behavior change, OpenAPI change, new route, Tool Handler call, Provider Schema send, STATIC_ALLOWLIST change, frontend, audit read API, audit viewer
- STATIC_ALLOWLIST remains `frozenset({"clarify"})`; Execute route remains blocked-only
- Route governance: OpenAPI=33, Runtime=33, Tool GET=4, Tool write=0, Tool dry-run=1, Tool execution=1 (unchanged)
- Docs-only, no code changes, no OpenAPI file changes, no route changes, no frontend changes, no test changes
- Local docs-only commit created, not pushed
- Next = future dry-run historical lookup implementation only after user approval; real Controlled Execution not started

**Phase 1G-04-16 is completed locally.** Dry-Run Historical Lookup Read-Only Implementation / Still Blocked-Only.
- `hermes_cli/dev_web_tool_execute_preflight.py` — New read-only lookup helper: reads dev-only audit JSONL, searches by dryRunRequestId, returns DryRunHistoricalLookupResult, fail-closed on missing/malformed/not found/expired, does not write files, does not access ~/.hermes, does not expose raw secrets
- `hermes_cli/dev_web_tool_execute.py` — Integrated lookup gates: Gate 7 dryRunRequestId present, Gate 8 dry-run historical lookup, Gate 9 decision must be would_allow, Gate 10 auditWritten must be true, Gate 11 canonicalName binding, Gate 12 riskTier binding, Gate 13 policyVersion binding (no-op), Gate 14 digest binding (no-op), Gate 15 confirmationToken present, Gate 16 confirmation token verification blocks (not implemented); all side-effect flags remain false on every path
- `hermes_cli/dev_web_api.py` — Pass hermes_home to evaluate_tool_execute_request
- `docs/webui/openapi/dev-web-api-v1.yaml` — Added 9 error codes to ToolExecuteErrorCode enum (dry_run_not_found, dry_run_expired, dry_run_not_allowed, dry_run_audit_missing, dry_run_canonical_name_mismatch, dry_run_risk_tier_mismatch, dry_run_policy_version_mismatch, dry_run_lookup_unavailable, confirmation_not_implemented)
- `docs/webui/phase-1g-04-16-dry-run-historical-lookup-read-only-implementation.md` — Phase documentation
- New tests: 35 preflight reader tests; Updated tests: 82 execute + 56 execute-api tests
- Known limitations: policyVersion/argumentsDigest/dryRunDecisionDigest not stored in audit events (binding checks are no-ops), auditWritten uses "presence = written" mapping
- STATIC_ALLOWLIST remains `frozenset({"clarify"})`; Execute route remains blocked-only
- Route governance: OpenAPI=33, Runtime=33, Tool GET=4, Tool write=0, Tool dry-run=1, Tool execution=1 (unchanged)
- Not implemented: confirmation token, digest verification, token store, pre/post execution audit, handler lookup, dispatch, execution, provider schema, provider API, frontend execute UI, audit read API, audit viewer, real Controlled Execution
- Local commit created, not pushed
- Next = future confirmation token issuance / verification scope or implementation only after user approval; real Controlled Execution not started

**Phase 1G-04-17 is completed locally.** Preflight Production Path Guard Hardening / Still Blocked-Only.
- `hermes_cli/dev_web_tool_execute_preflight.py` — Hardened production path guard from equality-only (`home == prod_home`) to containment-based checks using `Path.relative_to()`. Added `_is_relative_to()` helper. New guards: production subtree containment, resolved audit path production containment, dev audit directory containment, symlink/path traversal protection. No file opened before guard passes.
- `.hermes-dev` style paths NOT falsely blocked (containment uses `Path.relative_to()`, not string prefix)
- Execute route remains blocked-only; valid lookup still blocks at confirmation token boundary
- STATIC_ALLOWLIST remains `frozenset({"clarify"})`; no allowlist expansion
- Route governance: OpenAPI=33, Runtime=33, Tool GET=4, Tool write=0, Tool dry-run=1, Tool execution=1 (unchanged)
- Not implemented: confirmation token, digest verification, token store, pre/post execution audit, handler lookup, dispatch, execution, provider schema, provider API, frontend execute UI, audit read API, audit viewer, real Controlled Execution
- Local commit created, not pushed
- Next = future confirmation token issuance / verification scope or implementation only after user approval; real Controlled Execution not started

**Phase 1G-04-18 is completed locally.** Confirmation Token Issuance / Verification Scope Freeze.
- `docs/webui/phase-1g-04-18-confirmation-token-scope.md` — Confirmation token issuance / verification scope freeze: token goal (short-lived, single-use, dev-only approval artifact, necessary but never sufficient), issuance source (only after successful dry-run with would_allow + auditWritten + allowlisted; preferred Option A extend dry-run response over Option B new endpoint), binding contract (11 fields: dryRunRequestId, dryRunDecisionDigest, canonicalName, riskTier, policyVersion, auditEventId, argumentsDigest, redactionVersion, issuedAt, expiresAt, nonce), payload strategy (raw token = base64url random 256-bit, opaque no JSON claims), hash strategy (HMAC-SHA256 or SHA-256 of raw token, never store raw token), token store strategy (dev-only file-backed JSONL at $HERMES_HOME/gateway/dev/tokens/confirmation-tokens.jsonl, forbidden: ~/.hermes/production state.db/repo/frontend/provider logs), TTL (≤ 5 min, expiresAt ≤ dry-run expiresAt, expired blocks before digest verification), single-use (consumed before pre-execution audit readiness, reused blocks with confirmation_reused), verification gate order (29 gates frozen: Gates 1-13 existing + Gates 14-29 new token gates), failure contract (15 error codes, all block before handler lookup, all keep side-effect flags false), audit strategy (record tokenId/tokenHash prefix/binding fields, never raw token/secrets/arguments), digest verification boundary (token verification ≠ digest verification, separate concerns), execute route behavior delta (token implementation does not imply real execution, route may remain blocked), route governance strategy (no count change, 33/33/4/0/1/1), future OpenAPI (no path change, may refine existing schemas), future allowed files (14 files), future forbidden files (15 categories), future test matrix (36 tests), entry criteria (15 conditions), exit criteria (20 conditions)
- Confirmation token issuance scope frozen; confirmation token verification scope frozen; token storage scope frozen; token TTL scope frozen; token single-use scope frozen; token binding contract frozen; token verification gate order frozen; token failure contract frozen; token audit strategy frozen
- NOT implemented: confirmation token issuance/verification, token store, digest verification, pre/post execution audit, execute route behavior change, OpenAPI change, new route, Tool Handler call, Provider Schema send, STATIC_ALLOWLIST change, frontend, audit read API, audit viewer, real Controlled Execution
- STATIC_ALLOWLIST remains `frozenset({"clarify"})`; Execute route remains blocked-only
- Route governance: OpenAPI=33, Runtime=33, Tool GET=4, Tool write=0, Tool dry-run=1, Tool execution=1 (unchanged)
- Docs-only, no code changes, no OpenAPI file changes, no route changes, no frontend changes, no test changes
- Local docs-only commit created, not pushed
- Next = future confirmation token issuance / verification implementation only after user approval; real Controlled Execution not started

**Phase 1G-04-19 is completed locally.** Confirmation Token Minimal Backend Implementation Scope Freeze.
- `docs/webui/phase-1g-04-19-confirmation-token-implementation-scope.md` — Confirmation token minimal backend implementation scope freeze: future module boundary (`dev_web_tool_execute_confirmation.py`, 15 responsibilities, 14 prohibitions), future issuance helper scope (`issue_confirmation_token()`, 16 responsibilities, never stores raw token), future verification helper scope (`verify_confirmation_token()`, 22 responsibilities, never exposes raw token/tokenHash), future token store scope (`$HERMES_HOME/gateway/dev/tokens/confirmation-tokens.jsonl`, 7 path guard rules, 4 prohibitions), future token hash/tokenId scope (HMAC-SHA256 preferred, SHA-256 fallback with documented limitation), future TTL scope (≤ 5 min, expiresAt ≤ dry-run expiresAt, missing fails closed), future single-use scope (recommended append-only JSONL event model Option A), future execute route token integration (gates 15–30, valid token still blocks at gates 28–30), future failure contract (16 error codes, all block before handler lookup), future route governance (no route change, 33/33/4/0/1/1), future allowed files (14 files), future forbidden files (16 categories), future test matrix (43 tests: 14 issuance, 14 verification, 10 safety, 5 governance), entry criteria (13 conditions), exit criteria (25 conditions)
- Minimal backend implementation boundary frozen; future module boundary frozen; future issuance helper scope frozen; future verification helper scope frozen; future token store scope frozen; future token hash/tokenId scope frozen; future TTL scope frozen; future single-use scope frozen; future execute route integration scope frozen; future failure contract frozen; future test matrix frozen
- NOT implemented: confirmation token issuance/verification, token store, token hash, token TTL, token single-use consumption, digest verification, pre/post execution audit, execute route behavior change, OpenAPI change, new route, Tool Handler call, Provider Schema send, STATIC_ALLOWLIST change, frontend, audit read API, audit viewer, real Controlled Execution
- STATIC_ALLOWLIST remains `frozenset({"clarify"})`; Execute route remains blocked-only
- Route governance: OpenAPI=33, Runtime=33, Tool GET=4, Tool write=0, Tool dry-run=1, Tool execution=1 (unchanged)
- Docs-only, no code changes, no OpenAPI file changes, no route changes, no frontend changes, no test changes
- Local docs-only commit created, not pushed
- Next = future minimal confirmation token backend implementation only after user approval; real Controlled Execution not started

**Phase 1G-04-20 is completed locally.** Confirmation Token Minimal Backend Implementation / Still Blocked-Only.
- `hermes_cli/dev_web_tool_execute_confirmation.py` — New confirmation token module: `issue_confirmation_token()`, `verify_confirmation_token()`, `ConfirmationTokenIssueResult`, `ConfirmationTokenVerificationResult`, dev-only token JSONL store, HMAC-SHA256 token hashing, tokenId derivation, TTL ≤ 5 min, single-use consumption, path containment guard
- `hermes_cli/dev_web_tool_execute.py` — Execute route token verification gate (Gates 15–27), digest verification boundary block (Gate 28), new error codes (confirmation_*, digest_verification_not_implemented)
- `hermes_cli/dev_web_api.py` — Dry-run token issuance integration (issueConfirmationToken flag), token returned in response when eligible
- `docs/webui/openapi/dev-web-api-v1.yaml` — Schema-only: issueConfirmationToken in ToolDryRunRequest, confirmationToken/confirmationTokenId/confirmationTokenExpiresAt in ToolDryRunData, new error codes and decisions
- `tests/test_dev_web_tool_execute_confirmation.py` — 50 new tests: issuance (15), verification (16), safety invariants (7), path guard (5), hash/ID (7)
- `tests/test_dev_web_tool_execute.py` — Updated 3 tests + 2 new tests for valid-token-still-blocks and token-reuse
- Valid token passes verification but execute still blocks at digest verification boundary
- NOT implemented: digest verification, pre/post execution audit, handler lookup, dispatch, execution, Provider Schema/API, frontend, audit read API, audit viewer, real Controlled Execution
- STATIC_ALLOWLIST remains `frozenset({"clarify"})`; Execute route remains blocked-only
- Route governance: OpenAPI=33, Runtime=33, Tool GET=4, Tool write=0, Tool dry-run=1, Tool execution=1 (unchanged)
- Local commit created, not pushed
- Next = digest verification or pre-execution audit scope only after user approval; real Controlled Execution not started

**Phase 1G-04-21 is completed locally.** Digest Verification Scope Freeze.
- `docs/webui/phase-1g-04-21-digest-verification-scope.md` — Digest verification scope freeze: digest goal (verify execute matches dry-run decision package, necessary but not sufficient, passing does not execute), digest input package (14-field canonical package), canonicalization strategy (sorted JSON, UTF-8, no whitespace, no secrets), digest algorithm (`sha256:` + hex), source-of-truth strategy (dry-run audit JSONL primary, token store secondary), current `dryRunDecisionDigest` gap (not yet stored in audit events, token binding may be None), confirmation token + digest relationship (both required, neither sufficient), future dry-run behavior delta (may add dryRunDecisionDigest/digestAlgorithm/digestPackageVersion to response and audit event), future execute digest gate order (Gates 28–37), failure contract (14 error codes, all block before handler lookup), OpenAPI schema-only strategy (no path change), route governance strategy (33/33/4/0/1/1 maintained), future allowed files (1 new module + 7 backend + 1 OpenAPI + 10 tests + 3 docs), future forbidden files (frontend, agent, tools, toolsets, runtime, memory, review, .env, .claude, ~/.hermes, production), future test matrix (51 tests: 14 digest package, 8 dry-run digest, 5 token binding, 11 execute gates, 8 safety invariants, 5 route governance), entry criteria (13 conditions), exit criteria (22 conditions)
- Digest verification goal frozen; digest input package frozen; canonicalization strategy frozen; digest algorithm frozen; source-of-truth strategy frozen; current dryRunDecisionDigest gap documented; confirmation token relationship frozen; future dry-run behavior delta frozen; future execute digest gate order frozen; failure contract frozen; OpenAPI strategy frozen; route governance frozen; future allowed/forbidden files frozen; future test matrix frozen; entry/exit criteria frozen
- NOT implemented: digest verification, dry-run digest persistence, pre/post execution audit, handler lookup, dispatch, execution, Provider Schema/API, frontend, audit read API, audit viewer, real Controlled Execution
- STATIC_ALLOWLIST remains `frozenset({"clarify"})`; Execute route remains blocked-only
- Route governance: OpenAPI=33, Runtime=33, Tool GET=4, Tool write=0, Tool dry-run=1, Tool execution=1 (unchanged)
- Docs-only, no code changes, no OpenAPI file changes, no route changes, no frontend changes, no test changes
- Local docs-only commit created, not pushed
- Next = future digest verification minimal implementation only after user approval; real Controlled Execution not started

**Phase 1G-04-22 is completed locally.** Digest Verification Minimal Implementation / Still Blocked-Only.
- `docs/webui/phase-1g-04-22-digest-verification-minimal-implementation.md` — Digest verification minimal implementation
- `hermes_cli/dev_web_tool_execute_digest.py` — New digest module: canonical digest package builder, canonicalization, SHA-256 hex computation, multi-source verification
- Digest package builder implemented; canonicalization implemented (`json-sort-v1`); digest algorithm `sha256:hex` implemented
- `dryRunDecisionDigest` generated during dry-run; persisted in dry-run audit events; returned in dry-run response
- Confirmation token issuance requires non-null `dryRunDecisionDigest`; legacy null-digest tokens fail closed
- Execute route digest verification gates (28–37) implemented; valid token + valid digest blocks at `blocked_pre_execution_audit_not_implemented`
- OpenAPI schema-only updates (new digest fields, error codes, decisions); OpenAPI paths remain 33
- NOT implemented: pre-execution audit, post-execution audit, handler lookup, dispatch, execution, Provider Schema/API, frontend, audit read API, audit viewer, real Controlled Execution
- STATIC_ALLOWLIST remains `frozenset({"clarify"})`; Execute route remains blocked-only
- Route governance: OpenAPI=33, Runtime=33, Tool GET=4, Tool write=0, Tool dry-run=1, Tool execution=1 (unchanged)
- Local commit created, not pushed
- Next = pre-execution audit scope freeze only after user approval; real Controlled Execution not started

**Phase 1G-04-23 is completed locally.** Pre-Execution Audit Scope Freeze.
- `docs/webui/phase-1g-04-23-pre-execution-audit-scope.md` — Pre-execution audit scope freeze
- Pre-execution audit goal frozen (durable record before handler lookup, necessary but not sufficient)
- Difference from dry-run audit frozen (execute attempt record vs. policy simulation)
- Confirmation token relationship frozen (references confirmationTokenId, timestamps, dryRunRequestId)
- Digest verification relationship frozen (references dryRunDecisionDigest, historical/token-bound/execute-derived digests)
- Handler lookup relationship frozen (pre-audit is final record before future handler lookup)
- Write timing frozen (after all gates pass, before handler lookup / dispatch / execution)
- Event structure frozen (30+ field structure with gate status and side-effect flags)
- Audit store path frozen (`$HERMES_HOME/gateway/dev/audit/tool-pre-execution-audit.jsonl`)
- Path guard strategy frozen (containment-based, not string prefix)
- ID strategy frozen (`pea_` / `exe_` prefixes, safe for correlation, not authorization credentials)
- Idempotency strategy frozen (append-only, single-use token natural dedup)
- Failure contract frozen (8 error codes, all block before handler lookup)
- Success contract frozen (audit written but still blocked at `blocked_handler_lookup_not_enabled`)
- Future execute gate order frozen (Gates 38–45)
- Future OpenAPI strategy frozen (schema-only, no new paths)
- Future route governance frozen (unchanged 33/33/4/0/1/1)
- Future allowed/forbidden files frozen
- Future test matrix frozen (55 tests)
- Entry/exit criteria frozen
- NOT implemented: pre-execution audit, post-execution audit, handler lookup, dispatch, execution, Provider Schema/API, frontend, audit read API, audit viewer, real Controlled Execution
- STATIC_ALLOWLIST remains `frozenset({"clarify"})`; Execute route remains blocked-only
- Route governance: OpenAPI=33, Runtime=33, Tool GET=4, Tool write=0, Tool dry-run=1, Tool execution=1 (unchanged)
- Docs-only, no code changes, no OpenAPI file changes, no route changes, no frontend changes, no test changes
- Local docs-only commit created, not pushed
- Next = future pre-execution audit minimal implementation only after user approval; real Controlled Execution not started

**Phase 1G-04-24 is completed locally.** Pre-Execution Audit Minimal Implementation / Still Blocked-Only.
- Pre-execution audit module implemented: audit package builder, containment-based path guard, preExecutionAuditId, executeRequestId
- Audit store path: `$HERMES_HOME/gateway/dev/audit/tool-pre-execution-audit.jsonl` (dev-only, local-only)
- Execute route audit gates (38–45) implemented: valid token + valid digest + audit written blocks at `blocked_handler_lookup_not_enabled`
- STATIC_ALLOWLIST remains `frozenset({"clarify"})`; Execute route remains blocked-only
- Route governance: OpenAPI=33, Runtime=33, Tool GET=4, Tool write=0, Tool dry-run=1, Tool execution=1 (unchanged)
- NOT implemented: post-execution audit, handler lookup, dispatch, execution, Provider Schema/API, frontend, audit read API, audit viewer, real Controlled Execution
- Local commit created, not pushed
- Next = future handler lookup audit or controlled execution scope only after user approval; real Controlled Execution not started

**Phase 1G-04-25 is completed locally.** Handler Lookup Scope Freeze.

**Phase 1G-04-26 is completed locally.** Handler Lookup Minimal Implementation / Still Blocked-Only. Safe handler descriptor lookup, handlerLookupId generation, execute route handler lookup gates 46–56 implemented. Execute remains blocked-only at `blocked_dispatch_not_enabled`. STATIC_ALLOWLIST remains `frozenset({"clarify"})`. No Tool Handler call, dispatch, execution, post-execution audit, Provider Schema sending, or Provider API call. Real Controlled Execution not started. Not pushed.
- `docs/webui/phase-1g-04-25-handler-lookup-scope.md` — Handler lookup scope freeze: handler lookup goal (resolve safe handler descriptor for approved/audited/allowlisted canonicalName, necessary but not sufficient), why handler lookup is not execution, relationship with pre-execution audit, relationship with STATIC_ALLOWLIST, relationship with tool registry / catalog, handler descriptor structure (12 safe fields, excludes raw arguments/token/credentials), handler lookup ID strategy (`hl_` prefix, correlation-only), lookup timing (after all 45 prior gates + explicit enable gate), failure contract (10 error codes), success contract (still blocks at `blocked_dispatch_not_enabled`), future execute gate order (Gates 46–56), future OpenAPI schema-only strategy, future route governance strategy (33/33/4/0/1/1 maintained), future allowed files, future forbidden files, future test matrix (47 tests), stale STATIC_ALLOWLIST assertion observation, entry criteria (14 conditions), exit criteria (18 conditions)
- NOT implemented: handler lookup, handler registry adapter, Tool Handler call, dispatch, execution, post-execution audit, Provider Schema/API, frontend execute UI, audit read API, audit viewer, real Controlled Execution
- STATIC_ALLOWLIST remains `frozenset({"clarify"})`; Execute route remains blocked-only
- Route governance: OpenAPI=33, Runtime=33, Tool GET=4, Tool write=0, Tool dry-run=1, Tool execution=1 (unchanged)
- Docs-only, no code changes, no OpenAPI file changes, no route changes, no frontend changes, no test changes
- Local docs-only commit created, not pushed
- Next = future handler lookup minimal implementation only after user approval; real Controlled Execution not started

**Phase 1G-04-27 is completed locally.** Dispatch Scope Freeze.
- `docs/webui/phase-1g-04-27-dispatch-scope.md` — Dispatch scope freeze: dispatch goal (safe dispatch plan / envelope for an already verified, audited, allowlisted, handler-resolved canonicalName; necessary but not sufficient), why dispatch is still not a Tool Handler call, why dispatch is still not execution, relationship with handler lookup, relationship with pre-execution audit, relationship with STATIC_ALLOWLIST, relationship with handler descriptor, relationship with future Tool Handler call, dispatch plan / dispatch envelope structure (dispatchStatus, dispatchId, dispatchPlan with dispatchAllowed=false / toolHandlerCallAllowed=false / executionAllowed=false / providerSchemaAllowed=false / sideEffectFreeDispatch=true), dispatch input (already-verified gate context, not raw arguments), dispatch output (safe metadata only), dispatch ID strategy (`dsp_` prefix, correlation-only), dispatch timing (after kill switch + allowlist + dry-run lookup + dry-run binding + token verification + token consumed + digest verification + pre-execution audit + handler lookup + explicit dispatch enable gate), failure contract (12 error codes, all block before a Tool Handler call), success contract (still blocks at `blocked_tool_handler_call_not_enabled`), future execute gate order (Gates 57–69), future OpenAPI schema-only strategy (no path change), future route governance strategy (33/33/4/0/1/1 maintained), future allowed files (1 new dispatch module + 8 existing backend + 1 OpenAPI + 10 tests + 3 docs), future forbidden files (frontend, agent, tools, toolsets, runtime, memory, review, .env, .claude, ~/.hermes, production state.db, provider config, gateway state, runtime audit JSONL), future test matrix (58 tests), stale STATIC_ALLOWLIST assertion observation, entry criteria (15 conditions), exit criteria (16 conditions)
- Dispatch future boundary frozen; dispatch plan / envelope structure frozen; dispatch input/output frozen; dispatch ID strategy frozen; dispatch failure / success contract frozen; future execute gate order frozen; future OpenAPI schema-only strategy frozen; future route governance frozen (33/33/4/0/1/1)
- NOT implemented: dispatch, dispatch adapter, dispatch envelope runtime module, Tool Handler call, Tool Dispatch, Tool Execution, post-execution audit, Provider Schema/API, frontend execute UI, audit read API, audit viewer, real Controlled Execution
- STATIC_ALLOWLIST remains `frozenset({"clarify"})`; Execute route remains blocked-only
- Route governance: OpenAPI=33, Runtime=33, Tool GET=4, Tool write=0, Tool dry-run=1, Tool execution=1 (unchanged)
- Docs-only, no code changes, no OpenAPI file changes, no route changes, no frontend changes, no test changes
- Local docs-only commit created, not pushed
- Next = future dispatch minimal implementation only after user approval; real Controlled Execution not started

**Phase 1G-04-28 is completed locally.** Dispatch Minimal Implementation / Still Blocked-Only.
- `docs/webui/phase-1g-04-28-dispatch-minimal-implementation.md` — Dispatch minimal implementation: new `hermes_cli/dev_web_tool_dispatch.py` module (DispatchPlan, DispatchResult, build_dispatch_plan, create_dispatch_plan, validate_dispatch_plan, generate_dispatch_id, safe_dispatch_summary), safe metadata-only dispatch plan / envelope builder, `dsp_` dispatchId generation, dispatch plan validation (canonicalName / handler descriptor consistency / registry consistency / allowlist / policy metadata / side-effect-free metadata only), execute route dispatch gates 57–69, dispatch success contract (still blocks at `blocked_tool_handler_call_not_enabled`), dispatch failure contract (fail-closed before Tool Handler call), OpenAPI schema-only updates (ToolExecuteData.dispatchId/dispatchStatus/dispatchPlan + ToolDispatchPlan schema + dispatch_* / tool_handler_call_not_enabled error and decision enums), backend tests (new test_dev_web_tool_dispatch.py + execute integration updates)
- A valid token plus a valid digest plus a successful pre-execution audit plus a successful handler lookup plus a successful dispatch plan now pass the confirmation, digest, pre-execution audit, handler lookup, and dispatch planning gates, but execute STILL blocks at the Tool Handler call boundary (`blocked_tool_handler_call_not_enabled`)
- NOT implemented: Tool Handler call, dispatch runtime invocation, tool execution, post-execution audit, Provider Schema sending, Provider API call, frontend execute UI, audit read API, audit viewer, real Controlled Execution
- STATIC_ALLOWLIST remains `frozenset({"clarify"})`; Execute route remains blocked-only
- Route governance: OpenAPI=33, Runtime=33, Tool GET=4, Tool write=0, Tool dry-run=1, Tool execution=1 (unchanged)
- No new route, no route count change, no OpenAPI path change, no frontend change, no agent/tools change
- Local commit created, not pushed
- Next = Tool Handler Call Scope Freeze only after user approval; real Controlled Execution not started
---

## Phase 1G-04-30 — Accelerated WebUI Closeout (completed locally / not pushed)

**Phase 1G-04-30 is completed locally.** Accelerated WebUI Closeout.

- `docs/webui/phase-1g-04-30-accelerated-webui-closeout.md` — read-only audit events API (`GET /api/dev/v1/tools/audit-events`) + safe audit JSONL reader with redaction/path-containment + frontend Execute UI (clarify-only controlled execution workbench) + Audit Viewer + frontend API client + browser smoke/E2E (both default-block and completed scenarios) + OpenAPI update + route governance transition.
- Route governance: OpenAPI=34, Runtime=34, Tool GET=5, Tool write=0, Tool dry-run=1, Tool execution=1. Exactly one new read-only GET route added.
- STATIC_ALLOWLIST remains `frozenset({"clarify"})`. No Tool write route, no second execution route, no Provider route.
- Audit read API is read-only; dev HERMES_HOME only; production `~/.hermes` and `state.db` blocked; missing file → empty items; malformed lines skipped safely; raw token / full tokenHash / raw arguments / secrets / callable / function repr / provider payload never exposed.
- Frontend Execute UI: clarify-only; default gate unset → `blocked_tool_handler_call_not_enabled`; explicit dev/test gate → `clarify_execution_completed` with `postExecutionAuditId` and false Provider side-effect flags. Raw confirmation token held in-memory only (never persisted / logged / rendered).
- Digest-binding fix in the dry-run route (`hermes_cli/dev_web_api.py`): the real dry-run endpoint now computes `dryRunDecisionDigest` bound to the real audit `eventId` / timestamp / expiry, matching the execute gate's recomputation — the end-to-end dry-run → execute chain now works (previously returned `blocked_digest_mismatch`; backend unit tests used synthetic events so did not catch it).
- Browser smoke: completed scenario 7 passed; blocked scenario 6 passed + 1 skipped. Servers isolated to 127.0.0.1, torn down after; production Gateway PID 69355 unaffected; 5180/5181 free.
- Backend regression 1471 passed; frontend vitest 670 passed; frontend build / type-check / lint pass; memory-check PASS; dev-check PASS (only dirty-worktree WARN).
- No Provider Schema sent, no Provider API called, no non-clarify execution, no production access.
- Local commit created, not pushed.
- Next = Phase 1G-04-31 (final sealing / push) only after user approval; not started.

---

## Phase 1G-04-31 — Final WebUI Sealing (sealed and pushed)

**Phase 1G-04-31 is sealed.** Phase 1G-04 WebUI mainline is sealed.

- `docs/webui/phase-1g-04-31-final-webui-sealing.md` — final sealing report: phase definition, baseline HEAD, completed backend chain (dry-run lookup → confirmation token → digest verification → pre-execution audit → handler lookup → dispatch planning → clarify-only handler call → post-execution audit → read-only audit events API), completed frontend chain (Execute UI + Audit Viewer + in-memory raw-token handling), route governance final state, security boundary, browser smoke summary, backend regression summary, frontend quality summary, production isolation summary, P0/P1/P2 risk list, acceptance checklist, final push criteria.
- `docs/webui/phase-1g-04-final-acceptance-report.md` — consolidated acceptance for Phase 1G-04-20 → 1G-04-31, with the full capability table, final security boundaries, final verification results, and P2/known-limitation list.
- **Phase 1G-04 WebUI mainline = SEALED.**
- Final route governance = OpenAPI=34, Runtime=34, Tool GET=5, Tool write=0, Tool dry-run=1, Tool execution=1 (unchanged from 1G-04-30).
- STATIC_ALLOWLIST remains `frozenset({"clarify"})`.
- Production Gateway PID baseline = `69355` (unaffected).
- No P0, No P1.
- Remaining P2: stale `auditWritten=false` assumption in the dormant `phase-1g-04-dry-run-api-safety-smoke.spec.ts` (historical, not in any active runner); offset-based audit pagination; multi-file JSONL rotation / race handling future work; non-clarify tools disabled by design; Provider integration permanent non-goal; frontend visual polish optional.
- Final verification: backend regression 1471 passed / 2 skipped / 5 deselected / 0 failed; frontend type-check + lint + vitest 674 passed + build pass; browser smoke blocked scenario 6 passed + 1 skipped / completed scenario 7 passed; memory-check PASS; dev-check WARN (only `.claude/` dirty); compileall + toolsets + ruff pass; production Gateway PID 69355 unchanged; 5180/5181 free.
- No new route, no allowlist change, no Provider, no non-clarify execution, no Tool write route, no production access, no audit JSONL commit, no `.claude/` commit.
- Docs-only sealing commit created and pushed.
- Next = post-sealing polish only, not required for Phase 1G-04 acceptance.

---

## Phase 1G-05 — Post-Sealing Readiness (pushed)

**Phase 1G-05 is pushed** at `da5c31a8c`. Post-Sealing Readiness & Pilot Acceptance Baseline.

- **Phase 1G-04 remains SEALED.** Phase 1G-05 does **not** reopen Phase 1G-04 and does **not** add functionality. It prepares Pilot / release readiness only.
- Purpose: establish the post-sealing readiness baseline, Pilot acceptance baseline, release checklist, ops / rollback runbook, and P2 risk register for the sealed Phase 1G-04 WebUI mainline.
- Deliverables (all docs-only):
  - `docs/webui/phase-1g-05-post-sealing-readiness.md` — Phase 1G-05 definition, Phase 1G-04 sealed baseline (HEAD `94f22f67b`), route governance, allowlist, controlled-execution chain, default vs explicit gate behavior, readiness checklist, invariants, follow-on phase entry points, non-reopening declaration.
  - `docs/webui/phase-1g-05-pilot-acceptance-baseline.md` — 14 Pilot scenarios (A–N) with preconditions / steps / expected result / security assertion / pass-fail / severity (P0/P1/P2), two gate configurations (blocked + completed), pass criteria, reporting.
  - `docs/webui/phase-1g-05-release-checklist.md` — 34 pre-release items with copy-pasteable commands (git, route governance, kill switches, production isolation, backend regression, compileall, ruff, frontend typecheck/lint/unit/build, browser smoke, memory-check, dev-check, forbidden-file + secret scan, rollback plan, go/no-go).
  - `docs/webui/phase-1g-05-ops-and-rollback-runbook.md` — dev `HERMES_HOME`, production `~/.hermes` prohibition, production Gateway PID check, Dev/WebUI server start/stop, browser smoke runbook, log + audit JSONL locations, safe cleanup, revert-based rollback (no reset / force / production mutation), blocked-execution / audit-viewer / digest-mismatch / port-conflict / provider-disabled troubleshooting, emergency stop conditions.
  - `docs/webui/phase-1g-05-risk-register.md` — 0 P0, 0 P1, 8 P2 (stale dormant `auditWritten=false` assumption; offset-based audit pagination; multi-file JSONL rotation; JSONL race handling; non-clarify disabled by design; Provider permanent non-goal; frontend visual polish optional; large-scale audit search/index).
- No route governance change. Route governance remains OpenAPI=34, Runtime=34, Tool GET=5, Tool write=0, Tool dry-run=1, Tool execution=1.
- No allowlist change. `STATIC_ALLOWLIST` remains `frozenset({"clarify"})`.
- No code feature expansion. No new route, no Tool write route, no second execution route, no Provider route, no non-clarify execution, no Provider Schema / API.
- No production `~/.hermes` access; no production `state.db` access; production Gateway PID `69355` unaffected.
- Local docs-only commit created, then pushed (`da5c31a8c`).
- Next = Pilot execution (optional, pending explicit approval); Phase 1G-06 explicitly **not started** (at the time of authoring).

## Phase 1G-06 — Pilot Release Rehearsal / Smoke Harness Hardening (pushed)

**Phase 1G-06 is pushed** at `311221e0d`. Pilot Release Rehearsal & Smoke Harness Hardening.

- **Phase 1G-04 remains SEALED.** **Phase 1G-05 remains the pushed readiness baseline.** Phase 1G-06 does **not** reopen Phase 1G-04 and does **not** introduce any new product capability. It hardens release rehearsal and smoke execution only.
- Purpose: convert the Phase 1G-05 readiness into a repeatable release rehearsal baseline — fixate the execute/audit browser smoke as a committed harness, define the gate profiles precisely, and establish a go/no-go template.
- Gate profiles (the `blocked_tool_handler_call_not_enabled` vs `clarify_execution_completed` distinction is the key correction recorded this phase): Profile A (upstream execution gates on, handler-call gate unset → `blocked_tool_handler_call_not_enabled`); Profile B (all three gates `=true` → `clarify_execution_completed`); optional Profile C (all gates unset → `blocked_by_kill_switch`). Unsetting all gates tests `blocked_by_kill_switch`, **not** `blocked_tool_handler_call_not_enabled`.
- Deliverables (docs + one dev-only script):
  - `docs/webui/phase-1g-06-pilot-release-rehearsal.md` — Phase 1G-06 definition, Phase 1G-04 sealed + Phase 1G-05 pushed baselines, route governance, release rehearsal goal, gate profiles A/B/C, Pilot rehearsal checklist, release-candidate validation checklist, smoke commands, go/no-go, known P2, exit criteria, next-phase options, non-reopening declaration.
  - `docs/webui/phase-1g-06-smoke-harness-runbook.md` — exact env vars + exact commands per profile, expected UI/API/audit-viewer results, side-effect flags, the common-mistake note, troubleshooting, cleanup, final port + production PID checks.
  - `docs/webui/phase-1g-06-release-candidate-validation.md` — actual observed rehearsal gate results (git baseline, route governance, backend regression 1471 passed / 2 skipped / 0 failed, compile/ruff, frontend type-check/lint/674 unit/build, smoke A 6 passed / 1 skipped / 0 failed, smoke B 7 passed / 0 failed, memory-check, dev-check, production PID `69355` unchanged, final ports free, GO).
  - `docs/webui/phase-1g-06-go-no-go-template.md` — reusable copy-per-release go/no-go record (candidate ID, branch, HEAD, route governance, smoke, backend, frontend, production safety, P0/P1/P2, decision, approver, rollback note, next action, emergency stop conditions).
  - `scripts/run-dev-webui-execute-audit-smoke.sh` — committed dev-only, 127.0.0.1-only, self-cleaning smoke harness replacing the ad-hoc `/tmp` harness; refuses production `HERMES_HOME`; port-precheck; kill-only-started-PIDs; supports `blocked` / `completed` / `all` profiles; prints gate profile, ports, PIDs, production PID, and result summary.
- No route governance change. Route governance remains OpenAPI=34, Runtime=34, Tool GET=5, Tool write=0, Tool dry-run=1, Tool execution=1.
- No allowlist change. `STATIC_ALLOWLIST` remains `frozenset({"clarify"})`.
- No code feature expansion. No new route, no Tool write route, no second execution route, no Provider route, no non-clarify execution, no Provider Schema / API. No backend functional code change (no P0/P1 defect required a fix).
- No production `~/.hermes` access; no production `state.db` access; production Gateway PID `69355` unaffected; ports `5180` / `5181` free throughout.
- Local commit created, then pushed (`311221e0d`).
- Next = Pilot execution (optional, pending explicit approval); Phase 1G-07 (Release Candidate Dry Run) completed locally — see below.

## Phase 1G-07 — Release Candidate Dry Run (pushed)

**Phase 1G-07 is pushed** at `6f9176953`. Release Candidate Dry Run. RC ID: `RC-1G-07-001`.

- **Phase 1G-04 remains SEALED.** **Phase 1G-05 remains the pushed readiness baseline.** **Phase 1G-06 remains the pushed release rehearsal baseline.** Phase 1G-07 does **not** reopen Phase 1G-04 and does **not** introduce any new product capability. It validates release-candidate readiness only.
- Purpose: execute a formal Release Candidate Dry Run against the current `dev-huangruibang` branch and decide whether it is eligible to enter Pilot acceptance.
- Deliverables (docs-only):
  - `docs/webui/phase-1g-07-release-candidate-dry-run.md` — Phase 1G-07 definition, RC ID (`RC-1G-07-001`), Phase 1G-04 sealed + Phase 1G-05 pushed + Phase 1G-06 pushed baselines, route governance, RC dry-run goal, validation scope, non-goals, smoke profiles A/B/C, backend / frontend / production-isolation / security-boundary validation, Go / No-Go criteria, exit criteria, next-phase options, non-reopening declaration.
  - `docs/webui/phase-1g-07-rc-validation-report.md` — actual observed RC dry-run gate results (git baseline, route governance 34 / 34 / 5 / 0 / 1 / 1, backend route governance 124 passed / 0 failed, related backend regression 19 files 1471 passed / 0 failed, compile / `py_compile toolsets.py` / ruff, frontend type-check / lint 0-0 / 674 unit / 1862-module build, smoke A 6 passed / 1 skipped / 0 failed, smoke B 7 passed / 0 failed, memory-check PASS, dev-check WARN only for `.claude/`, production PID `69355` unchanged, final ports free, GO).
  - `docs/webui/phase-1g-07-go-no-go-decision.md` — filled go / no-go record for `RC-1G-07-001` (candidate ID, branch, HEAD, route governance, smoke, backend, frontend, production safety, security boundary, P0/P1/P2 = 0 / 0 / 8, **Decision: GO**, approver, rollback note, next action, emergency stop conditions).
- No route governance change. Route governance remains OpenAPI=34, Runtime=34, Tool GET=5, Tool write=0, Tool dry-run=1, Tool execution=1.
- No allowlist change. `STATIC_ALLOWLIST` remains `frozenset({"clarify"})`.
- No code feature expansion. No new route, no Tool write route, no second execution route, no Provider route, no non-clarify execution, no Provider Schema / API. No backend functional code change.
- No production `~/.hermes` access (no `ls` / `stat` / `find` / `cat` / `sqlite3` / `du` / mtime); no production `state.db` access; production Gateway PID `69355` unaffected; ports `5180` / `5181` free throughout and after.
- Local docs-only commit created, then pushed (`6f9176953`).
- Next = Pilot execution (optional, pending explicit approval); Phase 1G-08 (Pilot Acceptance Preparation) completed locally — see below.

## Phase 1G-08 — Pilot Acceptance Preparation (pushed)

**Phase 1G-08 is pushed** at `9812c069e`. Pilot Acceptance Preparation. Pilot Acceptance ID: `PILOT-1G-08-001`.

- **Phase 1G-04 remains SEALED.** **Phase 1G-05 remains the pushed readiness baseline.** **Phase 1G-06 remains the pushed release rehearsal baseline.** **Phase 1G-07 remains the pushed GO RC dry run.** Phase 1G-08 does **not** reopen Phase 1G-04 and does **not** introduce any new product capability. It prepares Pilot acceptance execution only.
- Purpose: convert the `RC-1G-07-001` GO decision into an executable Pilot acceptance preparation pack so a Pilot operator / participant can run `PILOT-1G-08-001` against the sealed mainline with a fixed scenario list, evidence rules, defect / feedback scheme, and PASS / NO-GO / PAUSED exit criteria.
- Deliverables (docs-only):
  - `docs/webui/phase-1g-08-pilot-acceptance-preparation.md` — Phase 1G-08 definition, Pilot Acceptance ID (`PILOT-1G-08-001`), Phase 1G-04 sealed + Phase 1G-05 / 1G-06 / 1G-07 pushed baselines, route governance, Pilot preparation goal, scope, non-goals, participating roles, process, preconditions, execution order, recording / defect / pause-rollback / exit rules, next-phase options, non-reopening declaration.
  - `docs/webui/phase-1g-08-pilot-acceptance-pack.md` — the ready-to-run Pilot pack: ID, scope, out-of-scope, environment, safety boundary, commands, evidence, 15 scenarios (A–O) with objective / preconditions / steps / expected / evidence / pass / fail / severity, run matrix, screenshots / log-summary rules, pass / fail criteria, known P2, Go/No-Go relation, completion checklist.
  - `docs/webui/phase-1g-08-pilot-operator-guide.md` — operator responsibilities, before/after checklists, environment setup, git / PID / port checks, backend / frontend / smoke validation, evidence + defect recording, failure handling, pause / rollback / no-go rules, forbidden actions, quick-reference commands.
  - `docs/webui/phase-1g-08-pilot-participant-guide.md` — non-technical instructions: Pilot purpose, what to do / not do, how to observe the WebUI, how to report / reproduce, blocker / major / minor distinction, when to stop, what not to provide, worked feedback examples.
  - `docs/webui/phase-1g-08-pilot-acceptance-record-template.md` — copy-fill Pilot record (header + per-scenario A–O status / actual / evidence / defect / severity / notes, evidence index, defects index, decision, sign-off).
  - `docs/webui/phase-1g-08-pilot-defect-feedback-template.md` — copy-fill defect / feedback record (severity P0 / P1 / P2, categories, triage rules, worked examples).
  - `docs/webui/phase-1g-08-pilot-exit-criteria.md` — PASS / NO-GO / PAUSED conditions, P0 / P1 / P2 handling, Phase 1G-09 entry rule, Pilot execution entry rule, supplemental RC rule, rollback rule, evidence + sign-off requirements, emergency stop conditions.
- No route governance change. Route governance remains OpenAPI=34, Runtime=34, Tool GET=5, Tool write=0, Tool dry-run=1, Tool execution=1.
- No allowlist change. `STATIC_ALLOWLIST` remains `frozenset({"clarify"})`.
- No code feature expansion. No new route, no Tool write route, no second execution route, no Provider route, no non-clarify execution, no Provider Schema / API. No backend functional code change.
- No production `~/.hermes` access (no `ls` / `stat` / `find` / `cat` / `sqlite3` / `du` / mtime); no production `state.db` access; production Gateway PID `69355` unaffected; ports `5180` / `5181` free throughout and after.
- Final re-verification: route governance 124 passed / 0 failed; related backend regression 19 files 1471 passed / 0 failed; compile / `py_compile toolsets.py` / ruff clean; frontend type-check / lint 0-0 / unit / build pass; smoke A 6 passed / 1 skipped / 0 failed; smoke B 7 passed / 0 failed; memory-check PASS; dev-check WARN only for `.claude/`; Production Gateway PID `69355` unchanged; ports `5180` / `5181` free.
- Local docs-only commit created, then **pushed** at `9812c069e` (`docs(webui): add phase 1g-08 pilot acceptance pack`).
- Next = Pilot execution (performed in Phase 1G-09); Phase 1G-09 performed the Pilot acceptance execution (see below).

---

## Phase 1G-09 — Pilot Acceptance Execution (completed locally / not pushed)

**Phase 1G-09 is completed locally.** Pilot Acceptance Execution. Pilot Acceptance ID: `PILOT-1G-08-001`; Pilot Execution ID: `PILOT-EXEC-1G-09-001`; Related RC: `RC-1G-07-001`.

- **Phase 1G-04 remains SEALED.** **Phase 1G-05 remains the pushed readiness baseline.** **Phase 1G-06 remains the pushed release rehearsal baseline.** **Phase 1G-07 remains the pushed GO RC dry run.** **Phase 1G-08 remains the pushed Pilot acceptance preparation.** Phase 1G-09 does **not** reopen Phase 1G-04 and does **not** introduce any new product capability. It executes the prepared Pilot acceptance pack only.
- Purpose: execute Pilot `PILOT-1G-08-001` (execution `PILOT-EXEC-1G-09-001`) against the sealed mainline — run the 15 scenarios (A–O) under the two named server-gate profiles (blocked + completed), capture evidence, record defects, and output a Pilot final decision (PASS / NO-GO / PAUSED) against the Phase 1G-08 exit criteria.
- Deliverables (docs-only):
  - `docs/webui/phase-1g-09-pilot-acceptance-execution.md` — Phase 1G-09 definition, Pilot Acceptance ID (`PILOT-1G-08-001`), Pilot Execution ID (`PILOT-EXEC-1G-09-001`), Phase 1G-04 sealed + Phase 1G-05 / 1G-06 / 1G-07 / 1G-08 pushed baselines, route governance, Pilot execution goal, scope, out-of-scope, participating roles, execution method, scenario list A–O, evidence policy, security boundary, exit criteria, final decision summary, non-reopening declaration.
  - `docs/webui/phase-1g-09-pilot-acceptance-record.md` — filled acceptance record: header, per-scenario A–O status / preconditions / steps / expected / actual / evidence / defect / severity / notes, run matrix, evidence index, defects index, decision, sign-off.
  - `docs/webui/phase-1g-09-pilot-evidence-index.md` — text-summary evidence index (EV-1G09-001 … EV-1G09-016); no raw logs / screenshots / audit JSONL committed.
  - `docs/webui/phase-1g-09-pilot-defect-feedback-log.md` — no new P0 / P1 / P2; the 8 carried-over P2 items (P2-01 … P2-08) recorded as accepted, non-blocking.
  - `docs/webui/phase-1g-09-pilot-final-decision.md` — **Decision: PASS** (operator-executed; all technical PASS criteria met; human approver sign-off pending), PASS-conditions check, route governance, security boundary, production safety, gates summary, eligibility / next action.
- No route governance change. Route governance remains OpenAPI=34, Runtime=34, Tool GET=5, Tool write=0, Tool dry-run=1, Tool execution=1.
- No allowlist change. `STATIC_ALLOWLIST` remains `frozenset({"clarify"})`.
- No code feature expansion. No new route, no Tool write route, no second execution route, no Provider route, no non-clarify execution, no Provider Schema / API. No backend functional code change.
- No production `~/.hermes` access (no `ls` / `stat` / `find` / `cat` / `sqlite3` / `du` / mtime); no production `state.db` access; production Gateway PID `69355` unaffected; ports `5180` / `5181` free throughout and after.
- Final re-verification: route governance 124 passed / 0 failed; related backend regression 19 files 1471 passed / 0 failed; compile / `py_compile toolsets.py` / ruff clean; frontend type-check / lint 0-0 / unit 674 passed (31 files) / build 1862 modules pass; smoke A 6 passed / 1 skipped / 0 failed; smoke B 7 passed / 0 failed; memory-check PASS; dev-check WARN only for `.claude/`; Production Gateway PID `69355` unchanged; ports `5180` / `5181` free.
- **Pilot Result: PASS.** 0 P0, 0 P1, 8 carried-over P2 (non-blocking). 15 / 15 required scenarios (A–O) passed under the two named gate profiles. A final Pilot-accepted PASS requires a human approver sign-off; a PASS recorded without an approver is a recommendation only.
- Local docs-only commit created, then **pushed** at `cd7298416` (`docs(webui): add phase 1g-09 pilot execution record`).
- Next = post-Pilot closeout / final release decision preparation (Phase 1G-10 — see below).

---

## Phase 1G-10 — Post-Pilot Closeout / Final Release Decision Preparation (completed locally / not pushed)

**Phase 1G-10 is completed locally.** Post-Pilot Closeout / Final Release Decision Preparation. Closeout ID: `CLOSEOUT-1G-10-001`; Final Decision Preparation ID: `RELEASE-DECISION-PREP-1G-10-001`; Related RC: `RC-1G-07-001`; Pilot Acceptance ID: `PILOT-1G-08-001`; Pilot Execution ID: `PILOT-EXEC-1G-09-001`; Baseline HEAD: `cd7298416`.

- **Phase 1G-04 remains SEALED.** **Phase 1G-05 remains the pushed readiness baseline.** **Phase 1G-06 remains the pushed release rehearsal baseline.** **Phase 1G-07 remains the pushed GO RC dry run.** **Phase 1G-08 remains the pushed Pilot acceptance preparation.** **Phase 1G-09 remains the pushed Pilot acceptance execution PASS record.** Phase 1G-10 does **not** reopen Phase 1G-04 and does **not** introduce any new product capability. It consolidates the Pilot PASS and prepares final release decision materials only.
- Purpose: consolidate the Phase 1G-09 Pilot PASS (`PILOT-EXEC-1G-09-001`) into a post-Pilot closeout package, and prepare the final release decision materials so a human approver has everything required to issue a final GO / NO-GO / PAUSED decision. **Pilot Result: PASS.** **Human approver sign-off: pending.** **Release authorization: not granted in this phase.**
- Deliverables (docs-only):
  - `docs/webui/phase-1g-10-post-pilot-closeout.md` — Phase 1G-10 definition, Closeout ID (`CLOSEOUT-1G-10-001`), Final Decision Preparation ID (`RELEASE-DECISION-PREP-1G-10-001`), Phase 1G-04 sealed + 1G-05 / 1G-06 / 1G-07 / 1G-08 / 1G-09 pushed baselines, route governance, closeout objective / scope / out-of-scope, Pilot result / evidence / defect / carried-over P2 summary, release authorization status, human approver sign-off status, next phase recommendation, security boundary, production safety, non-reopening declaration.
  - `docs/webui/phase-1g-10-final-release-decision-preparation.md` — final release decision preparation package: decision preparation ID, technical Pilot result, required approver, sign-off status, GO prerequisites (15), NO-GO triggers (14), PAUSED triggers, release scope, release non-goals, safety / route / production boundaries, P0/P1/P2 summary, evidence required before approval, final approver checklist, decision output format.
  - `docs/webui/phase-1g-10-human-approver-signoff-template.md` — blank human approver sign-off template (Approver Name / Role / Decision Date / reviewed IDs / P0/P1/P2 counts / GO-NO-GO-PAUSED / Conditions / Required follow-up / Approval notes / Signature); does not grant approval by itself; no approver fabricated.
  - `docs/webui/phase-1g-10-release-readiness-summary.md` — release readiness summary: status, branch, remote HEAD, related RC / Pilot, Pilot result, gate summary, route governance, security boundary, production safety, documentation package, known P2 list, approval status, release recommendation, remaining blockers.
  - `docs/webui/phase-1g-10-pilot-closeout-report.md` — Pilot closeout report: overview, scenarios A–O (15/15 PASS), evidence summary, defect summary, feedback summary, P0/P1/P2 status, carried-over P2 rationale, operator notes, approver pending note, closeout conclusion.
  - `docs/webui/phase-1g-10-final-go-no-go-draft.md` — final GO / NO-GO draft (recommended = GO, authorized = no, reason = technical Pilot PASS, pending human approver sign-off); GO / NO-GO / PAUSED drafts; not a decision.
- No route governance change. Route governance remains OpenAPI=34, Runtime=34, Tool GET=5, Tool write=0, Tool dry-run=1, Tool execution=1.
- No allowlist change. `STATIC_ALLOWLIST` remains `frozenset({"clarify"})`.
- No code feature expansion. No new route, no Tool write route, no second execution route, no Provider route, no non-clarify execution, no Provider Schema / API. No backend functional code change.
- No production `~/.hermes` access (no `ls` / `stat` / `find` / `cat` / `sqlite3` / `du` / mtime); no production `state.db` access; exactly one Production Gateway running with the identical command; this phase did not stop / restart / replace / reconfigure the Production Gateway; ports `5180` / `5181` free.
- Production Gateway PID note: the sealed baseline PID referenced through Phase 1G-09 (`69355`) no longer exists at Phase 1G-10 closeout — the host rebooted (`2026-06-14 04:02:09`) and `launchd` respawned the gateway as PID `1962` (PPID=1). This is environmental host-reboot drift, not a phase action; exactly one healthy production gateway is running.
- Risk register addendum: Phase 1G-10 addendum (no new P0; no new P1; P2 carried over; P2-09 human approver sign-off pending added as a release authorization dependency, not a technical Pilot failure; release authorization not granted; no production / route / allowlist / provider impact).
- **Pilot Result: PASS.** 0 P0, 0 P1, 8 carried-over P2 + P2-09 (sign-off dependency). Release authorization remains **pending human approver sign-off**; no release was authorized in this phase.
- Local docs-only commit created, **not pushed**.
- Next = final release decision review by the designated human approver; Phase 1G-11 explicitly **not started**.

---

## Phase 1G-10A — Smoke Harness PID Baseline Refresh (completed locally / not pushed)

**Phase 1G-10A is completed locally.** Smoke Harness PID Baseline Refresh. Refresh ID: `SMOKE-PID-REFRESH-1G-10A-001`; Related Closeout ID: `CLOSEOUT-1G-10-001`; Related Final Decision Preparation ID: `RELEASE-DECISION-PREP-1G-10-001`; Related Pilot Execution ID: `PILOT-EXEC-1G-09-001`; Related Pilot Acceptance ID: `PILOT-1G-08-001`; Related RC: `RC-1G-07-001`; Baseline HEAD (remote): `cd7298416`; Local pre-refresh HEAD: `f403eb1cb`.

- **Phase 1G-04 remains SEALED.** **Phase 1G-05 remains the pushed readiness baseline.** **Phase 1G-06 remains the pushed release rehearsal baseline.** **Phase 1G-07 remains the pushed GO RC dry run.** **Phase 1G-08 remains the pushed Pilot acceptance preparation.** **Phase 1G-09 remains the pushed Pilot acceptance execution PASS record.** **Phase 1G-10 remains the completed-locally Post-Pilot closeout.** Phase 1G-10A does **not** reopen Phase 1G-04 and does **not** introduce any new product capability. It refreshes a dev-only smoke harness PID baseline only.
- Purpose: the host reboot documented in Phase 1G-10 (`2026-06-14 04:02:09`) caused `launchd` to respawn the Production Gateway as PID `1962` (the sealed baseline `69355` no longer exists). The dev-only browser smoke harness `scripts/run-dev-webui-execute-audit-smoke.sh` had its production-PID preflight pinned to the now-stale `69355`, so it was fail-closing on a correct, healthy gateway. Phase 1G-10A refreshes that pinned value to the currently observed healthy `1962` and reruns fresh smoke.
- Deliverables (1 script line + comment; docs-only otherwise):
  - `scripts/run-dev-webui-execute-audit-smoke.sh` — `PRODUCTION_GATEWAY_PID=69355` → `1962`, with a two-line comment recording the Phase 1G-10 host-reboot drift origin and the intent that the harness still fails closed on future PID drift. Smoke / preflight / production-count / ports-cleanup logic **unchanged**; `bash -n` passes.
  - `docs/webui/phase-1g-10a-smoke-harness-pid-baseline-refresh.md` — Phase 1G-10A definition, Refresh ID, related IDs, baselines, sealed vs. observed PID, root cause, scope, out-of-scope, script change summary, retained safety checks, fresh smoke result, route governance, backend / frontend gate result, production safety result, security boundary, final conclusion, push status, Phase 1G-11 status, non-reopening declaration.
  - `docs/webui/phase-1-implementation-plan.md` — this update.
  - `docs/webui/phase-1g-05-risk-register.md` — Phase 1G-10A addendum (P2 environment observation closed for the current session).
- No route governance change. Route governance remains OpenAPI=34, Runtime=34, Tool GET=5, Tool write=0, Tool dry-run=1, Tool execution=1.
- No allowlist change. `STATIC_ALLOWLIST` remains `frozenset({"clarify"})`.
- No code feature expansion. No new route, no Tool write route, no second execution route, no Provider route, no non-clarify execution, no Provider Schema / API. No backend functional code change.
- No production `~/.hermes` access (no `ls` / `stat` / `find` / `cat` / `sqlite3` / `du` / mtime); no production `state.db` access; exactly one Production Gateway running (PID `1962`) with the identical command; this phase did not stop / restart / replace / signal / reconfigure the Production Gateway; ports `5180` / `5181` free.
- Fresh smoke rerun after the script refresh: smoke A `6 passed / 1 skipped / 0 failed`; smoke B `7 passed / 0 failed`; **Overall PASS**. The preflight now accepts Production Gateway PID `1962` and would still fail closed on future drift.
- Final re-verification: route governance 124 passed / 0 failed; related backend regression 19 files 1471 passed / 0 failed; compile / `py_compile toolsets.py` / ruff clean; frontend type-check / lint 0-0 / 674 unit (31 files) / build 1862 modules pass; memory-check PASS; dev-check WARN only for the in-flight worktree (this phase's own uncommitted script edit + `.claude/`); Production Gateway PID `1962` unchanged; ports `5180` / `5181` free.
- **Release authorization remains pending human approver sign-off.** A PASS without an approver is a recommendation only. No release, push, production rollout, or Phase 1G-11 start is permitted without the human approver's sign-off.
- Local commit created, **not pushed**.
- Next = final release decision review by the designated human approver; Phase 1G-11 explicitly **not started**.

---

## Phase 1G-10B — Human Approver Final Decision (completed locally / not pushed)

**Phase 1G-10B is completed locally.** Human Approver Final Decision. Human Decision ID: `HUMAN-DECISION-1G-10B-001`; Reviewed Baseline HEAD: `56b571fec1f61b8d6554b1c4a0bf597576266bd1`; Related RC: `RC-1G-07-001`; Pilot Acceptance ID: `PILOT-1G-08-001`; Pilot Execution ID: `PILOT-EXEC-1G-09-001`; Closeout ID: `CLOSEOUT-1G-10-001`; Final Decision Preparation ID: `RELEASE-DECISION-PREP-1G-10-001`; Smoke Refresh ID: `SMOKE-PID-REFRESH-1G-10A-001`.

- **Phase 1G-04 remains SEALED.** All prior baselines (1G-05 readiness, 1G-06 rehearsal, 1G-07 GO RC, 1G-08 Pilot preparation, 1G-09 Pilot execution PASS, 1G-10 closeout, 1G-10A smoke PID refresh) remain as pushed. Phase 1G-10B does **not** reopen Phase 1G-04 and does **not** introduce any new product capability. It records the designated human approver's final decision only.
- Purpose: record the designated human approver's real GO / NO-GO / PAUSED final release decision (`HUMAN-DECISION-1G-10B-001`) in a traceable commit. **Decision: GO.** **Release authorization: granted by the designated human approver (黄瑞邦).** **P2-09: resolved.**
- The decision is the approver's real, explicit input; the Dev Agent did not invent, infer, auto-select, or fabricate it.
- Deliverables (docs-only):
  - `docs/webui/phase-1g-10b-human-approver-final-decision.md` — Phase 1G-10B definition, Human Decision ID, approver, reviewed baseline HEAD + reviewed RC / Pilot / Closeout / Decision Prep / Smoke Refresh IDs, Pilot result + P0/P1/P2 summary, final decision (GO verbatim), decision summary, conditions, required follow-up, approval notes, what-this-decision-is-and-is-not, route governance / security / production safety confirmation, Phase 1G-11 eligibility, final conclusion.
  - `docs/webui/phase-1g-10-human-approver-signoff-template.md` — blank template completed by the designated human approver (GO; signature 黄瑞邦).
  - `docs/webui/phase-1g-10-final-go-no-go-draft.md` — Phase 1G-10B addendum (draft superseded by human approver final decision; GO; authorization granted).
  - `docs/webui/phase-1g-10-release-readiness-summary.md` — Phase 1G-10B addendum (sign-off completed; authorization granted; P2-09 resolved; remaining blockers none).
  - `docs/webui/phase-1g-10-final-release-decision-preparation.md` — Phase 1G-10B addendum (GO prerequisite 15 met; authorization granted).
  - `docs/webui/phase-1g-10-post-pilot-closeout.md` — Phase 1G-10B addendum (human approver final decision recorded; GO).
  - `docs/webui/phase-1g-10-pilot-closeout-report.md` — Phase 1G-10B addendum (human approver final decision recorded; GO).
  - `docs/webui/phase-1g-05-risk-register.md` — Phase 1G-10B addendum (P2-09 resolved; release authorization dependency cleared; P2-01 … P2-08 carried over).
  - `docs/webui/phase-1-implementation-plan.md` — this update.
- No route governance change. Route governance remains OpenAPI=34, Runtime=34, Tool GET=5, Tool write=0, Tool dry-run=1, Tool execution=1.
- No allowlist change. `STATIC_ALLOWLIST` remains `frozenset({"clarify"})`.
- No code feature expansion. No new route, no Tool write route, no second execution route, no Provider route, no non-clarify execution, no Provider Schema / API. No backend functional code change.
- No production `~/.hermes` access (no `ls` / `stat` / `find` / `cat` / `sqlite3` / `du` / mtime); no production `state.db` access; exactly one Production Gateway running (PID `1962`, the Phase 1G-10A refreshed baseline) with the identical command; this phase did not stop / restart / replace / reconfigure the Production Gateway; ports `5180` / `5181` free.
- **Decision: GO.** 0 P0, 0 P1, 8 carried-over P2 (P2-01 … P2-08, non-blocking) + P2-09 (resolved). Release authorization granted by the designated human approver.
- Local docs-only commit created, **not pushed**.
- Phase 1G-11 eligibility: **eligible to prepare as a separately authorized next phase**. Phase 1G-11 is **not started** by this phase.

---

## Phase 1G-11 — Final Release Seal & Phase 2 Unlock (completed and pushed)

**Phase 1G-11 is completed and pushed.** Final Release Seal & Phase 2 Unlock.
Final Seal ID: `FINAL-SEAL-1G-11-001`; Phase 2 Unlock ID:
`PHASE-2-UNLOCK-1G-11-001`; Baseline input HEAD: `3c6ae479b37f3cb4e02c18f6dbef97334b1355e1`;
Related Human Decision ID: `HUMAN-DECISION-1G-10B-001`; Related RC:
`RC-1G-07-001`; Pilot Acceptance ID: `PILOT-1G-08-001`; Pilot Execution ID:
`PILOT-EXEC-1G-09-001`; Closeout ID: `CLOSEOUT-1G-10-001`; Final Decision
Preparation ID: `RELEASE-DECISION-PREP-1G-10-001`; Smoke Refresh ID:
`SMOKE-PID-REFRESH-1G-10A-001`.

- **Phase 1G is SEALED.** All prior baselines (1G-04 sealed, 1G-05 readiness,
  1G-06 rehearsal, 1G-07 GO RC, 1G-08 Pilot preparation, 1G-09 Pilot execution
  PASS, 1G-10 closeout, 1G-10A smoke PID refresh, 1G-10B human approver GO)
  remain as pushed. Phase 1G-11 does **not** reopen Phase 1G-04 and does **not**
  introduce any new product capability. It records the final seal and the Phase 2
  unlock only.
- **Decision: Phase 1G sealed.** Release authorization already granted by
  `HUMAN-DECISION-1G-10B-001` (GO; approver 黄瑞邦; 2026-06-14).
- **Phase 2: unlocked** (`PHASE-2-UNLOCK-1G-11-001`). Phase 2A (Real Tool
  Execution MVP — read-only multi-tool execution) is the recommended next phase,
  eligible to start as a **separately authorized** phase. Phase 2A implementation
  is **not started** by Phase 1G-11.
- **New delivery model from here:** do **not** continue Phase 1G micro-phases;
  use vertical feature slices in Phase 2, where each slice delivers a usable
  capability (not only documentation). See
  `docs/webui/phase-2-unlock-plan.md`.
- Deliverables (docs-only):
  - `docs/webui/phase-1g-11-final-release-seal-and-phase-2-unlock.md` — Phase
    1G-11 definition, Final Seal ID, Phase 2 Unlock ID, reviewed baseline HEAD,
    related Human Decision / RC / Pilot / Closeout / Decision Prep / Smoke
    Refresh IDs, Phase 1G final release status, capability / security boundary /
    route governance / production safety baselines, final gates summary,
    P0/P1/P2 status, Phase 2 unlock decision, Phase 2 roadmap, Phase 2A next
    target, non-goals, what-this-phase-does-not-authorize, final conclusion.
  - `docs/webui/phase-1g-final-release-seal.md` — Phase 1G timeline, final
    commit chain, accepted scope, delivered capabilities (18), security
    guarantees, route governance baseline, audit capabilities, frontend
    capabilities, Pilot result, human approval, known P2, permanent non-goals,
    not-implemented capabilities, production safety, final seal statement,
    Phase 2 handoff.
  - `docs/webui/phase-2-unlock-plan.md` — Phase 2 unlock rationale, why Phase 1G
    stops here, new delivery model, Phase 2 roadmap (2A → 2E), boundaries,
    carried-forward safety invariants, explicit non-goals, entry / exit
    conditions, suggested sequencing.
  - `docs/webui/phase-2a-real-tool-execution-mvp-plan.md` — Phase 2A purpose,
    user-facing outcome, MVP scope, out-of-scope, tool category strategy,
    read-only first principle, candidate tools (planning only, not implemented),
    backend / frontend / audit work items, safety gates, test plan, acceptance
    criteria, rollback plan, risks (R2A-01 … R2A-05), expected commit strategy,
    Phase 1G-11 boundary restated.
  - `docs/webui/phase-1-implementation-plan.md` — this update.
  - `docs/webui/phase-1g-05-risk-register.md` — Phase 1G-11 addendum (Phase 1G
    sealed; Phase 2 unlocked; P2-09 resolved; P2-01 … P2-08 carried over; new
    Phase 2 risks R2A-01 … R2A-05 with mitigations).
  - `docs/webui/phase-1g-10-release-readiness-summary.md` — Phase 1G-11 addendum
    (final seal recorded; Phase 2 unlocked; production rollout not performed;
    Phase 2A not started).
  - `docs/webui/phase-1g-10-final-release-decision-preparation.md` — Phase 1G-11
    addendum (final seal recorded; Phase 2 unlocked; Phase 2A not started).
  - `docs/webui/phase-1g-10b-human-approver-final-decision.md` — Phase 1G-11
    addendum (final seal built on the recorded GO; Phase 2 unlocked).
- No route governance change. Route governance remains OpenAPI=34, Runtime=34,
  Tool GET=5, Tool write=0, Tool dry-run=1, Tool execution=1. **No new backend
  route.**
- No allowlist change. `STATIC_ALLOWLIST` remains `frozenset({"clarify"})`. **No
  allowlist expansion.**
- No code / OpenAPI / test / frontend route changes. No backend functional code
  change. No Provider Schema sent; no Provider API called; no non-clarify
  execution; no Tool write route.
- No production `~/.hermes` access (no `ls` / `stat` / `find` / `cat` /
  `sqlite3` / `du` / mtime); no production `state.db` access; exactly one
  Production Gateway running (PID `1962`, the Phase 1G-10A refreshed baseline)
  with the identical command; this phase did not stop / restart / replace /
  signal / reconfigure the Production Gateway; ports `5180` / `5181` free.
- **Production rollout: not performed.** **Phase 2A implementation: not
  started.**
- Final re-verification: route governance 124 passed / 0 failed; related
  backend regression 19 files passed / 0 failed; compile / `py_compile
  toolsets.py` / ruff clean; frontend type-check / lint 0-0 / unit / build pass;
  smoke A 6 passed / 1 skipped / 0 failed; smoke B 7 passed / 0 failed; memory-
  check PASS; dev-check PASS / WARN only for `.claude/`; Production Gateway PID
  `1962` unchanged; ports `5180` / `5181` free.
- Local docs-only commit created, then **pushed**
  (`docs(webui): seal phase 1g and unlock phase 2`).
- **Next recommended task: Phase 2A Real Tool Execution MVP** (separately
  authorized). Phase 1G is sealed; no further 1G-`xx` micro-phases.

### Phase Status Summary

| Phase | Status |
|-------|--------|
| Phase 1G-04 | SEALED |
| Phase 1G-05 | pushed |
| Phase 1G-06 | pushed |
| Phase 1G-07 | pushed (RC `RC-1G-07-001` GO) |
| Phase 1G-08 | pushed |
| Phase 1G-09 | pushed (Pilot `PILOT-EXEC-1G-09-001` PASS) |
| Phase 1G-10 | pushed |
| Phase 1G-10A | pushed (smoke PID `69355` → `1962`) |
| Phase 1G-10B | pushed (`HUMAN-DECISION-1G-10B-001` GO) |
| Phase 1G-11 | **completed and pushed** (`FINAL-SEAL-1G-11-001` / `PHASE-2-UNLOCK-1G-11-001`) |
| Phase 2 | **unlocked** |
| Phase 2A | completed and pushed (read-only multi-tool execution) |
| Phase 2A-H1 | completed and pushed (`HARDENING-2A-H1-001`) |
| Phase 2B | completed and pushed (controlled provider round-trip; real blocked) |
| Phase 2B-H1 | **completed and pushed** (`HARDENING-2B-H1-001`) |
| Phase 2C | not started (Tool Write Controlled Execution — separately authorized) |

---

## Phase 2B-H1 — Provider Round-trip Hardening (completed and pushed)

**Phase 2B-H1 is completed and pushed.** Provider Round-trip Hardening &
Transient Flake Closure. Hardening ID: `HARDENING-2B-H1-001`; Provider Boundary
Audit ID: `PROVIDER-BOUNDARY-AUDIT-2B-H1-001`; Provider Flake Closure ID:
`PROVIDER-FLAKE-CLOSURE-2B-H1-001`; Input HEAD:
`a3cd3b762e947ba5b93d676557c47ac9487a0649`.

- **Purpose:** harden the Phase 2B provider round-trip and close the Phase 2B
  P2 backlog (real-vendor provider not wired; one transient flake under high
  parallelism; frontend polish optional) with deterministic, agent-independent
  evidence.
- **P0: 0. P1: 0.** All 8 lenses PASS (Provider Schema / Request / Fake / Real
  / Controlled Chain / Audit Redaction / Flake Stability / Frontend Contract).
- **Transient flake:** closed as non-reproduced under
  `PROVIDER-FLAKE-CLOSURE-2B-H1-001` (60+ deterministic reruns, 0 failures; no
  leak path exists in the audit writers).
- **Audit-secret hardening (the only product-code change):** the provider audit
  PEM private-key value pattern was widened from bare/RSA-only to every PEM
  variant (`-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----`) across all four provider
  modules, and `_is_forbidden_field` substring stems were broadened
  (`apikey`, `privatekey`, `credential`). Strictly improving; never relaxes a
  boundary.
- **Phase 2C: not started.** Tool write remains `0`.
- **Production rollout: not performed.**
- **No route governance impact** (OpenAPI 34 / runtime 34 / Tool GET 5 / Tool
  write 0 / dry-run 1 / execution 1; no new route). **No allowlist impact.**
- **Production safety:** exactly one Production Gateway (PID `1962`), unchanged;
  no `~/.hermes` access; no production `state.db` access; ports `5180` / `5181`
  free.
- **Deliverables:** `tests/test_dev_web_phase_2b_hardening_boundaries.py`
  (66 tests), `scripts/run-dev-webui-phase2b-hardening-audit.sh`, and four docs
  (`phase-2b-h1-provider-roundtrip-hardening.md`,
  `phase-2b-h1-provider-boundary-audit.md`,
  `phase-2b-h1-provider-flake-closure.md`, `phase-2b-h1-test-report.md`).
- Commit created, then **pushed**
  (`chore(webui): harden phase 2b provider roundtrip`).
- **Next recommended task: Phase 2C Tool Write Controlled Execution**
  (separately authorized).

## Phase 2C Update — Controlled Tool Write Execution

Phase 2C is complete and pushed (`feat(webui): add controlled sandbox write
tools`). It adds four controlled dev-sandbox write tools
(`dev_sandbox_file_write` / `_append` / `_patch` / `_readback`) in a **separate**
registry + allowlist + execution chain; the Phase 1G/2A `STATIC_ALLOWLIST`
stays frozen at six read-only tools. Writes are sandbox-only, two-phase
(plan/preview → confirm/execute), gated by
`HERMES_TOOL_WRITE_EXECUTION_ENABLED`, and fully audited with rollback
manifests. **No new HTTP route** — `/tools/dry-run` and `/tools/execute` are
reused via `mode` branches, so route governance stays 34/34/5/0/1/1. No
shell/database/external-service write, no production rollout, no `~/.hermes`
or production `state.db` access. See
[phase-2c-controlled-tool-write-execution](phase-2c-controlled-tool-write-execution.md).

## Phase 2C-H1 Update — Write Execution Hardening

Phase 2C-H1 is complete and pushed (`feat(webui): harden sandbox write rollback
and confirmation`). It closes two Phase 2C P2 items: **automatic rollback
execution** (`dev_sandbox_rollback_execute`) and **file-backed confirmation
token TTL** (dev-only store, scope binding, digest binding, persistent
single-use replay protection). No new HTTP route — rollback reuses
`/tools/dry-run` (`mode=rollback_preview`) and `/tools/execute`
(`mode=rollback`) via `mode` branches, so route governance stays 34/34/5/0/1/1.
Provider write remains preview-only. See
[phase-2c-h1-write-execution-hardening](phase-2c-h1-write-execution-hardening.md).

## Phase 2D update — durable audit store

Phase 2D adds a dev-only durable audit store (canonical `audit_schema_v2`,
unified sanitizer, append-only storage, indexing, cursor pagination, filters,
rotation, corruption quarantine) under the dev `HERMES_HOME`. The existing
`GET /api/dev/v1/tools/audit-events` route is enhanced with optional filter /
cursor parameters — **no new route**. Route governance remains 34/34/5/0/1/1.
Legacy offset pagination and the legacy per-kind JSONL read path remain for
backward compatibility. No production rollout, no `~/.hermes` access, no
production `state.db` access. See
[phase-2d-advanced-audit-storage-indexing](phase-2d-advanced-audit-storage-indexing.md).

## Phase 2D-H1 Update — Audit Storage Hardening

Phase 2D-H1 is complete and pushed (`chore(webui): harden audit storage
indexing`). It is a hardening phase — not Phase 2E — that deterministically
hardens the Phase 2D durable dev audit store before Phase 2E. A 10-lens review
(schema, sanitizer, append store, index, query, rotation, recovery, dual-write,
API+Viewer no-leak, production isolation) all PASS; 0 P0, 0 P1.

- Hardening ID: `HARDENING-2D-H1-001`
- Audit Consistency ID: `AUDIT-CONSISTENCY-2D-H1-001`
- Audit Stress ID: `AUDIT-STRESS-2D-H1-001`
- Audit Security Closure ID: `AUDIT-SECURITY-CLOSURE-2D-H1-001`
- Input HEAD: `4836aca4ced0a345098de450876178541e227295`
- Purpose: harden the Phase 2D durable dev audit store before Phase 2E
- Result: 10-lens hardening complete (134 new tests; 1 latent sanitizer fix)
- P0: 0
- P1: 0
- Phase 2E: not started (eligible as the separately authorized next phase)

Deliverables: 3 new hardening test files, the
`run-dev-webui-phase2d-hardening-audit.sh` script, 5 hardening docs, and risk-
register / plan addenda. Route governance remains 34/34/5/0/1/1 — no new route.
No production rollout, no `~/.hermes` access, no production `state.db` access.
See [phase-2d-h1-audit-storage-hardening](phase-2d-h1-audit-storage-hardening.md).

### Phase 2E — Frontend UX Polish (Unified Developer Console)

Frontend-only polish that organizes the Phase 2A–2D-H1 capabilities into a
unified developer console at `/#/console`: an Overview dashboard, a Safety
Boundary panel, unified empty/loading/error/blocked states, consistent safety
badges, and result→audit cross-navigation. Additive `/console` route (the
`/#/` chat workbench is unchanged). Overview/Safety/Diagnostics source from
read-only GETs (`/tools/policy`, `/tools/audit-events`) + frozen baselines; they
execute no tools and add no new HTTP route, no Tool write route, no Provider
route. Route governance remains 34/34/5/0/1/1; production PID 28428 untouched.
See [phase-2e-frontend-ux-polish](phase-2e-frontend-ux-polish.md).

### Phase 2E-H1 — Frontend UX Hardening (Console Stability, Accessibility & Safety Closure)

Phase 2E-H1 is complete and pushed (`chore(webui): harden dev console ux`). It is
a hardening phase — not Phase 3 — that deterministically hardens the Phase 2E
unified developer console through a 9-lens review (console routing/navigation
state, overview/safety baseline, workflow continuity, audit cross-navigation,
blocked reason/error state, accessibility/keyboard/responsive, frontend
type/state consistency, UI no-leak/safety, smoke/production isolation). All 9
lenses PASS; 0 P0, 0 P1.

- Hardening ID: `HARDENING-2E-H1-001`
- Console Workflow Review ID: `CONSOLE-WORKFLOW-2E-H1-001`
- Accessibility Review ID: `ACCESSIBILITY-2E-H1-001`
- UI Security Closure ID: `UI-SECURITY-CLOSURE-2E-H1-001`
- Input HEAD: `0b89f6fc32f1227b9b512c1bb7b215fb0b5ca809`
- Purpose: harden the Phase 2E unified developer console before Phase 3 planning
- Result: 9-lens hardening complete (6 new frontend hardening test files, 1 new
  smoke profile/spec, 1 new backend blocked-reason vocabulary contract test,
  surgical frontend fixes — blocked-reason catalogue drift corrected, stale
  phase status corrected, Audit Viewer prefill marker made lossy)
- P0: 0
- P1: 0
- Phase 3: not started

Deliverables: 6 new hardening vitest files, the `run-dev-webui-phase2e-hardening-audit.sh`
script, 5 hardening docs, a new `phase2e_h1_frontend_ux_hardening` smoke profile,
and risk-register / plan addenda. Route governance remains 34/34/5/0/1/1 — no new
route. No production rollout, no `~/.hermes` access, no production `state.db`
access. See [phase-2e-h1-frontend-ux-hardening](phase-2e-h1-frontend-ux-hardening.md).
