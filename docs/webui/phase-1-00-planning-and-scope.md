# Phase 1-00: Phase 1 Planning & Scope Freeze

**Status:** Completed
**Date:** 2026-06-08
**Branch:** dev-huangruibang
**Base commit:** cc64aa690 (Phase 0E-Release: Phase 1 safety boundary)
**Depends on:** Phase 0E-Release (all 0E subphases completed and pushed)

---

## 1. Background

Phase 0 (0A → 0B → 0C → 0D → 0E) is formally sealed and pushed to `origin/dev-huangruibang` at commit `cc64aa690`. The Dev WebUI is a fully read-only system with:

- **11 read-only API routes** connected to real backend data
- **11 GET routes + 1 side-effect-free POST route** (context preview)
- **Zero write operations** of any kind
- **803 tests** (479 backend + 324 frontend) — all passing
- **24 Playwright smoke tests** across 5 themes × 4 viewports
- **15 dev-check WebUI governance checks**
- **Complete production isolation** verified at every phase closure
- **Phase 1 Safety Boundary** documented in `phase-0e-06-phase-1-safety-boundary.md`

Phase 1-00 is a **planning-only** task. It does not implement any functionality. It freezes the Phase 1 roadmap, subphase boundaries, safety gates, and acceptance criteria before any Phase 1 development begins.

---

## 2. Current Baseline

### 2.1 Repository State

| Item | Value |
|------|-------|
| Branch | `dev-huangruibang` |
| HEAD | `cc64aa69029cf6b101a47d3a24ad658faf55954f` |
| origin/dev-huangruibang | `cc64aa69029cf6b101a47d3a24ad658faf55954f` |
| local == remote | Yes |
| Working tree | Clean |

### 2.2 Completed Phases

| Phase | Scope | Final Commit |
|-------|-------|-------------|
| 0A | Theme system & project scaffold | `b2e34b83e` |
| 0B | Layout & theme integration | `e078c18ba` |
| 0C | Read-only API, sessions, messages, memory, context, agent | `564c15c98` |
| 0D | Responsive breakpoints, accessibility, reduced motion | `279e27259` |
| 0E | Engineering governance, build artifacts, smoke tests, dev-check, safety boundary | `cc64aa690` |

### 2.3 Environment State

| Item | Value |
|------|-------|
| HERMES_HOME | `/Users/huangruibang/Code/hermes-home-dev` |
| Production Gateway PID | 1717 (running, untouched) |
| Dev Gateway | stopped |
| Port 5180 | free |
| Port 5181 | free |
| memory-check | PASS |
| dev-check | PASS |

### 2.4 Current Route Inventory

| Method | Path | Classification | Description |
|--------|------|----------------|-------------|
| GET | `/api/dev/v1/status` | READ | System status and environment verification |
| GET | `/api/dev/v1/files/status` | READ | File browsing availability (`available: false`) |
| GET | `/api/dev/v1/sessions` | READ | Session list with pagination |
| GET | `/api/dev/v1/sessions/{sessionId}` | READ | Session detail |
| GET | `/api/dev/v1/sessions/{sessionId}/messages` | READ | Session messages with pagination |
| GET | `/api/dev/v1/memory/status` | READ | Memory system status |
| GET | `/api/dev/v1/memory/categories` | READ | Memory categories list |
| GET | `/api/dev/v1/memory/items` | READ | Memory items list |
| GET | `/api/dev/v1/memory/items/{memoryId}` | READ | Memory item detail |
| POST | `/api/dev/v1/context/preview` | READ | Memory context preview (side-effect-free, no LLM) |
| GET | `/api/dev/v1/agent/status` | READ | Agent configuration status |

**Total: 12 endpoints. All read-only / side-effect-free.**

### 2.5 Current Safety Mechanisms

| Mechanism | Location | Status |
|-----------|----------|--------|
| Environment isolation | `dev_web_config.py` `enforce_dev_environment()` | Active |
| Local-only binding | FastAPI `127.0.0.1` | Active |
| CORS restriction | `dev_web_middleware.py` | Active |
| Path redaction | `dev_web_api.py` `redact_local_paths()` | Active |
| DTO whitelisting | `dev_web_schemas.py` | Active |
| Input validation | Session ID regex, memory ID pattern, pagination limits | Active |
| Sensitive field filtering | Agent status strips API keys, base URLs, credentials | Active |
| No LLM calls | Context preview simulates without model calls | Active |
| No side effects | Every operation guaranteed to leave no persistent state changes | Active |
| Production fail-closed | `enforce_dev_environment()` refuses if wrong home detected | Active |
| Dev gateway isolation | `gateway/dev_isolation.py` | Active |
| Forbidden route verification | `dev-check` | Active |
| Route count verification | `dev-check` (12 expected) | Active |

### 2.6 Confirmed Write-Zero State

- `state.db` in dev-home: **unchanged by any WebUI operation**
- `MEMORY.md` in dev-home: **unchanged**
- All `memory/` files in dev-home: **unchanged** (SHA-256 verified at 0C/0D/0E closure)
- Production `~/.hermes`: **never accessed**
- Production `state.db`: **never accessed**
- Production Gateway PID 1717: **never stopped, restarted, or replaced**

### 2.7 Code Modules Outside WebUI (Not Accessible)

| Module | Path | Capability |
|--------|------|-----------|
| Memory Writer | `agent/runtime_memory_writer.py` | Evaluates whether to WRITE, UPDATE, REVIEW, or SKIP memory candidates |
| Memory Review Queue | `agent/memory_review_queue.py` | Manages review lifecycle (enqueue → approve/reject), supports dry-run |
| Memory Router | `hermes_cli/memory_router.py` | `create_memory_item()`, `update_memory_item()`, `find_item_location()` |
| Agent Runtime | `agent/conversation_loop.py` | Core agent conversation loop |
| Tool Registry | `tools/registry.py` | Self-registering tool dispatch |
| Toolsets | `toolsets.py` | Tool grouping and management |

**None of these modules are imported or referenced by any `dev_web_*.py` file.** The WebUI has zero access to write/execute capabilities.

---

## 3. Phase 1 Goal

### 3.1 Primary Goal

**Transition the Dev WebUI from a purely read-only observability dashboard to a controlled Dev Operations Console, introducing write and execution capabilities incrementally under strict safety gates.**

Phase 1 is **not** "fully open write operations." Phase 1 introduces capabilities under:

```
Read-only first → Dry-run second → Dev-only execute third → High-risk last
```

### 3.2 Core Principles

1. **Default Deny** — All capabilities disabled until explicitly enabled per-phase
2. **Dry-Run First** — Every write operation must have a dry-run mode that validates without mutating
3. **Dev-Only Isolation** — All Phase 1 capabilities restricted to dev-home; production is fail-closed
4. **Explicit Confirmation** — All write operations require user confirmation with cancel-default focus
5. **Allowlist Enforcement** — Only explicitly listed actions are permitted
6. **Audit Trail** — Every real write operation produces an audit event
7. **Kill Switch** — Every capability can be immediately disabled without code changes
8. **No Production by Design** — Production detection results in refusal, not warning
9. **Test-Before-Enable** — Comprehensive tests are a prerequisite, not an afterthought
10. **Dual-Channel Safety** — Backend enforcement is mandatory; frontend hiding is insufficient

### 3.3 Safety Baseline

All Phase 1 work must satisfy the Phase 1 Safety Boundary defined in:

- `docs/webui/phase-0e-06-phase-1-safety-boundary.md` — definitive safety reference

No Phase 1 write capability may be enabled without satisfying every applicable gate defined in that document.

---

## 4. Phase 1 Non-Goals

Phase 1 **does not** aim to:

1. Deploy the Dev WebUI to any server or production environment
2. Enable public or network access (remains `127.0.0.1` only)
3. Replace the CLI as the primary agent interface
4. Modify the production environment in any way
5. Access or modify `~/.hermes` (production home)
6. Access or modify production `state.db`
7. Control the production Gateway (stop, restart, replace)
8. Open Dashboard control capabilities
9. Enable arbitrary file browsing, upload, or deletion
10. Enable arbitrary shell or tool execution
11. Enable unconfirmed write operations
12. Enable write operations without dry-run preview
13. Enable write operations without audit trail
14. Enable actions without an explicit allowlist entry
15. Enable untested routes
16. Remove or weaken any existing safety mechanism
17. Enable multiple concurrent users
18. Introduce any capability not listed in the Phase 1 subphase sequence

---

## 5. Subphase Roadmap

### Overview

```
Phase 1A ─── Review Queue Read-Only Panel         [Low Risk, No Write]
Phase 1B ─── Review Queue Approve/Reject Dry-Run  [Medium Risk, No Real Write]
Phase 1C ─── Review Queue Approve/Reject Execute   [High Risk, Dev-Only Write]
Phase 1D ─── Memory Writer Dry-Run Panel           [Medium Risk, No Real Write]
Phase 1E ─── Agent Prompt Preview / Dry-Run        [Medium Risk, No LLM]
Phase 1F ─── Agent Run Dev-Only Without Tools      [High Risk, Dev-Only LLM]
Phase 1G ─── Tool Execution Safety Framework        [High Risk, Allowlist Only]
Phase 1-Release ─ Final Verification & Push        [Release Gate]
```

**Dependency graph:**

```
1A ──→ 1B ──→ 1C
  (parallel)     1D (no dependency on 1A/1B/1C)
                  1E ──→ 1F ──→ 1G
```

1A→1B→1C and 1D and 1E→1F→1G are independent tracks. Within each track, phases are sequential.

---

## 6. Phase 1A: Review Queue Read-Only Panel

### 6.1 Goal

Display Memory Review Queue items in the Dev WebUI as a read-only panel. This is the first new data surface added to the WebUI since Phase 0C.

### 6.2 Scope

**New API routes (3 read-only):**

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/dev/v1/reviews/status` | Review queue status (enabled, pending count, max capacity) |
| GET | `/api/dev/v1/reviews` | List review items with pagination and filtering |
| GET | `/api/dev/v1/reviews/{reviewId}` | Review item detail |

**New frontend components:**

- Review tab in workspace panel
- Review item list with status badges
- Review item detail view
- Review queue status indicator

### 6.3 Non-Goals

- No approve, reject, or enqueue operations
- No review item creation
- No review item modification
- No memory write, update, or archive
- No agent run or tool execution
- No write operations of any kind

### 6.4 Write Capability

**None.** This phase is strictly read-only.

### 6.5 Safety Gates

1. Dev-only environment enforced
2. Only GET routes for review items
3. No approve/reject/enqueue routes registered
4. Review item content follows DTO whitelisting
5. Path redaction applied to review item paths
6. No modification to review queue files on disk
7. `dev-check` includes review queue read-only check
8. Playwright smoke test for Review panel
9. Forbidden route test: `POST /api/dev/v1/reviews/*` returns 405

### 6.6 Acceptance Criteria

1. 3 new GET routes registered and documented in OpenAPI spec
2. Route count updated in dev-check (12 → 15 business routes)
3. Forbidden route tests updated
4. Frontend Review panel displays review items
5. All 5 themes render correctly with Review panel
6. No review files modified on disk (SHA-256 hash unchanged)
7. No memory files modified on disk
8. DTO whitelisting prevents raw content/prompt leakage
9. Path redaction strips all local paths
10. `dev-check` PASS
11. `memory-check` PASS
12. `compileall` PASS
13. Frontend lint/type-check/test/build PASS
14. Playwright smoke PASS
15. Production untouched
16. Worktree clean

### 6.7 Prerequisite

- Phase 0E-Release completed and pushed
- Review Queue module (`agent/memory_review_queue.py`) has `list_review_items()` and `load_review_item()` functions confirmed

---

## 7. Phase 1B: Review Queue Approve/Reject Dry-Run

### 7.1 Goal

Enable dry-run preview of Review Queue approve and reject operations. No real state mutation occurs. The user sees exactly what *would* happen without any files being modified.

### 7.2 Scope

**New API routes (2 dry-run only):**

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/dev/v1/reviews/{reviewId}/approve/dry-run` | Preview approve action without executing |
| POST | `/api/dev/v1/reviews/{reviewId}/reject/dry-run` | Preview reject action without executing |

**New frontend components:**

- Dry-run preview dialog for approve action
- Dry-run preview dialog for reject action
- Confirmation UI (display-only, does not execute)

### 7.3 Non-Goals

- No real approve execution
- No real reject execution
- No memory write, update, or archive
- No event append to `events.jsonl`
- No snapshot generation
- No review file modification
- No state mutation of any kind

### 7.4 Write Capability

**None.** All operations are dry-run only. No real execution is possible.

### 7.5 Safety Gates

1. Phase 1A completed and accepted
2. `dry_run=true` is the default (no real execution possible)
3. Dry-run response shows proposed action, target memory ID, duplicate/protected checks
4. P0 and permanent memory items cannot be approved for update
5. Kill switch: `HERMES_WEBUI_ENABLE_REVIEW_APPROVE=false` by default
6. Audit event produced even for dry-run
7. No modification to review queue files on disk in dry-run mode
8. Side-effect hash test: review files unchanged after dry-run
9. Forbidden route test: real approve without dry_run returns 403

### 7.6 Acceptance Criteria

1. 2 new POST routes registered (dry-run only)
2. Route count updated in dev-check (15 → 17)
3. Dry-run response includes: `wouldModify`, `wouldWrite`, `affectsMemory`, `affectsProduction` (always false)
4. P0/permanent memory items cannot be dry-run approved
5. Review files hash unchanged after dry-run
6. Memory files hash unchanged after dry-run
7. No events appended to `events.jsonl`
8. UI shows confirmation dialog but does not execute
9. Kill switch visible in status API
10. `dev-check` PASS
11. `memory-check` PASS
12. `compileall` PASS
13. Frontend lint/type-check/test/build PASS
14. Playwright smoke PASS
15. Production untouched
16. Worktree clean

### 7.7 Prerequisite

- Phase 1A completed and accepted
- `approve_review_item()` in `memory_review_queue.py` has `dry_run` parameter confirmed
- `reject_review_item()` in `memory_review_queue.py` available

---

## 8. Phase 1C: Review Queue Approve/Reject Dev-Only Execute

### 8.1 Goal

Allow real execution of Review Queue approve and reject operations within the dev-home environment only. Requires explicit confirmation, dry-run preview, and audit trail.

### 8.2 Scope

**New API routes (2 execute):**

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/dev/v1/reviews/{reviewId}/approve` | Execute approve action (dev-only, confirmed) |
| POST | `/api/dev/v1/reviews/{reviewId}/reject` | Execute reject action (dev-only, confirmed) |

**New frontend components:**

- Execute confirmation flow (dry-run → confirm → execute)
- Audit event display
- Rollback status or irreversibility warning

### 8.3 Non-Goals

- No agent run
- No tool execution
- No general-purpose memory writer
- No production environment execution
- No batch operations
- No auto-approve or auto-reject

### 8.4 Write Capability

**Yes — dev-home only, explicit confirmation required.**

This is the first phase that introduces real write operations. Only dev-home review queue files may be modified. Production is fail-closed.

### 8.5 Safety Gates

1. Phase 1B completed and accepted
2. Dry-run preview must be shown first (no skip)
3. Explicit confirmation required (request body `confirmed: true` + UI dialog)
4. Only dev-home review queue accessible
5. P0/permanent protection enforced at backend level
6. Real audit event produced on execution
7. Before/after summary in audit event
8. Undo/rollback strategy documented (or explicit "no rollback" warning)
9. Kill switch active and visible in dev-check
10. State transition correctness verified
11. Duplicate detection enforced
12. Hash side-effect matches expected

### 8.6 Acceptance Criteria

1. 2 new POST routes registered (execute)
2. Route count updated in dev-check
3. Dry-run first: real execute requires showing dry-run result first
4. Confirmation: both backend (`confirmed: true`) and UI dialog required
5. Dev-only: production paths rejected immediately
6. Audit event: timestamp, actor, action, target, before/after summary, result
7. State transition: PENDING → APPROVED or PENDING → REJECTED verified
8. P0/permanent items: backend rejects approve for protected memories
9. Review files hash changes match expected operation
10. No unexpected memory file changes
11. Rollback strategy documented
12. Kill switch functional and visible
13. `dev-check` PASS
14. `memory-check` PASS
15. `compileall` PASS
16. Frontend lint/type-check/test/build PASS
17. Playwright smoke PASS
18. Production untouched
19. Worktree clean

### 8.7 Prerequisite

- Phase 1B completed and accepted
- Audit trail design complete
- Kill switch implemented
- Explicit confirmation mechanism implemented
- Production fail-closed verified
- Rollback strategy documented

---

## 9. Phase 1D: Memory Writer Dry-Run Panel

### 9.1 Goal

Display Memory Writer decision previews and dry-run results in the WebUI. Show what the Memory Writer *would* do (WRITE, UPDATE, REVIEW, or SKIP) without actually performing any operation.

### 9.2 Scope

**New API routes (3 dry-run only):**

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/dev/v1/memory/write/dry-run` | Preview memory write decision |
| POST | `/api/dev/v1/memory/update/dry-run` | Preview memory update decision |
| POST | `/api/dev/v1/memory/archive/dry-run` | Preview memory archive decision |

**New frontend components:**

- Memory Writer decision preview panel
- Dry-run result display (proposed action, target category, duplicate score, protection status)

### 9.3 Non-Goals

- No real memory write
- No real memory update
- No real memory archive
- No automatic memory writing
- No agent auto-memory
- No memory event append

### 9.4 Write Capability

**None.** All operations are dry-run only. No real memory mutation is possible.

### 9.5 Safety Gates

1. Dev-only environment enforced
2. No real memory write possible (dry-run only)
3. Dry-run shows: proposed memory content, target category, duplicate detection score
4. Category allowlist enforced (only active categories)
5. P0/permanent protection enforced
6. No modification to `MEMORY.md`, indexes, records, or `events.jsonl`
7. Side-effect hash test: all memory files unchanged
8. Kill switch: `HERMES_WEBUI_ENABLE_MEMORY_WRITE=false` by default
9. `dev-check` includes memory write dry-run check

### 9.6 Acceptance Criteria

1. 3 new POST routes registered (dry-run only)
2. Route count updated in dev-check
3. Dry-run response shows: proposed action, content summary, category, duplicate score, protection status
4. P0/permanent items: dry-run shows "would be blocked" status
5. Memory files hash unchanged after dry-run
6. No events appended to `events.jsonl`
7. No `MEMORY.md` modification
8. Path redaction applied to dry-run output
9. DTO whitelisting applied
10. `dev-check` PASS
11. `memory-check` PASS
12. `compileall` PASS
13. Frontend lint/type-check/test/build PASS
14. Playwright smoke PASS
15. Production untouched
16. Worktree clean

### 9.7 Prerequisite

- Phase 0E-Release completed and pushed (no dependency on 1A/1B/1C)
- `evaluate_memory_auto_write()` in `runtime_memory_writer.py` confirmed available
- `format_memory_auto_json()` confirmed available for dry-run formatting

---

## 10. Phase 1E: Agent Prompt Preview / Dry-Run

### 10.1 Goal

Preview the Agent's prompt construction and context assembly in the WebUI. Show what the system prompt, tool list, memory context, and conversation history would look like before any LLM call. No actual LLM invocation occurs.

### 10.2 Scope

**New API routes (2 preview only):**

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/dev/v1/agent/prompt-preview` | Preview full prompt assembly without LLM call |
| POST | `/api/dev/v1/agent/dry-run` | Simulate agent run without LLM call or tool execution |

**New frontend components:**

- Prompt preview panel (system prompt, tools, context, history)
- Cost/token estimate display
- Context boundary visualization

### 10.3 Non-Goals

- No real agent run
- No LLM call
- No tool execution
- No message persistence
- No SSE streaming
- No conversation initiation

### 10.4 Write Capability

**None.** No LLM calls, no tool execution, no state mutation.

### 10.5 Safety Gates

1. Dev-only environment enforced
2. No LLM call in preview mode
3. Prompt preview shows: system prompt summary, tool list, context size, model selection
4. No API key exposure in preview
5. Cost/token estimate displayed (optional)
6. No tool execution in dry-run mode
7. Memory auto-write disabled by default
8. Conversation history boundary clearly defined
9. Cancellation mechanism available
10. Timeout configured
11. Rate limiting configured
12. Kill switch: `HERMES_WEBUI_ENABLE_AGENT_RUN=false` by default
13. Production fail-closed

### 10.6 Acceptance Criteria

1. 2 new POST routes registered (preview only)
2. Route count updated in dev-check
3. No LLM calls made
4. No tool calls made
5. Prompt content redacted (no API keys, secrets, full system prompt text)
6. Context boundary clearly defined and visible
7. Memory auto-write disabled
8. Production isolation: fail-closed if production home detected
9. `dev-check` PASS
10. `memory-check` PASS
11. `compileall` PASS
12. Frontend lint/type-check/test/build PASS
13. Playwright smoke PASS
14. Production untouched
15. Worktree clean

### 10.7 Prerequisite

- Phase 0E-Release completed and pushed (no dependency on 1A/1B/1C/1D)
- `agent/prompt_builder.py` confirmed available for prompt construction
- AIAgent constructor and `build_system_prompt()` confirmed accessible

---

## 11. Phase 1F: Agent Run Dev-Only Without Tools

### 11.1 Goal

Enable real Agent execution within the dev-home environment, but with tool execution disabled and Memory auto-write disabled. This introduces LLM calls for the first time in the WebUI.

### 11.2 Scope

**New API route (1 execute):**

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/dev/v1/agent/run` | Execute agent run (dev-only, no tools, no auto-memory) |

**New infrastructure:**

- SSE streaming via FastAPI (following CLAUDE.md SSE Constraints)
- Thread pool execution for `AIAgent.chat()`
- Bridge pattern for sync→async callback
- Single-generation constraint per session
- Client disconnect handling (`AIAgent.interrupt()`)

### 11.3 Non-Goals

- No tool execution
- No Memory auto-write
- No production execution
- No unbounded streaming
- No concurrent agent runs per session

### 11.4 Write Capability

**Yes — dev-home only, LLM call, explicit confirmation required.**

This is the first phase that invokes LLM calls. Tool execution remains disabled. Memory auto-write remains disabled. Only dev-home session data may be modified.

### 11.5 P1 Must-Resolve Before Implementation

1. **Double-persist question:** Verify whether `AIAgent.chat()` auto-persists messages. If yes, Web API must not duplicate persistence. (See CLAUDE.md Session Persistence Constraints.)
2. **SSE mechanism choice:** Decide between `stream_delta_callback` (AIAgent constructor) or `stream_callback` (chat/run_conversation parameter). Only one may be registered per consumer. (See CLAUDE.md SSE Constraints.)
3. **Rate limit / timeout / cancellation:** Define specific limits for Agent Run.
4. **Audit trail design:** Define audit event schema for agent runs.
5. **Kill switch:** Implement runtime enable/disable.

### 11.6 Safety Gates

1. Phase 1E completed and accepted
2. Explicit user confirmation required
3. Tool execution disabled by default (no tools in agent context)
4. Memory auto-write disabled
5. Rate limit enforced (requests per minute)
6. Timeout enforced (max generation time)
7. Cancellation available (client disconnect → `AIAgent.interrupt()`)
8. SSE streaming follows CLAUDE.md SSE Constraints:
   - Thread pool execution for `run_conversation()` / `chat()`
   - Bridge pattern: sync callbacks write to `asyncio.Queue` via `loop.call_soon_threadsafe()`
   - Single streaming entry: only one callback mechanism registered
   - Done event: emitted exactly once, triggered by background Future completing
   - Error propagation: background exceptions → `error` SSE event
   - Client disconnect: `AIAgent.interrupt()` called
   - Single-generation constraint: HTTP 409 for concurrent requests to same session
9. Session persistence: exactly once (no double-persist)
10. Audit event for each agent run
11. Production isolation: fail closed if production home detected
12. Kill switch active and visible

### 11.7 Acceptance Criteria

1. 1 new POST route registered (execute)
2. Route count updated in dev-check
3. Dev-only execution confirmed
4. Explicit confirmation required
5. Timeout enforced and tested
6. Cancel via client disconnect works
7. Rate limiting enforced
8. No tools in agent context
9. No memory auto-write
10. Prompt preview shown first
11. SSE streaming follows all CLAUDE.md constraints
12. Single-generation constraint enforced (409 for concurrent)
13. No double-persist verified
14. Audit event produced
15. `dev-check` PASS
16. `memory-check` PASS
17. `compileall` PASS
18. Frontend lint/type-check/test/build PASS
19. Playwright smoke PASS
20. Production untouched
21. Worktree clean

### 11.8 Prerequisite

- Phase 1E completed and accepted
- Double-persist question resolved
- SSE mechanism chosen
- Rate limit / timeout / cancellation defined
- Audit trail designed
- Kill switch implemented

---

## 12. Phase 1G: Tool Execution Safety Framework

### 12.1 Goal

Establish the safety framework for tool execution in the WebUI. This phase defines the allowlist, validation, audit, and kill switch infrastructure. It does **not** enable specific dangerous tools.

### 12.2 Scope

**New API routes (to be determined after full tool audit):**

Tool execution routes will only be defined after completing:
1. Full audit of `tools/registry.py` — every tool's registered name
2. Full audit of `toolsets.py` — which toolset each tool belongs to
3. Per-tool audit of input parameters, output format, and side effects
4. Definition of permanent prohibited list
5. Definition of initial allowlist (only confirmed-safe, side-effect-free tools)
6. Parameter schema validation framework
7. Output redaction framework

**New infrastructure:**

- Tool allowlist configuration
- Parameter schema validation
- Output redaction pipeline
- Per-tool timeout configuration
- Tool execution audit trail
- Kill switch per tool

### 12.3 Non-Goals

- No shell execution (`terminal`, `process` — permanently prohibited)
- No filesystem write (`write_file`, `patch` — permanently prohibited)
- No code execution (`execute_code` — permanently prohibited)
- No subagent spawning (`delegate_task` — permanently prohibited)
- No browser automation (`browser_*` — permanently prohibited)
- No desktop control (`computer_use` — permanently prohibited)
- No messaging (`send_message` — permanently prohibited)
- No cron management (`cronjob` — permanently prohibited)
- No skill mutation (`skill_manage` — permanently prohibited)
- No image generation (`image_generate` — permanently prohibited)
- No network access tools by default
- No delete operations by default
- No production operations of any kind

### 12.4 Write Capability

**Default: No.** Only allowlisted tools with confirmed low risk may be experimentally enabled. All others are default-deny.

### 12.5 Safety Gates

1. Phase 1F completed and accepted
2. Tool allowlist: only explicitly audited tools enabled
3. All permanently prohibited tools blocked at framework level
4. Argument schema validation enforced per tool
5. Output redaction applied to all tool responses
6. Timeout per tool execution enforced
7. Explicit confirmation before tool execution
8. Audit event for each tool execution
9. Kill switch: `HERMES_WEBUI_ENABLE_TOOL_EXECUTION=false` by default
10. Integration tests for each allowed tool

### 12.6 Acceptance Criteria

1. Tool audit complete and documented
2. Default deny: no tool executes unless explicitly allowlisted
3. Allowlist is static, not dynamically generated
4. Each allowed tool has: schema validation, timeout, output redaction, audit
5. Permanently prohibited tools cannot be enabled
6. Kill switch functional and visible
7. `dev-check` includes tool execution status
8. Forbidden route test for prohibited tools
9. `dev-check` PASS
10. `memory-check` PASS
11. `compileall` PASS
12. Frontend lint/type-check/test/build PASS
13. Playwright smoke PASS
14. Production untouched
15. Worktree clean

### 12.7 Prerequisite

- Phase 1F completed and accepted
- Full audit of `tools/registry.py` completed
- Full audit of `toolsets.py` completed
- Per-tool audit of parameters, output, and side effects completed
- Permanent prohibited list defined
- Initial allowlist defined
- Parameter schema validation framework implemented

---

## 13. Cross-Cutting Acceptance Criteria

Every Phase 1 subphase must satisfy all of the following:

### 13.1 Quality Gates

| Gate | Requirement |
|------|-------------|
| `memory-check` | PASS |
| `dev-check` | PASS (route count, forbidden routes, module checks updated) |
| `compileall` | PASS (`hermes_cli`, `hermes_state.py`, `agent`) |
| Frontend lint | PASS (`pnpm lint`) |
| Frontend type-check | PASS (`pnpm type-check`) |
| Frontend test | PASS (`pnpm test`, all tests) |
| Frontend build | PASS (`pnpm build`, artifacts gitignored) |
| Playwright smoke | PASS (new routes/themes verified) |
| OpenAPI spec | Static spec + runtime routes aligned |
| Forbidden routes | Tests verify unlisted routes return 405/404 |

### 13.2 Side-Effect Validation

| For dry-run phases | For execute phases |
|--------------------|--------------------|
| Review files hash unchanged | Review files hash changes match expected operation |
| Memory files hash unchanged | Memory files hash changes match expected operation |
| `state.db` hash unchanged | `state.db` changes match expected operation |
| `events.jsonl` unchanged | `events.jsonl` entries match expected audit events |
| No new files created | New files match expected artifacts |

### 13.3 Production Safety

| Check | Requirement |
|-------|-------------|
| Production Gateway PID 1717 | Still running, not stopped/restarted/replaced |
| `~/.hermes` | Not accessed or modified |
| Production `state.db` | Not accessed |
| `setup-hermes.sh` | Not run |
| Global `hermes` command | Not modified |
| Dev Gateway | Not started unless explicitly required by phase |
| Dashboard | Not started |
| Network binding | `127.0.0.1` only |

### 13.4 Documentation

| Document | Requirement |
|----------|-------------|
| Subphase closure document | Exists with full scope/results/tests |
| Implementation plan updated | Status reflects completion |
| OpenAPI spec updated | New routes documented |
| dev-check updated | New route counts and checks |

### 13.5 Git Hygiene

| Check | Requirement |
|-------|-------------|
| Branch | `dev-huangruibang` |
| Working tree | Clean after commit |
| No sensitive files staged | No `state.db`, `.env`, keys, tokens, logs, etc. |
| No build artifacts staged | No `dist/`, `tsbuildinfo`, `node_modules` |
| No test artifacts staged | No `playwright-report`, `test-results`, screenshots |
| No push until release | Each subphase commits locally only |

---

## 14. Risk Register

### 14.1 P0 — Blockers (Must Resolve Before Phase 1)

None identified at Phase 1-00 planning time.

### 14.2 P1 — Must Resolve Before Specific Phase

| ID | Risk | Phase | Mitigation |
|----|------|-------|-----------|
| P1-1 | Double-persist: `AIAgent.chat()` may auto-persist messages, causing Web API duplicate persistence | 1F | Audit `run_agent.py` `_persist_session()` before 1F. Document whether auto-persist is on/off. Design Web API persistence accordingly. |
| P1-2 | SSE mechanism choice: `stream_delta_callback` vs `stream_callback` overlapping text | 1F | Audit AIAgent constructor and `chat()` method. Choose one mechanism. Document choice. Never wire both. |
| P1-3 | Tool audit incomplete: tool names in CLAUDE.md may not match actual `registry.register()` names | 1G | Complete full audit of `tools/registry.py` and `toolsets.py` before 1G. Never assume tool safety from names alone. |
| P1-4 | Review approve triggers Memory Write with no undo | 1C | Document rollback strategy (or explicit irreversibility). Require dry-run first. Show impact scope. |
| P1-5 | Concurrent agent runs on same session corrupt state | 1F | Implement single-generation constraint (HTTP 409). Test concurrent access rejection. |
| P1-6 | Client disconnect during agent run leaves orphan thread | 1F | Implement `AIAgent.interrupt()` on disconnect. Verify thread cleanup. |

### 14.3 P2 — Should Resolve During Phase 1

| ID | Risk | Phase | Mitigation |
|----|------|-------|-----------|
| P2-1 | Audit log storage format undefined | 1C+ | Define exact storage location and format in dev-home |
| P2-2 | Kill switch granularity unclear | 1B+ | Determine per-capability vs grouped kill switches |
| P2-3 | Rate limiting strategy undefined | 1F | Define specific rate limits for Agent Run |
| P2-4 | Cost tracking not implemented | 1F | Determine how to track/display LLM token costs |
| P2-5 | Review queue undo strategy not documented | 1C | Document whether review approve/reject is reversible |
| P2-6 | Large review queue performance | 1A | Define pagination limits and lazy loading |
| P2-7 | Memory Writer evaluation may be slow | 1D | Set timeouts on dry-run operations |

---

## 15. Release Strategy

### 15.1 Per-Subphase Release

Each subphase follows the same release pattern:

```
Implement → Test → Gate → Commit (local) → [Next Subphase]
```

### 15.2 Phase 1-Release

Phase 1-Release is the final gate after all subphases (1A through 1G) are completed:

1. Run full quality gate (memory-check, dev-check, compileall, all tests)
2. Verify clean working tree
3. Verify production safety
4. Push all Phase 1 commits to `origin/dev-huangruibang`

### 15.3 Push Policy

- **1A through 1G:** Commit locally only. Do NOT push.
- **1-Release:** Push all Phase 1 commits in one batch after final verification.
- No subphase may push independently.

---

## 16. Phase 1-00 Scope (This Task)

### In Scope

1. Verify repository state and Phase 0E completion
2. Review and confirm Phase 1 Safety Boundary
3. Define Phase 1 overall goal, non-goals, and principles
4. Freeze Phase 1 subphase roadmap (1A through 1G)
5. Define scope, non-goals, and acceptance criteria for each subphase
6. Define which subphases allow write operations and which do not
7. Define safety gates for each subphase
8. Define cross-cutting acceptance criteria
9. Define risk register
10. Create Phase 1 planning document (this document)
11. Create Phase 1 implementation plan document
12. Update Phase 0E documents with next-phase pointers
13. Run verification gates (memory-check, dev-check, compileall)
14. Commit locally, do NOT push

### Strictly Out of Scope

- New business API routes
- Write operations of any kind
- Agent Run / LLM calls / Tool execution
- SSE / WebSocket implementation
- Memory write/update/archive
- Review Queue approve/reject
- Session/message creation
- File browsing/upload/delete
- Gateway or Dashboard integration
- Production environment changes
- Any modification to `~/.hermes`
- Phase 1A implementation

### Permitted File Modifications

| File | Action |
|------|--------|
| `docs/webui/phase-1-00-planning-and-scope.md` | **New** — This document |
| `docs/webui/phase-1-implementation-plan.md` | **New** — Implementation plan |
| `docs/webui/phase-0e-06-phase-1-safety-boundary.md` | **Optional** — Add link to Phase 1-00 |
| `docs/webui/phase-0e-implementation-plan.md` | **Optional** — Add next-phase pointer |

No other files may be modified.

---

## 17. Acceptance Conclusion

Phase 1-00 completed when:

1. ✅ Repository state verified (branch, HEAD, remote sync, clean worktree)
2. ✅ Phase 0E completion confirmed (all subphases completed and pushed)
3. ✅ Phase 1 Safety Boundary reviewed and confirmed
4. ✅ Phase 1 goal, non-goals, and principles defined
5. ✅ Phase 1 subphase roadmap frozen (1A through 1G)
6. ✅ Each subphase has scope, non-goals, write capability, safety gates, acceptance criteria
7. ✅ Cross-cutting acceptance criteria defined
8. ✅ Risk register defined (P0, P1, P2)
9. ✅ Release strategy defined
10. ✅ Planning document created
11. ✅ Implementation plan created
12. ✅ Phase 0E documents updated with next-phase pointers
13. ✅ memory-check PASS
14. ✅ dev-check PASS
15. ✅ compileall PASS
16. ✅ No business code modified
17. ✅ No new API routes added
18. ✅ Local commit created
19. ✅ Not pushed
20. ✅ Working tree clean
21. ✅ Production environment unaffected

---

## 18. Next Task

**Phase 1A: Review Queue Read-Only Panel**

This task does NOT automatically start Phase 1A.
