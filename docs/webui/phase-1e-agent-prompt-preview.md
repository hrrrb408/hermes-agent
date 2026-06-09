# Phase 1E: Agent Prompt Preview / Agent Run Dry-Run Implementation

**Status:** Completed
**Date:** 2026-06-09
**Branch:** dev-huangruibang
**Base commit:** dd3f783bb (Phase 1E-00 scope freeze)
**Commits:** 37d89efd5, e3e182b32
**OpenAPI paths:** 21 → 23

---

## 1. Status

Phase 1E is **completed**. Two read-only preview APIs and a frontend panel have been implemented with zero LLM calls, zero tool execution, and zero persistent side effects.

---

## 2. Scope

- Backend: `DevAgentPreviewService` — pure read-only prompt metadata assembly
- API: `POST /agent/prompt/preview` and `POST /agent/run/dry-run`
- Frontend: Agent panel with Status / Prompt Preview / Run Dry-Run sub-tabs
- All execution capabilities forced disabled in Phase 1E
- Full input validation, path/secret redaction, DTO whitelist

---

## 3. Non-Goals

- No `POST /agent/run` (real agent execution)
- No SSE streaming
- No tool execution
- No session/message writes
- No memory writes
- No review queue enqueue
- No LLM provider client construction

---

## 4. Backend Architecture

### Service: `DevAgentPreviewService`

- **File:** `hermes_cli/dev_web_agent_preview_service.py`
- **Pattern:** Independent read-only service, no agent instantiation
- **Dependencies:** `load_config_readonly()`, `SessionDB(read_only=True)`, `memory_router` read functions
- **Explicit home:** All paths passed via `hermes_home` parameter, never falls back to `~/.hermes`

### Prompt Builder Strategy

- Does NOT call `build_system_prompt_parts()` (requires live agent)
- Reads the same source files (SOUL.md, config, memory indexes) independently
- Estimates section character counts from actual file sizes
- Never constructs Provider client, Tool Registry, or Session Writer

### Key Safety Properties

- No `AIAgent` instantiation
- No Provider client initialization
- No API key access
- No Tool Registry initialization
- No Session DB writer
- No Runtime Memory Writer
- No Streaming callback
- No execution threads

---

## 5. Prompt Preview API

### Route: `POST /api/dev/v1/agent/prompt/preview`

**Request validation:**
- `message` required, 1–4000 chars
- `sessionId` optional, max 200 chars, no control chars
- Forbidden fields: `apiKey`, `baseUrl`, `systemPrompt`, `tools`, `execute`, `stream`, etc.
- Temperature: 0.0–2.0, maxOutputTokens: 1–32768

**Response structure:**
- `dryRun: true`, `operation: "PROMPT_PREVIEW"`
- Session metadata (exists, historyIncluded, historyMessageCount)
- Safe model metadata (name, provider, temperature, maxOutputTokens)
- Prompt section breakdown (type, included, characterCount, optional redacted preview)
- Memory context items (memoryId, title, category, score, summaryPreview)
- Capability plan (all forced disabled)
- Safety flags (all readOnly=true, all side-effects=false)
- Checks list, no-effects list, warnings

---

## 6. Agent Run Dry-Run API

### Route: `POST /api/dev/v1/agent/run/dry-run`

**Capability planning:**
- All execution capabilities forced disabled
- Client can request tools/streaming/auto-memory but server ignores
- Warnings generated for requested-but-forced-disabled capabilities

---

## 7. System Prompt Exposure

- Default: metadata only (section type, character count, included flag)
- Optional (`includeSystemPreview=true`): redacted, truncated 500-char preview
- Redaction: paths → `[local-path]`, secrets → `[secret-redacted]`
- Never returns full system prompt content

---

## 8. Redaction and Truncation

- Path patterns: `/Users/...`, `/home/...`, `file://...` → `[local-path]`, `[file-uri-redacted]`
- Secret patterns: `api_key=...`, `Authorization: Bearer ...`, `token=...`, `secret=...` → `[secret-redacted]`
- Order: redact first, truncate second
- Limits: user message 500, history 300, memory summary 300, system preview 500

---

## 9. Error Model

New error codes: `AGENT_PREVIEW_UNAVAILABLE`, `INVALID_AGENT_PREVIEW_REQUEST`, `INVALID_SESSION_ID`, `INVALID_MODEL_OVERRIDE`, `INVALID_TEMPERATURE`, `INVALID_MAX_OUTPUT_TOKENS`, `AGENT_CONFIG_UNAVAILABLE`, `AGENT_PROMPT_ASSEMBLY_ERROR`

---

## 10. OpenAPI Changes

- Paths: 21 → 23
- New routes: `/agent/prompt/preview`, `/agent/run/dry-run`
- Still absent: `/agent/run`, `/agent/stream`, `/agent/tools`

---

## 11. dev-check Changes

- Expected paths: 23
- Agent preview routes verified present
- `/agent/run` exact path forbidden
- `/agent/run/dry-run` allowed

---

## 12. Testing

### Backend: 70 new tests
- Prompt Preview: validation, session handling, memory context, system preview, overrides
- Run Dry-Run: capability planning, forced disabled, warnings
- Forbidden field rejection (20 parametrized cases)
- Safety flags verification
- Forbidden function monkeypatch (7 tests)
- DTO safety (no sensitive data in response)
- Side-effect hash verification (filesystem, DB, auxiliary files)
- Redaction verification (paths, secrets)

### Existing tests updated: 295 total pass
- `test_dev_check_webui.py`: 23-path spec
- `test_dev_web_0c06_closure.py`: 23 business paths, 10 POST routes

---

## 13. Side-Effect Validation

Formal dev-home before/after verification:
- state.db: PASS (identical)
- MEMORY.md: PASS (identical)
- memory/ files: PASS (identical)
- memory/ dirs: PASS (identical)
- DB auxiliary files: PASS (none created)

---

## 14. Frontend Architecture

- **Types:** Full TypeScript types for all preview request/response DTOs
- **API client:** `previewAgentPrompt()`, `dryRunAgent()` with AbortSignal
- **Store:** Pinia `useAgentPreviewStore` with loading/error/success/race handling
- **Components:** AgentPanel (3 tabs), AgentPreviewResult (full result display)
- **Accessibility:** ARIA tabs, aria-live, aria-busy, keyboard navigation, focus-visible

---

## 15. Risks

### P1 (Reported, not blocking)
- Prompt Builder coupled to agent instance — Phase 1E uses independent assembly
- Memory context depends on `parse_root`/`parse_index` format — tested with real dev-home
- Character counts are estimates, not exact token counts

### P2
- Prompt character count ≠ token count estimation
- Long session history performance (mitigated by historyLimit)
- Model allowlist maintenance for overrides

---

## 16. Acceptance

Phase 1E completed. Agent Prompt Preview and Agent Run Dry-Run APIs and frontend panel are implemented with zero LLM calls, zero tool execution, and zero persistent side effects.
