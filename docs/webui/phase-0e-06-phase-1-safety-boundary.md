# Phase 0E-06: Phase 1 Safety Boundary

**Status:** Completed
**Date:** 2026-06-08
**Branch:** dev-huangruibang
**Base commit:** fa2dc5d8f (Phase 0E-05 dev-check enhancement)

---

## 1. Background

Phase 0C through 0E established a fully read-only Dev WebUI with strong production isolation, path redaction, and comprehensive test coverage (803 tests). Before any Phase 1 work introduces write operations, Agent Run, SSE streaming, or tool execution, this document defines the safety boundary that all Phase 1 work must satisfy.

This document serves as the definitive safety reference for Hermes Dev WebUI Phase 1. No Phase 1 write capability may be enabled without satisfying every applicable gate defined here.

---

## 2. Current Read-Only Baseline

### 2.1 Route Inventory

The Dev WebUI currently exposes exactly **11 read-only API routes**:

| Method | Path | Classification | Description |
|--------|------|----------------|-------------|
| GET | `/api/dev/v1/status` | READ | System status and environment verification |
| GET | `/api/dev/v1/files/status` | READ | File browsing availability (returns `available: false`) |
| GET | `/api/dev/v1/sessions` | READ | Session list with pagination |
| GET | `/api/dev/v1/sessions/{sessionId}` | READ | Session detail |
| GET | `/api/dev/v1/sessions/{sessionId}/messages` | READ | Session messages with pagination |
| GET | `/api/dev/v1/memory/status` | READ | Memory system status |
| GET | `/api/dev/v1/memory/categories` | READ | Memory categories list |
| GET | `/api/dev/v1/memory/items` | READ | Memory items list |
| GET | `/api/dev/v1/memory/items/{memoryId}` | READ | Memory item detail |
| POST | `/api/dev/v1/context/preview` | READ | Memory context preview (side-effect-free, no LLM call) |
| GET | `/api/dev/v1/agent/status` | READ | Agent configuration status |

**All 11 routes are strictly read-only.** No write operations, no state mutation, no LLM calls, no tool execution, no file modification.

### 2.2 Current Safety Mechanisms

| Mechanism | Implementation |
|-----------|---------------|
| Environment isolation | `dev_web_config.py` enforces `HERMES_HOME=/Users/huangruibang/Code/hermes-home-dev` and source root validation at startup |
| Local-only binding | FastAPI binds exclusively to `127.0.0.1` |
| CORS restriction | Only `http://127.0.0.1:5180` allowed |
| Path redaction | All absolute paths (`/Users/`, `/home/`, `file://`) replaced with `[local-path]` |
| DTO whitelisting | Only explicitly approved fields in API responses |
| Input validation | Session ID regex, memory ID pattern, pagination limits |
| Sensitive field filtering | API keys, base URLs, credentials stripped from agent status |
| No LLM calls | Context preview simulates without model calls |
| No side effects | Every operation guaranteed to leave no persistent state changes |
| Production protection | `enforce_dev_environment()` fails closed if source root or HERMES_HOME is wrong |

### 2.3 Confirmed Write-Zero State

- `state.db` in dev-home: **unchanged by any WebUI operation**
- `MEMORY.md` in dev-home: **unchanged**
- All `memory/` files in dev-home: **unchanged** (SHA-256 verified at 0C/0D/0E closure)
- Production `~/.hermes`: **never accessed**
- Production `state.db`: **never accessed**
- Production Gateway PID 1717: **never stopped, restarted, or replaced**

---

## 3. Risk Taxonomy

### 3.1 P0 — Permanently Prohibited in WebUI

These capabilities must **never** be exposed through the Dev WebUI, regardless of phase:

| Capability | Reason |
|------------|--------|
| Production environment write (`~/.hermes`) | Violates fundamental isolation |
| Production `state.db` access | Violates fundamental isolation |
| Production Gateway stop/restart/replace | Operational safety |
| Production Memory read or write | Privacy and isolation |
| Unconfirmed LLM call | Cost, side effects, no audit trail |
| Unconfirmed Tool execution | Security, side effects |
| Unconfirmed Memory write | Data integrity, no audit trail |
| Unconfirmed Review approve/reject | Data integrity, no rollback |
| Unconfirmed file deletion | Irreversible |
| Unconfirmed batch operations | Blast radius too large |
| Cross-user / cross-environment operations | Isolation boundary violation |
| Write operations without audit trail | Accountability |

### 3.2 High-Risk — Requires Dedicated Phase with Full Gate

Each of these capabilities must have its **own phase, own design document, own test plan, and own acceptance criteria**:

| Capability | Primary Risk | Existing Code |
|------------|-------------|---------------|
| Agent Run (LLM call) | Cost, side effects, uncontrolled tool use | `agent/conversation_loop.py` |
| Tool Execution | Security, filesystem access, network access | `tools/*.py`, `model_tools.py` |
| Memory Write | Data integrity, no undo | `agent/runtime_memory_writer.py` → `memory_router.create_memory_item()` |
| Memory Update | Overwriting existing data, protected items | `agent/runtime_memory_writer.py` → `memory_router.update_memory_item()` |
| Memory Archive | Data loss, permanent removal | `memory_router` (archive logic) |
| Review Queue approve | Data mutation (triggers Memory Write or Update) | `agent/memory_review_queue.py` → `approve_review_item()` |
| Review Queue reject | Permanent rejection of memory candidate | `agent/memory_review_queue.py` → `reject_review_item()` |
| Review Queue enqueue | New review items in queue | `agent/memory_review_queue.py` → `enqueue_review_item()` |
| Session Write | Database mutation | `hermes_state.py` → `SessionDB` |
| Message Send | API cost, external side effects | `run_agent.py` → `AIAgent.chat()` |
| File Browse | Path traversal, information exposure | Not yet implemented |
| File Upload | Arbitrary file write | Not yet implemented |
| File Delete | Irreversible data loss | Not yet implemented |
| Gateway Control | Operational disruption | `gateway/run.py` |
| Dashboard Control | Operational disruption | Not yet implemented |

### 3.3 Medium-Risk — Requires Boundary Definition

| Capability | Notes |
|------------|-------|
| Review Queue read-only panel | Read-only access to review items |
| Agent status extended metadata | More detailed read-only config display |
| Memory preview expanded | Larger context limits (still no LLM) |
| Session advanced filtering | More query parameters (still read-only) |
| Diagnostic logs read-only | Read-only log access |
| Dev health metrics | Read-only metrics display |

### 3.4 Low-Risk — Continue Current Pattern

| Capability | Notes |
|------------|-------|
| Read-only status display | Current behavior, safe to extend |
| Read-only configuration summary | Current behavior, safe to extend |
| Read-only OpenAPI display | Current behavior |
| Read-only smoke/dev-check result display | Engineering governance display |
| Read-only documentation links | Navigation aids |

---

## 4. Phase 1 Non-Goals

Phase 1 **does not** aim to:

1. Deploy the Dev WebUI to any server or production environment
2. Enable public or network access (remains `127.0.0.1` only)
3. Replace the CLI as the primary agent interface
4. Modify the production environment in any way
5. Introduce any capability not listed in the Phase 1 candidate sequence (Section 13)
6. Enable multiple concurrent users
7. Remove or weaken any existing safety mechanism

---

## 5. Default Deny Model

### Principle

All new capabilities are **disabled by default**. No route, action, button, or command may be active without an explicit, documented allowlist entry.

### Rule

```
No allowlist entry → No execution.
```

### Implementation Requirements

1. Every new API route must be registered in an explicit route allowlist
2. Every new UI action must be gated behind a feature flag or allowlist check
3. The allowlist must be a **static configuration**, not dynamically generated
4. The backend must enforce the allowlist independently of frontend state
5. `dev-check` must verify that no routes exist outside the allowlist

### Verification

- `dev-check` OpenAPI route count check must be updated when new routes are added
- Playwright smoke tests must verify disabled UI elements remain disabled
- Forbidden route tests must verify that unlisted routes return 405 or 404

---

## 6. Dry-Run First Model

### Principle

Every write operation must support a **dry-run mode** that validates the operation without mutating any state. Dry-run must be the **default** for the first subphase of any write capability.

### Dry-Run Requirements

A dry-run response must include:

| Field | Description |
|-------|-------------|
| `wouldModify` | List of resources that would be modified |
| `wouldWrite` | List of files that would be written |
| `wouldCall` | List of services/APIs that would be called |
| `triggersLLM` | Whether the operation would invoke an LLM call |
| `triggersTool` | Whether the operation would invoke tool execution |
| `affectsMemory` | Whether the operation modifies Memory data |
| `affectsSession` | Whether the operation modifies Session data |
| `affectsGateway` | Whether the operation modifies Gateway state |
| `affectsProduction` | Always `false` in dev-only mode; if `true`, refuse immediately |
| `estimatedCost` | Token/cost estimate if LLM is involved |

### Rule

```
No dry-run → No real execution.
```

### Phase Progression

For each write capability:

1. **Phase X-1:** Dry-run only (no real execution possible)
2. **Phase X-2:** Dry-run + explicit confirmation → dev-only execution
3. **Phase X-3 (if applicable):** Production-like validation (still dev-only, but with production-isolation checks)

---

## 7. Dev-Only Isolation

### Principle

All Phase 1 experimental capabilities must operate exclusively within the development environment. The production environment is not a "warning then proceed" — it is a hard failure.

### Hard Boundaries

| Boundary | Value | Enforcement |
|----------|-------|-------------|
| Dev HERMES_HOME | `/Users/huangruibang/Code/hermes-home-dev` | `enforce_dev_environment()` at API startup |
| Forbidden home | `/Users/huangruibang/.hermes` | Path comparison in all write operations |
| Forbidden state.db | `/Users/huangruibang/.hermes/state.db` | Path comparison |
| Forbidden Gateway PID | 1717 | PID guard in all process operations |
| Binding | `127.0.0.1` only | FastAPI startup configuration |
| Forbidden ports | 5182, 0.0.0.0, ::, LAN IPs | Network binding check |

### Fail-Closed Rule

```
If production-like home is detected → Refuse immediately.
Not warn. Not confirm. Refuse.
```

### Verification

- Every write operation must call `enforce_dev_environment()` or equivalent
- `dev-check` must verify isolation is active
- Tests must confirm that production paths are rejected

---

## 8. Explicit User Confirmation

### Principle

All write operations require explicit user confirmation through the UI. Confirmation is not optional, not bypassable, and not auto-dismissed.

### WebUI Confirmation Requirements

Every write operation must present:

| Element | Description |
|---------|-------------|
| Operation description | What will happen |
| Risk statement | What could go wrong |
| Impact scope | Which resources are affected |
| Dry-run result | Preview of changes |
| Confirm button | Explicit "Yes, execute" action |
| Cancel button | Always available, default focus |

**The cancel button must have default focus.** Users must actively choose to proceed.

### CLI Confirmation Requirements

| Element | Description |
|---------|-------------|
| `--dry-run` | Default behavior for all write commands |
| `--confirm` | Required flag for real execution |
| `--yes -y` | Explicit override for scripted use |
| Interactive prompt | Required for destructive operations |

### Prohibited Patterns

- Auto-confirmation after timeout
- Confirmation bypass via URL parameter
- Single-click confirmation for destructive operations
- Pre-checked confirmation checkboxes
- Confirmation dialogs that default to "proceed"

---

## 9. Allowlist Model

### Principle

Phase 1 may only expose actions that are **explicitly listed** in a static allowlist. The allowlist is the source of truth for what is permitted.

### Allowlist Structure

```yaml
# Conceptual structure — actual implementation TBD in Phase 1
dev-webui-phase1:
  allowedActions:
    - review.read
    - review.list
    - review.show
    - memory.preview
    - context.preview
  deniedActions:
    - memory.write
    - memory.update
    - memory.archive
    - review.approve
    - review.reject
    - agent.run
    - tool.execute
    - session.write
    - message.send
    - file.browse
    - file.upload
    - file.delete
    - gateway.control
```

### Allowlist Rules

1. Actions not in `allowedActions` are treated as denied
2. `deniedActions` is an explicit deny list for documentation and test purposes
3. The backend must reject any action not in `allowedActions`
4. The frontend must not render UI for denied actions
5. `dev-check` must verify the allowlist is consistent with OpenAPI routes

---

## 10. Audit Trail Requirements

### Principle

Every real write operation (not dry-run) must produce an audit event.

### Audit Event Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `timestamp` | ISO 8601 | Yes | When the operation occurred |
| `requestId` | string | Yes | Unique request identifier |
| `actor` | string | Yes | `dev-webui` or `cli` |
| `environment` | string | Yes | `dev` (never `production`) |
| `action` | string | Yes | The action identifier (e.g., `review.approve`) |
| `target` | string | Yes | Target resource ID (e.g., memory ID, session ID) |
| `dryRun` | boolean | Yes | Whether this was a dry-run |
| `beforeSummary` | string | Yes | State before operation (summary, not full content) |
| `afterSummary` | string | No | State after operation (not available for dry-run) |
| `result` | string | Yes | `success`, `failed`, `cancelled` |
| `errorCode` | string | No | Error code if failed |

### Audit Redaction Rules

Audit events must **never** contain:

- API keys, tokens, cookies
- Full user messages or assistant messages
- Full local file paths
- Full system prompt content
- Full Memory record content
- LLM prompt or response text
- Secret environment variables

### Audit Storage

- Audit events stored in dev-home only (`/Users/huangruibang/Code/hermes-home-dev/`)
- Append-only log (no modification or deletion)
- Rotation policy defined in Phase 1 implementation

---

## 11. Kill Switch Requirements

### Principle

Every Phase 1 write capability must have a kill switch that can immediately disable it without code changes.

### Kill Switch Mechanisms

| Mechanism | Scope |
|-----------|-------|
| Environment variable | `HERMES_WEBUI_ENABLE_<CAPABILITY>=false` |
| Config flag | YAML configuration option |
| `dev-check` visibility | Kill switch status reported in dev-check |
| Runtime status display | Current capability status visible in WebUI status bar |

### Kill Switch Rules

1. **Default state: OFF** — capabilities are disabled until explicitly enabled
2. **Kill switch is additive** — enabling a capability requires setting the flag; disabling is removing it
3. **No restart required** — kill switch takes effect on next request (or immediately if feasible)
4. **Kill switch is visible** — `dev-check` and `/api/dev/v1/status` report current capability state

---

## 12. Route Safety Rules

### New Route Requirements

Every new API route added in Phase 1 must:

1. Be registered in the route allowlist (Section 9)
2. Call `enforce_dev_environment()` at the handler level
3. Support a `?dry_run=true` query parameter (for write operations)
4. Require explicit confirmation in the request body (for write operations)
5. Produce an audit event (for write operations)
6. Have at least 2 tests: one success, one boundary rejection
7. Have a forbidden-route test confirming no unlisted routes exist
8. Be documented in the OpenAPI spec

### Forbidden Routes (Permanent)

These routes must **never** be registered in the Dev WebUI API:

| Route | Reason |
|-------|--------|
| `POST /api/dev/v1/gateway/*` | Gateway control prohibited |
| `POST /api/dev/v1/production/*` | Production access prohibited |
| `DELETE /api/dev/v1/*` | DELETE on any resource |
| `POST /api/dev/v1/files/upload` | File upload prohibited |
| `POST /api/dev/v1/files/delete` | File deletion prohibited |
| `POST /api/dev/v1/tools/execute` | Tool execution requires dedicated phase |
| `POST /api/dev/v1/agent/run` | Agent run requires dedicated phase |

---

## 13. UI Safety Rules

### General UI Safety

1. **Disabled state:** All write-capable UI elements must render as disabled until the corresponding backend capability is confirmed active via `/api/dev/v1/status`
2. **Status polling:** The WebUI must check capability status at startup and periodically (not just on user action)
3. **No hidden buttons:** Write-capable buttons must be visible but disabled (not hidden) — this communicates capability availability
4. **Confirmation flow:** All write actions must go through a confirmation dialog (Section 8)
5. **Error display:** Failed write operations must display the error with actionable guidance

### Read-Only Indicator

The current "Read only" status indicator in the top bar must remain until at least one write capability is enabled. When write capabilities are active, the indicator must change to show which capabilities are enabled.

---

## 14. CLI Safety Rules (Dual-Channel)

### Principle

High-risk capabilities must have **both** CLI and WebUI safety. Backend enforcement is mandatory — frontend hiding is insufficient.

### Requirements

1. Every write API route must validate safety **independently** of the request source
2. The same allowlist applies to CLI and WebUI
3. CLI commands must have `--dry-run` as default behavior
4. CLI commands for dangerous operations must require explicit `--confirm` or interactive prompt
5. WebUI and CLI must produce the same audit events

### Prohibited

- Relying solely on frontend button hiding for safety
- Assuming requests come only from the WebUI
- Skipping backend validation because "the UI already checked"

---

## 15. Testing Requirements

### Per-Capability Test Minimums

Before any write capability is enabled, the following tests must exist:

| Test Type | Minimum Coverage |
|-----------|-----------------|
| Unit tests | Success path, failure path, boundary conditions |
| Integration tests | End-to-end with real dev-home data |
| OpenAPI route boundary tests | Route exists, route rejects invalid input |
| Forbidden route tests | Unlisted routes return 405/404 |
| Side-effect hash tests | SHA-256 of state.db and memory files unchanged after dry-run |
| Browser smoke tests | Playwright test for the new UI element |
| Production isolation tests | Production paths are rejected |
| `dev-check` coverage | New capability visible in dev-check output |

### Regression Requirements

- All existing tests (803+) must continue to pass
- No regression in existing safety mechanisms
- No regression in read-only behavior

---

## 16. Capability-Specific Gates

### 16.1 Review Queue Read-Only (Phase 1A)

**Gate requirements:**
- [ ] Dev-only environment enforced
- [ ] Only GET routes for review items (list, show, status)
- [ ] No approve/reject/enqueue routes registered
- [ ] Review item content follows DTO whitelisting
- [ ] Path redaction applied to review item paths
- [ ] No modification to review queue files on disk
- [ ] `dev-check` includes review queue read-only check
- [ ] Playwright smoke test for Review panel
- [ ] Forbidden route test: `POST /api/dev/v1/reviews/*` returns 405

### 16.2 Review Queue Approve/Reject Dry-Run (Phase 1B)

**Gate requirements:**
- [ ] Phase 1A completed and accepted
- [ ] `?dry_run=true` is the default (no real execution possible)
- [ ] Dry-run response shows proposed action, target memory ID, duplicate/protected checks
- [ ] P0 and permanent memory items cannot be approved for update
- [ ] Kill switch: `HERMES_WEBUI_ENABLE_REVIEW_APPROVE=false` by default
- [ ] Audit event produced even for dry-run
- [ ] CLI parity: `hermes review approve --dry-run`
- [ ] No modification to review queue files on disk in dry-run mode
- [ ] Side-effect hash test: review files unchanged after dry-run
- [ ] Forbidden route test: real approve without dry_run returns 403

### 16.3 Review Queue Approve/Reject Dev-Only Execute (Phase 1C)

**Gate requirements:**
- [ ] Phase 1B completed and accepted
- [ ] Explicit confirmation required (request body + UI dialog)
- [ ] Only dev-home review queue accessible
- [ ] P0/permanent protection enforced at backend level
- [ ] Real audit event produced on execution
- [ ] Before/after summary in audit event
- [ ] Undo/rollback strategy documented (or explicit "no rollback" warning)
- [ ] Kill switch active and visible in dev-check
- [ ] CLI parity: `hermes review approve --confirm`
- [ ] Playwright smoke test for approve/reject flow
- [ ] Integration test with real review queue data

### 16.4 Memory Writer Dry-Run Panel (Phase 1D)

**Gate requirements:**
- [ ] Dev-only environment enforced
- [ ] No real memory write possible (dry-run only)
- [ ] Dry-run shows: proposed memory content, target category, duplicate detection score
- [ ] Category allowlist enforced (only active categories)
- [ ] P0/permanent protection enforced
- [ ] No modification to MEMORY.md, indexes, records, or events.jsonl
- [ ] Side-effect hash test: all memory files unchanged
- [ ] `dev-check` includes memory write dry-run check
- [ ] Kill switch: `HERMES_WEBUI_ENABLE_MEMORY_WRITE=false` by default

### 16.5 Agent Prompt Preview / Dry-Run (Phase 1E)

**Gate requirements:**
- [ ] Dev-only environment enforced
- [ ] No LLM call in dry-run mode
- [ ] Prompt preview shows: system prompt summary, tool list, context size, model selection
- [ ] No API key exposure in preview
- [ ] Cost/token estimate displayed
- [ ] No tool execution in dry-run mode
- [ ] Memory auto-write disabled by default
- [ ] Conversation history boundary clearly defined
- [ ] Cancellation mechanism available
- [ ] Timeout configured
- [ ] Rate limiting configured
- [ ] Kill switch: `HERMES_WEBUI_ENABLE_AGENT_RUN=false` by default

### 16.6 Agent Run Dev-Only Without Tools (Phase 1F)

**Gate requirements:**
- [ ] Phase 1E completed and accepted
- [ ] Explicit user confirmation required
- [ ] Tool execution disabled by default (no tools in agent context)
- [ ] Memory auto-write disabled
- [ ] Rate limit enforced (requests per minute)
- [ ] Timeout enforced (max generation time)
- [ ] Cancellation available (client disconnect → `AIAgent.interrupt()`)
- [ ] SSE streaming follows CLAUDE.md SSE Constraints (thread pool, bridge pattern, single streaming entry)
- [ ] Single-generation constraint (HTTP 409 for concurrent requests to same session)
- [ ] Session persistence: exactly once (no double-persist — verify `AIAgent.chat()` auto-persists or Web API persists, never both)
- [ ] Audit event for each agent run
- [ ] Production isolation: fail closed if production home detected
- [ ] Kill switch active and visible
- [ ] Integration tests with real agent run
- [ ] Side-effect validation: expected state.db changes, no unexpected memory changes

### 16.7 Tool Execution Safety Framework (Phase 1G)

**Gate requirements:**
- [ ] Phase 1F completed and accepted
- [ ] Tool allowlist: only explicitly audited tools enabled (requires `tools/registry.py` audit per CLAUDE.md P0 Tool Execution Policy)
- [ ] No shell/system tools by default (`terminal`, `process` permanently prohibited)
- [ ] No filesystem write tools by default (`write_file`, `patch` permanently prohibited)
- [ ] No code execution by default (`execute_code` permanently prohibited)
- [ ] No subagent spawning (`delegate_task` permanently prohibited)
- [ ] No browser automation (`browser_*` permanently prohibited)
- [ ] No desktop control (`computer_use` permanently prohibited)
- [ ] No messaging (`send_message` permanently prohibited)
- [ ] No cron management (`cronjob` permanently prohibited)
- [ ] No skill mutation (`skill_manage` permanently prohibited)
- [ ] No image generation (`image_generate` permanently prohibited)
- [ ] Argument schema validation enforced
- [ ] Output redaction applied
- [ ] Timeout per tool execution
- [ ] Explicit confirmation before tool execution
- [ ] Audit event for each tool execution
- [ ] Kill switch: `HERMES_WEBUI_ENABLE_TOOL_EXECUTION=false` by default
- [ ] Integration tests for each allowed tool

---

## 17. Recommended Phase 1 Sequence

Based on risk level and dependency analysis:

| Phase | Capability | Risk Level | Dependencies |
|-------|-----------|------------|-------------|
| **1A** | Review Queue Read-Only Panel | Low | None |
| **1B** | Review Queue Approve/Reject Dry-Run | Medium | 1A |
| **1C** | Review Queue Approve/Reject Dev-Only Execute | High | 1B |
| **1D** | Memory Writer Dry-Run Panel | Medium | None |
| **1E** | Agent Prompt Preview / Dry-Run | Medium | None |
| **1F** | Agent Run Dev-Only Without Tools | High | 1E |
| **1G** | Tool Execution Safety Framework | High | 1F |

**Progression principle:**

```
Read-only first → Dry-run second → Dev-only execute third → High-risk last
```

Each phase is independently gated. Failure to meet any gate requirement blocks progression.

---

## 18. Session / Message / File / Gateway Operation Boundaries

### 18.1 Session Write

- Default: disabled
- Dev-only `state.db`
- Transaction safety required (SQLite WAL mode)
- Backup/snapshot before write
- No production `state.db` access
- CSRF/confirmation for browser-initiated writes
- Message content redaction policy for audit logs
- Must resolve double-persist question before implementation

### 18.2 Message Send

- Default: disabled
- Tied to Agent Run (Phase 1F)
- Requires SSE streaming infrastructure
- Rate limiting required
- Content redaction for audit logs

### 18.3 File Browse

- Default: disabled
- Root allowlist required (only dev-home and source-root)
- No production home paths
- No arbitrary path traversal
- Path redaction in responses
- Download disabled by default

### 18.4 File Upload / Delete

- Default: disabled
- Each requires dedicated phase
- Upload: validation, quarantine, size limits
- Delete: dry-run mandatory, confirmation mandatory, audit mandatory

### 18.5 Gateway / Dashboard Operations

- Default: disabled
- Gateway control permanently prohibited in WebUI (CLI only)
- Dashboard integration deferred indefinitely
- Read-only gateway status display may be considered (medium risk)

---

## 19. Existing Safety Mechanisms to Reuse

The following mechanisms are already implemented and must be preserved/reused in Phase 1:

| Mechanism | Location | Reuse For |
|-----------|----------|-----------|
| `enforce_dev_environment()` | `dev_web_config.py` | All Phase 1 routes |
| Path redaction (`redact_local_paths`) | `dev_web_api.py` | All data responses |
| DTO whitelisting | `dev_web_schemas.py` | All response models |
| CORS restriction | `dev_web_middleware.py` | All routes |
| `127.0.0.1` binding | FastAPI startup | Service lifetime |
| Memory P0/permanent protection | `runtime_memory_writer.py` | Memory write/update |
| Review queue fingerprint dedup | `memory_review_queue.py` | Review queue operations |
| Atomic JSON writes | `memory_review_queue.py` | Review queue persistence |
| `dev-check` WebUI section | `hermes_cli/main.py` | All new capabilities |
| OpenAPI route count verification | `dev-check` | Route allowlist |
| Forbidden route verification | `dev-check` | Route safety |
| Dry-run in memory writer | `runtime_memory_writer.py` | Memory write preview |
| Review approve dry-run | `memory_review_queue.py` | Review approve preview |
| Session ID regex validation | `dev_web_api.py` | Session operations |
| Memory ID pattern validation | `dev_web_api.py` | Memory operations |

---

## 20. Acceptance Criteria

Phase 0E-06 is complete when:

1. ✅ Phase 1 Safety Boundary document exists at `docs/webui/phase-0e-06-phase-1-safety-boundary.md`
2. ✅ Default deny principle documented
3. ✅ Dry-run first principle documented
4. ✅ Dev-only isolation principle documented
5. ✅ Explicit confirmation principle documented
6. ✅ Allowlist principle documented
7. ✅ Audit trail requirements documented
8. ✅ Kill switch requirements documented
9. ✅ No production by design principle documented
10. ✅ Test-before-enable principle documented
11. ✅ Review Queue gate defined
12. ✅ Memory write/update/archive gate defined
13. ✅ Agent Run / LLM gate defined
14. ✅ Tool Execution gate defined
15. ✅ Session/Message/File/Gateway operation boundaries defined
16. ✅ Phase 1 recommended sequence provided
17. ✅ No write operations implemented
18. ✅ No new API routes added
19. ✅ No business code modified
20. ✅ `memory-check` PASS
21. ✅ `dev-check` PASS
22. ✅ `compileall` PASS
23. ✅ Local commit created
24. ✅ Not pushed
25. ✅ Working tree clean
26. ✅ Production environment unaffected

---

## 21. Risks and Open Questions

### P0 (Blockers)

None.

### P1 (Must resolve before Phase 1)

1. **Double-persist question:** Before implementing Agent Run, must verify whether `AIAgent.chat()` auto-persists messages. If yes, the Web API must not duplicate persistence. (See CLAUDE.md Session Persistence Constraints.)
2. **SSE mechanism choice:** Before implementing SSE streaming, must decide whether to use `stream_delta_callback` (AIAgent constructor) or `stream_callback` (chat/run_conversation parameter). Only one must be registered per consumer. (See CLAUDE.md SSE Constraints.)
3. **Tool audit requirement:** Before any tool is enabled in WebUI, must complete full audit of `tools/registry.py` (registered names) and `toolsets.py` (toolset membership) per CLAUDE.md P0 Tool Execution Policy.

### P2 (Should resolve during Phase 1)

1. **Audit log storage format:** Define exact storage location and format for audit events in dev-home.
2. **Kill switch granularity:** Determine whether kill switches should be per-capability or grouped.
3. **Rate limiting strategy:** Define specific rate limits for Agent Run and Tool Execution.
4. **Cost tracking:** Determine how to track and display LLM token costs in the WebUI.
5. **Review queue undo strategy:** Document whether review approve/reject is reversible and how.

---

## 22. Conclusion

**Phase 0E-06 completed.** Phase 1 safety boundary is now defined.

Any future write operation introduced in the Dev WebUI must satisfy the principles defined in this document:

- **Default deny:** All capabilities off until explicitly enabled
- **Dry-run first:** No execution without preview
- **Dev-only isolation:** Production is fail-closed, not warn-then-proceed
- **Explicit confirmation:** Users must actively choose to proceed
- **Allowlist:** Only explicitly listed actions are permitted
- **Audit trail:** Every real write operation is recorded
- **Kill switch:** Every capability can be immediately disabled
- **Test-before-enable:** Comprehensive tests are a prerequisite, not an afterthought

The next subphase is **0E-Release: Final Verification & Push**.

---

## 23. Phase 1 Planning Reference

Phase 1 planning and scope freeze is documented at:

- **Planning document:** `docs/webui/phase-1-00-planning-and-scope.md`
- **Implementation plan:** `docs/webui/phase-1-implementation-plan.md`

Phase 1 follows the safety principles defined in this document. All Phase 1 subphases (1A through 1G) must satisfy the applicable gates defined in Section 16 (Capability-Specific Gates) before proceeding.
