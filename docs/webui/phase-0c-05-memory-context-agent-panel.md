# Phase 0C-05: Memory / Context / Agent Panel Read-only Integration

**Date:** 2026-06-08
**Status:** Completed (Phase 0C-05A closure validated)
**Depends on:** Phase 0C-04 (Session Messages)

---

## 1. Status

Phase 0C-05 is **completed and formally sealed**. All Memory, Context Preview, and Agent Status endpoints are implemented with full read-only guarantees, connected to real frontend panels, and validated through comprehensive closure testing (Phase 0C-05A).

---

## 2. Scope

### Backend (6 new routes)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/dev/v1/memory/status` | Memory system availability and counts |
| GET | `/api/dev/v1/memory/categories` | Memory category list with item counts |
| GET | `/api/dev/v1/memory/items` | Memory item list with filtering |
| GET | `/api/dev/v1/memory/items/{memoryId}` | Memory item detail with record preview |
| POST | `/api/dev/v1/context/preview` | Memory context scoring preview |
| GET | `/api/dev/v1/agent/status` | Agent configuration status |

Total runtime business routes: **11**

### Frontend

- Memory panel: categories, items, detail preview, archived toggle
- Context panel: query input, preview trigger, matched categories/memories with scores
- Agent panel: runtime flags, model info, memory flags

---

## 3. Architecture

### 3.1 Memory Service (`hermes_cli/dev_web_memory_service.py`)

Read-only service wrapping `hermes_cli.memory_router` functions with explicit `home` parameter.

**Read-only functions used:**
- `parse_root(home)`, `active_root_categories(home, include_all)`, `parse_index(category, home)`
- `list_items(home, include_all)`, `get_memory_system_summary(home)`
- `score_category()`, `score_memory_item()`, `_truncate_text()`, `_query_terms()`
- `resolve_memory_uri()` (for reading records only)

**Never called:** `write_root_categories`, `write_index_items`, `create_memory_item`, `update_memory_item`, `archive_memory_item`, `append_event`

### 3.2 Agent Service (`hermes_cli/dev_web_agent_service.py`)

Read-only service wrapping `hermes_cli.config.load_config_readonly()`.

**Safe fields exposed:** model name, provider name, memory flags, execution flags (all false)

**Never exposed:** api_key, base_url, secret, token, credential, full config, system_prompt

### 3.3 Context Preview

Built into Memory Service as `preview_context()` method. Pure algorithmic scoring — same logic as `load_memory_context()` but with explicit `home` parameter.

**Guarantees:** No LLM, no writes, no session persistence, no memory writer, no review queue.

---

## 4. DTO Whitelist

### 4.1 Memory Category DTO

Fields: `key`, `title`, `description`, `priority`, `keywords`, `status`, `memoryCount`, `activeMemoryCount`

Never returned: `index` (file URI), `storage`, `path`

### 4.2 Memory Item List DTO

Fields: `id`, `category`, `title`, `summary`, `tags`, `type`, `importance`, `status`, `updatedAt`

Never returned: `storage` (file URI), `path`

### 4.3 Memory Item Detail DTO

Fields: All list fields + `createdAt`, `recordPreview`, `truncated`

Never returned: `storage` (file URI), `path`, full record body

### 4.4 Context Preview DTO

Fields: `query`, `matchedCategories` (key, title, score, priority), `memories` (id, category, title, summary, score, truncated), `limits`, `sideEffects`

Never returned: `record_text` (full record), internal prompt text, system prompt

### 4.5 Agent Status DTO

Fields: `available`, `readOnly`, `runtime` (entry, messageSendEnabled, streamingEnabled, toolExecutionEnabled), `model` (configured, provider, name), `memory` (enabled, contextLoaderEnabled, autoWriteEnabled, reviewQueueEnabled)

Never returned: `api_key`, `base_url`, `secret`, `token`, `credential`, `system_prompt`, full config

---

## 5. Secret Redaction

- Error messages filtered through `_FORBIDDEN_IN_MESSAGE` check
- Config loaded via `load_config_readonly()` — only safe fields extracted
- Provider names sanitized through `_safe_provider_name()` whitelist
- Model names sanitized through `_safe_model_name()` — strips path segments
- All DTOs explicitly constructed — never `asdict()` or `__dict__`

### 5.1 Path Redaction (Phase 0C-05A)

Memory record content may contain local file paths written by users or system references. These must never appear in API responses or frontend display.

**Implementation:** `redact_local_paths()` pure function in `dev_web_memory_service.py`.

Applied before `recordPreview` enters the DTO in:
- `get_item()` — memory item detail endpoint
- Applied to record text before truncation

**Patterns redacted:**

| Pattern | Replacement | Notes |
|---------|-------------|-------|
| `/Users/<name>/...` | `[local-path]` | macOS home directories |
| `/home/<name>/...` | `[local-path]` | Linux home directories |
| `C:\Users\...` | `[local-path]` | Windows paths (defensive) |
| `file://...` | `[file-uri-redacted]` | File URI schemes |

**Preserved (not redacted):**

| Pattern | Reason |
|---------|--------|
| `memory://...` | Internal Hermes reference, not a local path |
| `https://...` | Public URL |
| `http://...` | Public URL |

---

## 6. Side-effect Guarantee

Context preview is guaranteed side-effect-free:
- Memory files hash unchanged after preview
- events.jsonl unchanged
- snapshots unchanged
- reviews unchanged
- SessionDB unchanged
- No LLM call
- No Agent call
- No Memory Writer call
- No Review Queue call

Verified by: `test_memory_files_unchanged_after_context_preview`, `test_no_new_events_after_api_calls`

---

## 7. Frontend Panel Behavior

### 7.1 Memory Panel

- Loads status on mount
- Shows categories as chips, items as clickable cards
- Click item to see detail with record preview
- Archived toggle available
- Loading / Empty / Error / Retry states
- No write buttons, no add/update/archive, no file paths

### 7.2 Context Panel

- Query input with manual preview trigger (no auto-request)
- Shows "No LLM" and "No writes" badges
- Results show matched categories with scores, loaded memories with scores
- Side effects guarantee shown
- Empty state with guidance text
- Loading / Error / Retry states

### 7.3 Agent Panel

- Loads status on mount
- Shows runtime flags (all disabled), model info (safe), memory flags
- Read-only badge
- No Run Agent button, no Send Message, no Tool Execute, no Reveal Prompt
- Loading / Error / Retry states

### 7.4 Files Panel

- Unchanged: `available=false`

---

## 8. Tests

### 8.1 Backend

File: `tests/test_dev_web_memory.py`

- **77 tests** covering:
  - Memory status (available/unavailable, counts, no paths)
  - Memory categories (list, archived toggle, whitelist, no paths)
  - Memory items (list, filter, pagination, whitelist, no storage URI)
  - Memory item detail (detail, record preview, not found, invalid ID)
  - Context preview (basic, scores, limits, validation, side effects)
  - Agent status (available, runtime flags, memory flags, no secrets)
  - Read-only verification (file hashes unchanged, no events appended)
  - Route boundary (11 business routes, no write routes, no reviews)
  - Status integration
  - **Path redaction unit tests** (13 tests): macOS, Linux, Windows, file://, memory://, https, empty, multiple
  - **Path redaction API integration** (5 tests): no local paths in responses, redaction markers present, memory:// preserved, https preserved, all endpoints verified

Total backend tests: **350 passed** (across all 4 test files)

### 8.2 Frontend

File: `apps/hermes-dev-webui/src/tests/memory-api.spec.ts`

- **21 tests** covering all API clients:
  - fetchMemoryStatus, fetchMemoryCategories, fetchMemoryItems, fetchMemoryItemDetail
  - previewContext
  - fetchAgentStatus
  - **Path redaction in responses** (3 tests): redaction markers, null preview, safe content passthrough

Updated: `workspace-panel.spec.ts` — **10 tests** for panel behavior including no-local-paths check across all tabs

Total frontend tests: **250 passed**

---

## 9. Browser Validation (Phase 0C-05A Closure)

Browser: Chromium Headless (Playwright)
WebUI: `http://127.0.0.1:5180`
API: `http://127.0.0.1:5181`
Viewports: 1280×800, 1440×900

### 9.1 Network Verification

| Endpoint | Status | Path Redaction |
|----------|--------|----------------|
| GET /memory/status | 200 | No paths in response |
| GET /memory/categories | 200 | No paths in response |
| GET /memory/items | 200 | No paths in response |
| GET /memory/items/{id} | 200 | `[local-path]` markers present |
| POST /context/preview | 200 | No paths in response |
| GET /agent/status | 200 | No paths in response |

Forbidden routes (all 404): `/reviews`, `/agent/run`, `/tools`
Port 5182: not listening

### 9.2 Panel Verification

**Memory Panel:**
- Badge: Read-only ✅
- Categories, items, detail visible ✅
- No path leaks in visible text ✅
- No write buttons ✅

**Context Panel:**
- Query input visible ✅
- Preview submitted and returned ✅
- No path leaks in visible text ✅
- No LLM badge, no write badge ✅

**Agent Panel:**
- No secrets (api_key, base_url, secret) ✅
- No Run Agent button ✅
- No Tool Execute button ✅
- No path leaks in visible text ✅

### 9.3 Browser Quality

| Check | Result |
|-------|--------|
| Console project errors | 0 |
| Console project warnings | 0 |
| CORS errors | 0 |
| Asset 404 | 0 |
| Horizontal overflow at 1280×800 | None |
| Horizontal overflow at 1440×900 | None |

### 9.4 Five-theme Regression

| Theme | Result |
|-------|--------|
| Obsidian | PASS |
| Paper | PASS |
| 宋韵 Song | PASS |
| 墨境 Ink | PASS |
| 夜樱 Sakura Night | PASS |

### 9.5 dev-check Result

- Result: **WARN** (only due to 5 pre-existing visual-review directories)
- No FAIL items
- All PASS items unchanged from baseline

### 9.6 Side-effect Verification

All memory files verified by SHA-256 hash before and after smoke test:
- MEMORY.md: unchanged
- memory/indexes/: all 7 files unchanged
- memory/records/: all 3 files unchanged
- memory/events.jsonl: unchanged
- memory/snapshots/: all 9 files unchanged
- memory/reviews/: all files unchanged

---

## 10. Non-goals

- Memory writing, updating, or archiving
- Review queue access
- Agent execution
- Tool execution
- LLM streaming (SSE)
- File browsing
- Session creation or modification
- Context persistence

---

## 11. Phase 0C-06 Input

Phase 0C-06 should:
1. Run comprehensive visual regression across all five themes
2. Audit error handling edge cases
3. Verify accessibility (keyboard nav, screen reader)
4. Run responsive breakpoint testing
5. Finalize and freeze Phase 0C baseline
