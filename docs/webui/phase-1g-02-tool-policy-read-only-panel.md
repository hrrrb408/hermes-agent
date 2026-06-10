# Phase 1G-02: Tool Policy Read-Only API and Workspace Panel

**Implementation Complete Document**

| Field | Value |
|---|---|
| Phase | 1G-02 |
| Status | Completed |
| Scope | Tool Policy Read-Only Query Service, API, Frontend Data Layer, Workspace Panel, Browser Integration |
| Completion Date | 2026-06-10 |
| Baseline Branch | dev-huangruibang |
| Scope Document | [phase-1g-02-00-tool-policy-read-only-scope.md](phase-1g-02-00-tool-policy-read-only-scope.md) |
| Parent Framework | [phase-1g-00-tool-execution-safety-scope.md](phase-1g-00-tool-execution-safety-scope.md) |
| Static Policy | [phase-1g-01-tool-inventory-static-policy.md](phase-1g-01-tool-inventory-static-policy.md) |

---

## 1. Background and Objectives

Phase 1G-01 established a static, immutable, default-deny policy module (`dev_web_tool_policy.py`) that catalogs 71 canonical tools with risk classification, permanent denylist, candidate allowlist, and schema/argument validation functions.

Phase 1G-02 exposes this policy state through:

1. A read-only query service with no I/O
2. Two GET API routes
3. A TypeScript frontend data layer with safety invariant enforcement
4. A Workspace panel with Overview and Catalog sub-tabs
5. Full browser integration verification across 5 themes and 4 viewports

**Phase 1G-02 does NOT:**

- Enable any tool for execution
- Send Provider Tool Schema to any LLM
- Allow Tool Dispatch or Tool Execute
- Provide Schema Preview, Dry-Run, or Audit capabilities
- Mutate policy, sessions, memory, or review queue state

---

## 2. Phase Breakdown

| Sub-phase | Scope | Status |
|---|---|---|
| 1G-02-00 | Scope Freeze and Contract Definition | Completed |
| 1G-02A | Query Service and DTO Implementation | Completed |
| 1G-02B | API Routes, OpenAPI, and Governance | Completed |
| 1G-02C | Frontend Data Layer (Types, API Client, Store) | Completed |
| 1G-02D | Workspace Tools Panel UI | Completed |
| 1G-02E | Integration and Browser Smoke Closure | Completed |
| 1G-02F | Documentation and Final Closure Gates | Completed |

**Rationale for fine-grained decomposition:**

- Reduce Claude + GLM context burden per session
- Maintain single-responsibility commits
- Each sub-phase independently testable and verifiable
- Natural rollback boundaries

---

## 3. Backend Architecture

### 3.1 Static Policy Module

**File:** `hermes_cli/dev_web_tool_policy.py`

The single source of truth for all policy data. Contains:

- `ToolPolicyEntry` — frozen dataclass per tool
- `ToolPolicyDecision` — frozen decision result
- `ToolRiskLevel` enum (R0–R5)
- `ToolCapability` enum (17 capabilities)
- 71-tool immutable inventory (`TOOL_POLICY_INVENTORY`)
- Derived sets: `STATIC_DENYLIST`, `CANDIDATE_ALLOWLIST`, `STATIC_ALLOWLIST`
- Import-time integrity verification (`_verify_inventory_integrity()`)
- Pure query functions: `get_tool_policy()`, `get_all_tool_policies()`, `evaluate_static_tool_policy()`
- Pure validation functions: `validate_tool_schema_safety()`, `validate_argument_structure()`

**Guarantees:**

- No dependency on FastAPI, Provider, SessionDB, Memory, or Tool Registry
- No filesystem, database, or network access at import time
- No thread or subprocess creation
- All collections are immutable (`MappingProxyType`, `frozenset`)
- Build-time locals deleted after integrity check

### 3.2 Query Service

**File:** `hermes_cli/dev_web_tool_policy_service.py`

`DevToolPolicyQueryService` provides two methods:

- `get_policy_status()` → `ToolPolicyStatusDTO`
- `list_tool_catalog(query)` → `ToolCatalogResponseDTO`

**DTO hierarchy:**

```
ToolPolicyStatusDTO
├── mode: "DEFAULT_DENY"
├── inventory_count: 71
├── risk_counts: {R0:1, R1:5, R2:19, R3:26, R4:17, R5:3}
├── permanent_denylist_count: 26
├── candidate_allowlist_count: 6
├── enabled_allowlist_count: 0
├── execution: ToolPolicyExecutionDTO (all False)
├── limits: ToolPolicyLimitsDTO (13 global limits)
└── safety: ToolPolicySafetyDTO (all read-only)

ToolCatalogResponseDTO
├── items: tuple[ToolCatalogItemDTO]
├── page, page_size, total, total_pages
├── filters: ToolCatalogFiltersDTO
├── summary: ToolCatalogSummaryDTO
└── safety: ToolCatalogSafetyDTO
```

**Query validation:** `validate_catalog_query()` enforces:

- Query string length ≤ 120 chars
- Risk, capability, policy_status, sort — strict enum validation
- Page ≥ 1, page_size ∈ [1, 100]
- Dangerous parameter rejection (`execute`, `force`, `enable`, `write`, `dispatch`, `override`)

**Catalog features:**

- Text search on canonical name and rationale preview
- Risk level filter
- Capability filter
- Policy status filter
- Sort: nameAsc, nameDesc, riskAsc, riskDesc
- Pagination with total pages calculation

**Redaction:** `_redact_paths_and_secrets()` strips local file paths, file:// URIs, and secret patterns from rationale previews. Truncated to 200 characters.

**Safety guarantees:**

- No Registry initialization
- No Handler initialization
- No Provider
- No SessionDB
- No filesystem access
- No database access
- No network access
- No threads
- No mutable global state

---

## 4. API Routes

### 4.1 Endpoints

| Method | Route | Handler | Status |
|---|---|---|---|
| GET | `/api/dev/v1/tools/policy` | `DevToolPolicyQueryService.get_policy_status()` | Implemented |
| GET | `/api/dev/v1/tools/catalog` | `DevToolPolicyQueryService.list_tool_catalog()` | Implemented |

### 4.2 Catalog Query Parameters

| Parameter | Type | Default | Validation |
|---|---|---|---|
| `q` | string | null | ≤ 120 chars |
| `risk` | string | null | R0–R5 |
| `capability` | string | null | 17 enum values |
| `policyStatus` | string | null | PERMANENTLY_DENIED, CANDIDATE, UNLISTED, STATICALLY_ALLOWED |
| `page` | int | 1 | ≥ 1 |
| `pageSize` | int | 25 | 1–100 |
| `sort` | string | nameAsc | nameAsc, nameDesc, riskAsc, riskDesc |

### 4.3 OpenAPI Path Count

| Metric | Value |
|---|---|
| OpenAPI paths (before 1G-02) | 27 |
| OpenAPI paths (after 1G-02) | 29 |
| Tool GET routes | 2 |
| Tool write routes | 0 |

### 4.4 Forbidden Routes (verified absent)

All POST, PATCH, PUT, DELETE methods on `/tools/*` paths return 404.
No `/tools/schema/preview`, `/tools/calls/dry-run`, `/tools/calls`, `/tools/calls/{id}`, or `/tools/calls/{id}/cancel` routes exist.

---

## 5. Policy State

### 5.1 Inventory

| Metric | Count |
|---|---|
| Total canonical tools | 71 |
| R0 (pure computation) | 1 |
| R1 (read-only local) | 5 |
| R2 (read-only external) | 19 |
| R3 (controlled write) | 26 |
| R4 (process/code execution) | 17 |
| R5 (high-risk system) | 3 |

### 5.2 Policy Sets

| Set | Count | Tools |
|---|---|---|
| Permanent Denylist | 26 | terminal, process, write_file, patch, execute_code, delegate_task, browser_back, browser_cdp, browser_click, browser_console, browser_dialog, browser_get_images, browser_navigate, browser_press, browser_scroll, browser_snapshot, browser_type, browser_vision, computer_use, cronjob, discord_admin, ha_call_service, image_generate, memory, send_message, skill_manage |
| Candidate Allowlist | 6 | clarify (R0), read_file (R1), search_files (R1), session_search (R1), skill_view (R1), skills_list (R1) |
| Enabled Static Allowlist | 0 | *(empty — no tool is enabled)* |

### 5.3 Mode

```
mode = DEFAULT_DENY
allowed = false (for ALL 71 tools)
```

---

## 6. Frontend Data Layer

### 6.1 TypeScript Types

**File:** `apps/hermes-dev-webui/src/types/api/toolPolicy.ts`

Read-only interfaces matching backend DTOs with `readonly` modifiers. Key types:

- `ToolPolicyStatusResponse`
- `ToolCatalogResponse`
- `ToolCatalogItem`
- `ToolCatalogFilters`
- `ToolRiskLevel`, `ToolCapability`, `ToolPolicyStatus` (union types)

### 6.2 API Client

**File:** `apps/hermes-dev-webui/src/api/toolPolicy.ts`

Two exported functions:

- `fetchToolPolicyStatus(signal?)` → GET `/tools/policy`
- `fetchToolCatalog(filters?, signal?)` → GET `/tools/catalog`

`buildCatalogQueryString()` only includes non-empty, non-default values and never sends dangerous parameters.

### 6.3 Pinia Store

**File:** `apps/hermes-dev-webui/src/stores/toolPolicy.ts`

Features:

- Independent `AbortController` per request type (policy vs catalog)
- Request sequence counter for stale response detection
- Retry with configurable max attempts
- Tool selection state with stale selection cleanup
- Safety invariant enforcement:
  - `checkPolicySafetyInvariants()`: enabled_allowlist_count must be 0, execution.enabled must be false, safety.read_only must be true, safety.execute_available must be false
  - `checkCatalogSafety()`: all catalog items must have `allowed=false` and `executionAvailable=false`
- Enters safety error state on violation

### 6.4 Constants

**File:** `apps/hermes-dev-webui/src/types/api/toolPolicyConstants.ts`

Runtime constants for dropdown labels derived from TypeScript union types.

---

## 7. Workspace UI

### 7.1 Tools Tab

The Workspace panel includes a **Tools** tab (alongside Files, Memory, Context, Agent, Review). Selecting it renders `ToolPolicyPanel.vue`.

### 7.2 Policy Overview (`ToolPolicyOverview.vue`)

Displays:

- Safety notice: "Read-only policy view — No tools are enabled"
- Statistics: inventory count, risk distribution bar, denylist/candidate/enabled counts
- Execution status: "Disabled" / "Not sent" / "Unavailable"
- Global limits table (14 values)
- Safety flags

### 7.3 Catalog (`ToolCatalog.vue`)

Features:

- Search input with debounce
- Risk filter dropdown
- Policy status filter dropdown
- Sort dropdown (name/risk ascending/descending)
- Paginated catalog list
- Tool selection with detail view
- Loading skeleton, error state, retry button, empty state

### 7.4 Tool Detail

Shows for each selected tool:

- Canonical name, risk level, capabilities
- Policy status badge (Permanently Denied / Candidate / Unlisted)
- Source module, rationale preview
- Execution availability: "Unavailable" for all features
- Schema preview: "Unavailable"
- Dry-run: "Unavailable"

### 7.5 Candidate Display

Candidate tools show:

- Policy status: "Candidate" badge
- Notice: "Not enabled"
- All `allowed` flags are `false`
- No enable or execute buttons exist

### 7.6 UI Safety

- No tool execution controls
- No policy mutation controls
- No enable/execute/action buttons
- "Read-only" badge in panel header
- All five themes supported via CSS variables
- Keyboard navigation with ARIA attributes
- Responsive across 4 viewports

---

## 8. Browser Integration

### 8.1 Test Matrix

| Dimension | Values | Count |
|---|---|---|
| Themes | obsidian, paper, song, ink, sakura-night | 5 |
| Viewports | 1440×900, 1280×800, 1024×768, 768×900 | 4 |
| **Combinations** | | **20** |

### 8.2 Verification Results

| Check | Result |
|---|---|
| Tool API requests all GET | ✓ |
| Tool write requests | 0 |
| Provider requests | 0 |
| External requests | 0 |
| Console errors | 0 |
| CORS errors | 0 |
| Asset 404 errors | 0 |
| Horizontal overflow | 0 |
| 5 themes rendered | ✓ |
| 4 viewports covered | ✓ |
| Policy Overview loads from real API | ✓ |
| Catalog loads with correct defaults | ✓ |
| Search, filter, sort, pagination work | ✓ |
| Tool selection shows correct detail | ✓ |
| Keyboard navigation works | ✓ |
| No mutation controls exist | ✓ |
| Rapid search settles to final result | ✓ |
| Error state shows retry button | ✓ |

### 8.3 Runner Cleanup

- `scripts/run-dev-webui-smoke.sh` tracks PIDs
- Cleanup trap kills Dev API and WebUI processes
- Port release verified for 5180 and 5181
- Playwright artifacts disabled (screenshot, video, trace = off)

---

## 9. Safety Boundary

### 9.1 Static Policy

| Property | Value |
|---|---|
| `STATIC_ALLOWLIST` | `frozenset()` (empty) |
| All tools `allowed` | `false` |
| `executionAvailable` | `false` |
| `schemaPreviewAvailable` | `false` |
| `dryRunAvailable` | `false` |

### 9.2 Runtime Safety

| Property | Status |
|---|---|
| Provider Tool Schema | Not sent |
| Tool Dispatch | 0 |
| Tool Audit | Absent (no `tool_execution_audit` table) |
| Tool Execution | Disabled |
| Session writes | 0 |
| Memory writes | 0 |
| Review writes | 0 |

### 9.3 Kill Switches

| Variable | Status |
|---|---|
| `HERMES_AGENT_RUN_ENABLED` | unset |
| `HERMES_TOOL_EXECUTION_ENABLED` | unset |
| `HERMES_AGENT_TOOLS_ENABLED` | unset |

---

## 10. Test Results

All results from this round's actual execution (not reused from prior phases).

### 10.1 Backend Tests

| Metric | Value |
|---|---|
| Command | `./scripts/run_tests.sh` (9 test files) |
| Collected | 617 |
| Passed | 617 |
| Failed | 0 |
| Duration | 7.3s (28 workers) |

**Test files:**

- `tests/test_dev_web_tool_policy.py` — 81 tests (static policy integrity)
- `tests/test_dev_web_tool_policy_service.py` — 143 tests (query service, DTOs, validation, filtering, sorting, pagination, redaction)
- `tests/test_dev_web_tool_policy_api.py` — 79 tests (API routes, safety boundaries, forbidden routes)
- `tests/test_dev_check_webui.py` — 18 tests (dev-check governance)
- `tests/test_dev_web_0c06_closure.py` — 106 tests (Phase 0C closure)
- `tests/test_dev_web_memory.py` — 77 tests (memory read-only)
- `tests/test_dev_web_memory_writer_dry_run.py` — 51 tests (memory writer dry-run)
- `tests/test_dev_web_agent_run.py` — 47 tests (agent run SSE)
- `tests/test_dev_web_agent_run_boundaries.py` — 15 tests (agent run boundaries)

### 10.2 Frontend Tests

| Metric | Value |
|---|---|
| Lint | PASS |
| Type-check | PASS |
| Test files | 24 |
| Tests | 506 |
| Failed | 0 |
| Duration | 1.84s |
| Build modules | 1847 |
| Build duration | 1.04s |

**Key test files:**

- `tool-policy-api.spec.ts` — 28 tests (GET-only, no dangerous params, abort, race)
- `tool-policy-store.spec.ts` — 68 tests (state, safety invariants, abort, race, retry)
- `tool-policy-panel.spec.ts` — 55 tests (UI rendering, read-only boundary, accessibility)
- `workspace-panel.spec.ts` — 11 tests (tab switching, no execution buttons)
- `accessibility.spec.ts` — 36 tests (ARIA, keyboard, no v-html)

### 10.3 Browser Smoke Tests

| Metric | Value |
|---|---|
| Command | `./scripts/run-dev-webui-smoke.sh` |
| Test files | 2 |
| Tests | 63 |
| Passed | 63 |
| Failed | 0 |
| Duration | 3.9 min |
| Themes | 5 |
| Viewports | 4 |

### 10.4 Hermes Gates

| Gate | Result |
|---|---|
| `python -m compileall hermes_cli agent tools` | PASS |
| `python -m py_compile toolsets.py` | PASS |
| Ruff (6 Phase 1G-02 files) | PASS |
| `memory-check` | PASS |
| `dev-check` | WARN (worktree dirty from docs changes + .claude/) |
| Static OpenAPI paths | 29 |
| Runtime routes | 29 |

---

## 11. Side-Effect Validation

### 11.1 Before (captured before quality gates)

| Artifact | SHA-256 (truncated) |
|---|---|
| state.db | `b1911d16c1b5...` (360,607,744 bytes) |
| MEMORY.md | `44be12a08bbe...` (1,890 bytes) |
| memory/events.jsonl | `3df1fc835d53...` (9 lines) |
| memory/reviews/events.jsonl | `05b8e7b851ee...` (9 lines) |

### 11.2 After (to be verified after all gates)

See Phase 1G-02F closure report for complete Before/After comparison.

### 11.3 Invariant

```
persistent side effects = 0
Provider Tool Schema = 0
Tool Dispatch = 0
Tool Execution = 0
Tool Audit creation = 0
Session writes = 0
Memory writes = 0
Review writes = 0
New runtime files = 0
```

---

## 12. Git Commit Chain

| # | Commit | Message | Sub-phase |
|---|---|---|---|
| 1 | `7f758ab4d` | `docs(webui): define phase 1g-02 tool policy read-only scope` | 1G-02-00 |
| 2 | `d0bed354c` | `feat(webui): add tool policy query service` | 1G-02A |
| 3 | `54d7f05f1` | `feat(webui): add tool policy read-only api` | 1G-02B |
| 4 | `af321efaa` | `feat(webui): add tool policy frontend data layer` | 1G-02C |
| 5 | `a26d35b64` | `feat(webui): add tool policy read-only panel` | 1G-02D |
| 6 | `088e2f900` | `test(webui): close tool policy panel integration` | 1G-02E |
| 7 | *(new)* | `docs(webui): complete phase 1g-02 tool policy panel` | 1G-02F |

---

## 13. Risks

### 13.1 P1 — Open (not blocking 1G-02)

| Risk | Why not blocking |
|---|---|
| Runtime Schema closure not implemented | STATIC_ALLOWLIST empty, no schema sent |
| `read_file` Root Allowlist not implemented | STATIC_ALLOWLIST empty, no file read dispatched |
| Symlink escape prevention not implemented | STATIC_ALLOWLIST empty, no file access dispatched |
| Tool Output Redaction runtime not implemented | No tool execution in this phase |
| Runtime Tool Timeout not implemented | No tool execution in this phase |
| `toolCallId` idempotency not implemented | No tool calls in this phase |

### 13.2 P2 — Future considerations

| Risk | Notes |
|---|---|
| Catalog performance at scale | Currently 71 items — sub-millisecond; revisit if inventory grows |
| Capability badge density | 17 capabilities may need grouping or progressive disclosure |
| Search debounce latency | 300ms default; user testing may adjust |
| Narrow-screen detail experience | Long tool detail may scroll on mobile; needs UX iteration |
| Theme contrast maintenance | CSS variable drift across themes; needs visual regression |

---

## 14. Follow-up Phases

| Phase | Scope | Status |
|---|---|---|
| Phase 1G-03 | Tool Schema Preview API | Not Started |
| Phase 1G-04 | Tool Call Dry-Run Policy Evaluation | Not Started |
| Phase 1G-05 | Fake Tool Fixture Execute | Not Started |
| Phase 1G-06 | Dev-Only R0/R1 Execute | Not Started |
| Phase 1-Release | Final Verification and Push | Not Started |

Phase 1G as a whole is NOT complete. Only Phase 1G-02 is complete.

---

## 15. Files Changed (Phase 1G-02)

### Backend (Production)

| File | Action |
|---|---|
| `hermes_cli/dev_web_tool_policy.py` | Added (1G-01 baseline) |
| `hermes_cli/dev_web_tool_policy_service.py` | Added |
| `hermes_cli/dev_web_api.py` | Modified (2 tool policy routes) |
| `docs/webui/openapi/dev-web-api-v1.yaml` | Modified (27→29 paths) |

### Frontend (Production)

| File | Action |
|---|---|
| `src/types/api/toolPolicy.ts` | Added |
| `src/types/api/toolPolicyConstants.ts` | Added |
| `src/api/toolPolicy.ts` | Added |
| `src/stores/toolPolicy.ts` | Added |
| `src/components/workspace/ToolPolicyPanel.vue` | Added |
| `src/components/workspace/ToolPolicyOverview.vue` | Added |
| `src/components/workspace/ToolCatalog.vue` | Added |
| `src/components/layout/WorkspacePanel.vue` | Modified |

*(All frontend paths relative to `apps/hermes-dev-webui/`)*

### Tests

| File | Action |
|---|---|
| `tests/test_dev_web_tool_policy.py` | Added (1G-01 baseline) |
| `tests/test_dev_web_tool_policy_service.py` | Added |
| `tests/test_dev_web_tool_policy_api.py` | Added |

### Frontend Tests

| File | Action |
|---|---|
| `src/tests/tool-policy-api.spec.ts` | Added |
| `src/tests/tool-policy-store.spec.ts` | Added |
| `src/tests/tool-policy-panel.spec.ts` | Added |

### Smoke Tests

| File | Action |
|---|---|
| `apps/hermes-dev-webui/tests/smoke/phase-1g-tool-policy-smoke.spec.ts` | Added |

### Documentation

| File | Action |
|---|---|
| `docs/webui/phase-1g-02-00-tool-policy-read-only-scope.md` | Added (1G-02-00) |
| `docs/webui/phase-1g-02-tool-policy-read-only-panel.md` | Added (this document, 1G-02F) |
| `docs/webui/phase-1-implementation-plan.md` | Modified |

---

## Phase 1G-02 Release Test Isolation Fix

**Status:** Completed

Two release-blocking items were fixed:

1. **Browser Guard log**: XAI OAuth tests in `test_auth_manual_paste.py` triggered `webbrowser.get`/`webbrowser.open`. Fixed with autouse fixture mocking `_can_open_graphical_browser`. Browser Supervisor tests triggered `subprocess.Popen(google-chrome)`. Fixed by adding `HERMES_E2E_BROWSER=1` env var gate to `pytestmark`.

2. **Stale route count assertions**: `test_dev_web_messages.py` and `test_dev_web_sessions.py` asserted `len(business) == 11` (actual: 29). Fixed with module-level route contract checks; central governance owns the exact 29-path count.

See `docs/webui/phase-1g-02-release-test-isolation-fix.md` for full details.
