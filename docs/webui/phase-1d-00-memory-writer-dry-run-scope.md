# Phase 1D-00: Memory Writer Dry-Run Panel — Scope, Contract & Safety Boundary Freeze

**Date:** 2026-06-09
**Status:** Completed
**Depends on:** Phase 0E-Release (commit `cc64aa690`)
**Governance scope:** `docs/webui/phase-1-00-planning-and-scope.md`

---

## 1. Status

Phase 1D-00 is a **documentation-only scope freeze**. No API, backend, frontend, or configuration code is modified. The purpose is to audit the Memory Writer subsystem, identify safe read-only functions, enumerate forbidden write functions, and freeze the dry-run API contract before Phase 1D implementation begins.

---

## 2. Background

Phase 1C (Review Queue Execute) introduced the first real write capability to the Dev WebUI. Phase 1D moves to an independent track: Memory Writer dry-run preview. Unlike the Review Queue — which operates on pre-existing review items — the Memory Writer dry-run must evaluate *candidate* memory content against existing data and return a decision preview without modifying any files.

The Memory Writer subsystem (`agent/runtime_memory_writer.py`) is a **rule-based, conservative, non-LLM** evaluator. It does not call external services, does not use embeddings, and produces five decision types: `WRITE`, `UPDATE`, `REVIEW`, `SKIP`, and `SKIP_DUPLICATE`.

---

## 3. Current Baseline

| Item | Value |
|------|-------|
| Current branch | `dev-huangruibang` |
| HEAD | `79b92142b` |
| Remote HEAD | `79b92142b` (synced) |
| OpenAPI paths | 18 |
| Memory capability | Read-only (status, categories, items, context preview) |
| Review Queue | Read-only + dry-run + dev-only execute |
| Memory Writer dry-run | Not implemented |
| Real Memory write | Not implemented in WebUI |

---

## 4. Audit Sources

### 4.1 Core Memory Code

| File | Lines | Role |
|------|-------|------|
| `agent/runtime_memory_writer.py` | 1017 | Decision engine — scoring, similarity, protection, write/update dispatch |
| `hermes_cli/memory_router.py` | 1540 | File-based CRUD — root, categories, indexes, records, events, backups |
| `agent/memory_review_queue.py` | 891 | Review Queue — enqueue, approve, reject, events, atomic writes |

### 4.2 WebUI Backend

| File | Lines | Role |
|------|-------|------|
| `hermes_cli/dev_web_memory_service.py` | 652 | Read-only memory query service |
| `hermes_cli/dev_web_review_service.py` | 1283 | Review dry-run + execute service |
| `hermes_cli/dev_web_config.py` | 179 | Dev environment config + safety guards |
| `hermes_cli/dev_web_schemas.py` | — | DTO definitions |
| `hermes_cli/dev_web_errors.py` | — | Error codes and sanitization |
| `hermes_cli/dev_web_api.py` | — | FastAPI routes |

### 4.3 Planning Documents

- `docs/webui/phase-1-00-planning-and-scope.md`
- `docs/webui/phase-1-implementation-plan.md`
- `docs/webui/phase-0e-06-phase-1-safety-boundary.md`
- `docs/webui/phase-1c-review-queue-execute.md`
- `docs/webui/phase-1c-post-approve-execute-test-closure.md`
- `docs/webui/dev-web-api-v1.md`
- `docs/webui/openapi/dev-web-api-v1.yaml`

---

## 5. Memory Data Model

### 5.1 Root Router (`MEMORY.md`)

MEMORY.md is the root index. Each section is a category:

```markdown
## hermes

- index: memory://indexes/hermes.md
- scope: project
- priority: P0
- status: active
- keywords: Hermes, dev-check, gateway, memory, cli
- description: ...
```

**Fields:** `index`, `scope`, `priority`, `status`, `keywords`, `description`.

**Valid status:** `active`, `archived`, `deprecated`.
**Valid priority:** `P0`, `P1`, `P2`, `P3`.

### 5.2 Category Index (`memory/indexes/{category}.md`)

Each category has an index file listing memory items:

```markdown
## MEM-HERMES-010 Memory Title

- type: project_status
- importance: P1
- ttl: project
- status: active
- tags: hermes, review-queue
- storage: memory://records/hermes/mem-hermes-010.md
- created_at: 2026-06-08
- updated_at: 2026-06-09
- summary: ...
```

**Fields:** `type`, `importance`, `ttl`, `status`, `tags`, `storage`, `created_at`, `updated_at`, `summary`.

**Valid importance:** `P0`, `P1`, `P2`, `P3`.
**Valid TTL:** `permanent`, `project`, `session`, `temporary`.
**Valid status:** `active`, `archived`, `deprecated`, `superseded`, `conflict`.

### 5.3 Memory Record (`memory://records/{category}/{id}.md`)

Individual record files with Summary, Details, and Metadata sections.

### 5.4 Events (`memory/events.jsonl`)

Append-only JSON Lines log:

```json
{"time": "2026-06-09T...", "action": "memory_create", "category": "hermes", "summary": "Created memory ...", "memory_id": "MEM-HERMES-010", "storage": "memory://..."}
```

### 5.5 Snapshots (`memory/snapshots/`)

Backup files created before mutations:

- `MEMORY-{timestamp}.md` — MEMORY.md backups
- `INDEX-{category}-{timestamp}.md` — Category index backups
- `RECORD-{memoryId}-{timestamp}.md` — Record backups

### 5.6 Review Queue (`memory/reviews/`)

- `items/{reviewId}.json` — Individual review items
- `events.jsonl` — Review event log

---

## 6. Writer Decision Model

The MemoryDecision enum defines 5 decision types:

| Decision | Value | Description |
|----------|-------|-------------|
| `WRITE` | `"WRITE"` | Create a new memory item |
| `UPDATE` | `"UPDATE"` | Update an existing memory item |
| `REVIEW` | `"REVIEW"` | Requires manual review — too similar or ambiguous |
| `SKIP` | `"SKIP"` | No action needed — score too low or invalid |
| `SKIP_DUPLICATE` | `"SKIP_DUPLICATE"` | Exact duplicate of existing memory |

**Key design properties:**
- REVIEW, SKIP, and SKIP_DUPLICATE **never modify memory files** (documented in module docstring).
- WRITE and UPDATE are only executed when `auto_write_enabled` is `True` and the decision passes through `perform_safe_memory_action()`.
- The evaluation functions (`evaluate_memory_auto_write` with `write=False`, `resolve_memory_decision`) are **pure computation** — they produce decisions without side effects.

---

## 7. WRITE Audit

### 7.1 Trigger Conditions

WRITE is triggered when **all** of the following are true:

1. A valid `MemoryCandidate` is extracted (non-empty summary, title, category, tags).
2. Score ≥ `write_threshold` (default 80).
3. No existing memory match with similarity ≥ `candidate_similarity_threshold` (default 0.75), OR match exists but similarity < `duplicate_similarity_threshold` (default 0.98) AND does not qualify for UPDATE.
4. Category exists and is active (or `auto_create_categories` is enabled and score ≥ write_threshold).
5. User has not explicitly requested no memory.
6. Source confidence is not `assistant_inferred` only.
7. `auto_write_enabled` is `True` (for actual execution; evaluation still produces WRITE decision even when disabled).

### 7.2 Memory ID Generation

```python
memory_id = allocate_memory_id(category)
# Format: MEM-{CATEGORY_UPPER}-{NNN}
# Example: MEM-HERMES-011
```

Sequential numbering within category. Scans all existing items (including archived) to find highest number.

### 7.3 Category Determination

Rule-based inference from text content:

| Terms | Category |
|-------|----------|
| gateway, wechat, 微信, memory, runtime, agent | `hermes` |
| travel, flight, hotel | `travel` |
| finance, stock, 基金, 股票, 理财 | `finance` |
| (default) | `hermes` |

### 7.4 Title/Summary/Tags Generation

- **Title:** Truncated summary (100 chars max).
- **Summary:** Truncated to 100 chars with "..." suffix.
- **Tags:** Category + matched tag terms, max 8 tags.

### 7.5 Duplicate Detection

Duplicate is detected when:
- Similarity ≥ `duplicate_similarity_threshold` (0.98) AND
- Either `title_similarity ≥ 0.95` OR `summary_similarity ≥ 0.95`.

Result: `SKIP_DUPLICATE` decision.

### 7.6 P0/Permanent Protection for WRITE

WRITE **bypasses** P0/permanent protection checks. Protection only applies during UPDATE operations.

### 7.7 Files Written by Real WRITE

When `perform_safe_memory_action()` executes a WRITE:

1. `ensure_memory_scaffold()` — creates `memory/indexes/`, `memory/records/`, `memory/snapshots/`, `memory/events.jsonl`, `MEMORY.md` if missing.
2. `_ensure_auto_category()` (if category missing and auto_create enabled):
   - `backup_memory_root()` — `memory/snapshots/MEMORY-{timestamp}.md`
   - `write_root_categories()` — rewrites `MEMORY.md`
   - Creates `memory/indexes/{category}.md`
   - `append_event("category_create", ...)`
3. `backup_file(index_path, "INDEX-{category}")` — `memory/snapshots/INDEX-{category}-{timestamp}.md`
4. `write_index_items()` — rewrites `memory/indexes/{category}.md`
5. `record_path.parent.mkdir(parents=True, exist_ok=True)` — creates record directory
6. `record_path.write_text(...)` — creates `memory/records/{category}/{id}.md`
7. `append_event("memory_create", ...)` — appends to `memory/events.jsonl`
8. `append_event("memory_auto_add", ...)` — appends to `memory/events.jsonl`

### 7.8 Failure States

No transaction or rollback mechanism. If any step fails mid-operation:
- Category may have been created but index not updated.
- Index may have been updated but record file not created.
- Event may have been appended but write incomplete.
- **Manual recovery from snapshots** is the only rollback path.

---

## 8. UPDATE Audit

### 8.1 Trigger Conditions

UPDATE is triggered when **all** of the following are true:

1. Score ≥ `write_threshold` (80).
2. Existing match with `similarity ≥ candidate_similarity_threshold` (0.75).
3. `similarity ≥ update_similarity_threshold` (0.90).
4. Either `title_similarity ≥ 0.85` OR `summary_similarity ≥ 0.90`.
5. Same category as candidate (`require_same_category_for_update=True`).
6. Core tag overlap exists (`require_tag_overlap_for_update=True`).
7. Target status is `active`.
8. Target is not P0/permanent protected.
9. `auto_write_enabled` and `auto_update_enabled` are both `True`.

### 8.2 Target Selection

`find_best_memory_match(candidate)` scans **all** items (including archived) and returns the one with highest `max(title_similarity, summary_similarity, combined_similarity)`.

### 8.3 Similarity Calculation

```python
def _similarity(left, right):
    return SequenceMatcher(None, normalize_memory_text(left), normalize_memory_text(right)).ratio()
```

- **Title similarity:** `_similarity(candidate.title, item.title)`
- **Summary similarity:** `_similarity(candidate.summary, fields["summary"])`
- **Combined similarity:** `_similarity(f"{title} {summary}", f"{title} {summary}")`

Normalization strips CJK and ASCII punctuation, lowercases, collapses whitespace.

### 8.4 Tag Overlap

```python
overlap = sorted(candidate_tags & existing_tags)       # all overlapping
core = sorted(tag for tag in overlap if tag not in GENERIC_TAGS)  # non-generic overlap
```

`GENERIC_TAGS = {"hermes", "project", "status", "memory", "system"}`

### 8.5 Protection

`is_protected_memory(match, cfg)` returns protection status:

| Condition | Code | Message |
|-----------|------|---------|
| `importance == "P0"` and `protect_p0` | `TARGET_P0_PROTECTED` | "Matched memory importance is P0 and automatic updates are protected." |
| `ttl == "permanent"` and `protect_permanent` | `TARGET_PERMANENT_PROTECTED` | "Matched memory ttl is permanent and automatic updates are protected." |

Both defaults: `protect_p0=True`, `protect_permanent=True`.

### 8.6 Fields Updated

The UPDATE operation updates: `type`, `importance`, `ttl`, `status` (forced to "active"), `tags`, `summary`, `body`.
**Title is NOT updated** (title=None passed to `update_memory_item()`).
`updated_at` is set to current date.

### 8.7 Files Written by Real UPDATE

1. `backup_file(index_path, "INDEX-{category}")` — index snapshot
2. `backup_file(record_path, "RECORD-{memoryId}")` — record snapshot
3. `write_index_items()` — rewrites category index
4. `record_path.write_text(...)` — rewrites record file
5. `append_event("memory_update", ...)` — event
6. `append_event("memory_auto_update", ...)` — event

### 8.8 Inconsistency Risks

Same as WRITE — no transactions, no rollback. Index may be updated but record not rewritten (or vice versa).

---

## 9. ARCHIVE Audit

### 9.1 Implementation

There is **no `archive_memory_item()` function**. Archive is implemented via `update_memory_item(args, archive=True)`:

```python
def cmd_memory_archive(args):
    item = update_memory_item(args, archive=True)
```

### 9.2 What Archive Does

When `archive=True` is passed:

1. Sets `status` to `"archived"` (overrides any other status update).
2. If item already has `status == "archived"`, returns immediately (idempotent).
3. Creates backup of index and record.
4. Rewrites index and record files.
5. Appends `append_event("memory_archive", ...)`.

### 9.3 Protection

P0/permanent protection is **not checked** during archive. The protection logic in `runtime_memory_writer.py` only applies to the auto-update decision path. Direct CLI archive (and any future API archive) does not enforce P0/permanent blocking.

**This is a P1 risk for Phase 1D:** The dry-run must enforce protection checks even if the underlying implementation does not.

### 9.4 Recovery

Archive is a status change (`active → archived`), not a file move. The record and index entries remain in place. Recovery requires setting status back to `active` via an update operation.

---

## 10. REVIEW / SKIP Audit

### 10.1 REVIEW

**Trigger conditions (any one sufficient):**

- Score ≥ `review_threshold` (65) but < `write_threshold` (80), with no match.
- Score ≥ `review_threshold` but candidate is `assistant_inferred` only.
- Category not found and `auto_create_categories` disabled.
- Category found but status is not `active`.
- Existing match with similarity ≥ `candidate_similarity_threshold` (0.75) but not safe to auto-update (fails one or more UPDATE conditions).

**Auto-enqueue:** When Review Queue is enabled, REVIEW decisions are enqueued via `enqueue_review_item()`. This IS a write operation (creates JSON file and appends review event).

**Phase 1D dry-run handling:** Dry-run must return `wouldEnqueueReview: true` but **must not** actually enqueue. The dry-run service must NOT call `maybe_auto_write_memory()` or `enqueue_review_item()`.

### 10.2 SKIP

**Trigger conditions (any one sufficient):**

- Score < `review_threshold` (65).
- User requested no memory (negative phrases).
- Casual chatter detected.
- One-off questions detected.
- Invalid candidate (missing title/summary/category/tags).

### 10.3 SKIP_DUPLICATE

**Trigger:** Similarity ≥ 0.98 AND (title_similarity ≥ 0.95 OR summary_similarity ≥ 0.95).

### 10.4 Side Effects

REVIEW, SKIP, and SKIP_DUPLICATE **never modify memory files** by themselves. However, the full `maybe_auto_write_memory()` pipeline may enqueue a review item for REVIEW decisions, which IS a write operation.

---

## 11. Duplicate and Similarity Strategy

### 11.1 Thresholds

| Threshold | Default | Purpose |
|-----------|---------|---------|
| `write_threshold` | 80 | Minimum score for WRITE/UPDATE consideration |
| `review_threshold` | 65 | Minimum score for REVIEW consideration |
| `candidate_similarity_threshold` | 0.75 | Minimum similarity to consider existing match |
| `update_similarity_threshold` | 0.90 | Minimum similarity to allow automatic UPDATE |
| `duplicate_similarity_threshold` | 0.98 | Threshold for exact duplicate detection |
| Title update threshold | 0.85 | Minimum title similarity for UPDATE |
| Summary update threshold | 0.90 | Minimum summary similarity for UPDATE |

### 11.2 Decision Flow by Similarity

| Similarity | Decision |
|------------|----------|
| ≥ 0.98 with title/summary ≥ 0.95 | `SKIP_DUPLICATE` |
| ≥ 0.90 with all UPDATE conditions met | `UPDATE` |
| ≥ 0.75 but UPDATE conditions not all met | `REVIEW` |
| < 0.75 (no match) and score ≥ 80 | `WRITE` (if enabled) |
| < 0.75 (no match) and score 65–79 | `REVIEW` |
| < 0.75 (no match) and score < 65 | `SKIP` |

### 11.3 Configuration Sources

Thresholds come from `config["memory"]["auto_write"]` dict, with environment variable overrides:

- `HERMES_MEMORY_AUTO_WRITE`
- `HERMES_MEMORY_AUTO_UPDATE`
- `HERMES_MEMORY_AUTO_CREATE_CATEGORIES`

Phase 1D dry-run should use default thresholds but allow the request to specify `options` for overriding display thresholds.

---

## 12. Protection Rules

### 12.1 P0 Protection

- **WRITE:** Not blocked (new items can have any importance level).
- **UPDATE:** Blocked if `protect_p0=True` (default) and target `importance == "P0"`.
- **ARCHIVE:** Not blocked by current implementation. **Phase 1D dry-run must block P0 archive.**
- **Phase 1D rule:** Dry-run must show `blocked: true` with code `MEMORY_P0_PROTECTED` for UPDATE and ARCHIVE on P0 items.

### 12.2 Permanent Protection

- **WRITE:** Not applicable (new items).
- **UPDATE:** Blocked if `protect_permanent=True` (default) and target `ttl == "permanent"`.
- **ARCHIVE:** Not blocked by current implementation. **Phase 1D dry-run must block permanent archive.**
- **Phase 1D rule:** Dry-run must show `blocked: true` with code `MEMORY_PERMANENT_PROTECTED` for UPDATE and ARCHIVE on permanent items.

### 12.3 Protected Target Identification

```python
def is_protected_memory(match: SimilarityBreakdown, cfg: AutoWriteConfig) -> tuple[bool, list[str], list[str]]:
```

Returns `(is_protected, codes, reasons)`.

### 12.4 Valid Importance Values

`VALID_IMPORTANCE = {"P0", "P1", "P2", "P3"}`

### 12.5 Valid TTL Values

`VALID_TTL = {"permanent", "project", "session", "temporary"}`

---

## 13. Side-Effect Matrix

| Operation | MEMORY.md | Category Index | Record | Memory Event | Snapshot | Review Queue |
|-----------|:---------:|:--------------:|:------:|:------------:|:--------:|:------------:|
| WRITE | Conditional¹ | Yes | Yes | Yes | Yes | No |
| UPDATE | No | Yes | Yes | Yes | Yes | No |
| ARCHIVE | No | Yes | Yes | Yes | Yes | No |
| REVIEW | No | No | No | No | No | Conditional² |
| SKIP | No | No | No | No | No | No |
| SKIP_DUPLICATE | No | No | No | No | No | No |

**Notes:**
1. MEMORY.md is only written when `auto_create_categories` creates a new category.
2. REVIEW does not write memory files, but `maybe_auto_write_memory()` enqueues a Review Queue item (JSON file + event) when Review Queue is enabled.

### 13.1 File Path Templates

| Resource | Path Pattern |
|----------|-------------|
| Root router | `MEMORY.md` |
| Category index | `memory/indexes/{category}.md` |
| Memory record | `memory/records/{category}/{id}.md` (or `memory/records/projects/hermes/{id}.md` for hermes) |
| Events log | `memory/events.jsonl` |
| Root snapshot | `memory/snapshots/MEMORY-{timestamp}.md` |
| Index snapshot | `memory/snapshots/INDEX-{category}-{timestamp}.md` |
| Record snapshot | `memory/snapshots/RECORD-{memoryId}-{timestamp}.md` |
| Review item | `memory/reviews/items/{reviewId}.json` |
| Review events | `memory/reviews/events.jsonl` |

---

## 14. Safe Read-Only Functions

These functions perform **no file writes** and are safe to reuse in Phase 1D dry-run:

### 14.1 Pure Computation (No I/O)

| Function | File | Notes |
|----------|------|-------|
| `normalize_memory_text()` | runtime_memory_writer.py | Text normalization for similarity |
| `_infer_category()` | runtime_memory_writer.py | Category inference from text |
| `_infer_tags()` | runtime_memory_writer.py | Tag inference from text |
| `calculate_score()` | runtime_memory_writer.py | Score computation |
| `_similarity()` | runtime_memory_writer.py | SequenceMatcher similarity |
| `calculate_tag_overlap()` | runtime_memory_writer.py | Tag set intersection |
| `calculate_similarity_breakdown()` | runtime_memory_writer.py | Full similarity analysis |
| `is_protected_memory()` | runtime_memory_writer.py | P0/permanent check |
| `_build_evaluation()` | runtime_memory_writer.py | Evaluation constructor |
| `resolve_memory_decision()` | runtime_memory_writer.py | **Core decision resolver — pure computation** |
| `extract_memory_candidate()` | runtime_memory_writer.py | Candidate extraction |
| `_auto_write_config()` | runtime_memory_writer.py | Config parsing |
| `auto_write_enabled()` | runtime_memory_writer.py | Config check |
| `get_auto_write_config()` | runtime_memory_writer.py | Config retrieval |
| `auto_update_enabled()` | runtime_memory_writer.py | Config check |
| `auto_create_categories_enabled()` | runtime_memory_writer.py | Config check |
| `memory_evaluation_to_dict()` | runtime_memory_writer.py | Serialization |
| `format_memory_auto_json()` | runtime_memory_writer.py | JSON formatting (calls queue config but no writes) |
| `format_memory_auto_test()` | runtime_memory_writer.py | Text formatting (calls queue config but no writes) |
| `_as_bool()` | runtime_memory_writer.py | Type coercion |
| `_as_int()` | runtime_memory_writer.py | Type coercion |
| `_as_ratio()` | runtime_memory_writer.py | Type coercion |

### 14.2 File-Reading Functions (No Writes)

| Function | File | Side-Effect Risk |
|----------|------|-----------------|
| `parse_root()` | memory_router.py | None — reads MEMORY.md |
| `parse_root_sections()` | memory_router.py | None — reads MEMORY.md |
| `active_root_categories()` | memory_router.py | None — filters parse_root() |
| `parse_index()` | memory_router.py | None — reads index file |
| `list_items()` | memory_router.py | None — reads all indexes |
| `find_item()` | memory_router.py | None — scans list_items() |
| `find_item_location()` | memory_router.py | None — returns item + path |
| `category_index_path()` | memory_router.py | None — resolves URI |
| `allocate_memory_id()` | memory_router.py | None — scans and computes next ID |
| `validate_memory_id()` | memory_router.py | None — regex check |
| `validate_memory_fields()` | memory_router.py | None — field validation |
| `validate_category_name()` | memory_router.py | None — regex check |
| `score_category()` | memory_router.py | None — pure scoring |
| `score_memory_item()` | memory_router.py | None — pure scoring |
| `validate_memory()` | memory_router.py | None — reads and validates |
| `get_memory_system_summary()` | memory_router.py | None — aggregates read data |
| `find_best_memory_match()` | runtime_memory_writer.py | None — reads list_items(), pure computation |
| `_category_status()` | runtime_memory_writer.py | None — reads parse_root() |

### 14.3 Review Queue Read-Only Functions

| Function | File | Side-Effect Risk |
|----------|------|-----------------|
| `get_review_queue_config()` | memory_review_queue.py | None — config parsing |
| `get_review_queue_paths()` | memory_review_queue.py | None — path computation |
| `proposed_action_for()` | memory_review_queue.py | None — pure computation |
| `should_enqueue_evaluation()` | memory_review_queue.py | None — pure computation |
| `fingerprint_memory_candidate()` | memory_review_queue.py | None — SHA-256 hash |
| `generate_review_id()` | memory_review_queue.py | None — ID generation |
| `validate_review_item()` | memory_review_queue.py | None — validation |
| `list_review_items()` | memory_review_queue.py | None — reads JSON files |
| `load_review_item()` | memory_review_queue.py | None — reads JSON file |
| `get_review_queue_summary()` | memory_review_queue.py | None — aggregation |
| `revalidate_review_approval()` | memory_review_queue.py | None — pure computation |
| `format_review_item()` | memory_review_queue.py | None — text formatting |

---

## 15. Forbidden Write Functions

These functions **must not be called** by Phase 1D dry-run:

### 15.1 Memory Write Functions

| Function | File | Write Effects |
|----------|------|--------------|
| `ensure_memory_scaffold()` | memory_router.py | Creates directories, creates files if missing |
| `write_root_categories()` | memory_router.py | Rewrites MEMORY.md |
| `write_index_items()` | memory_router.py | Rewrites category index |
| `create_memory_item()` | memory_router.py | Creates record, updates index, appends event, creates backup |
| `update_memory_item()` | memory_router.py | Updates record and index, appends event, creates backups |
| `append_event()` | memory_router.py | **Appends to events.jsonl AND calls ensure_memory_scaffold()** |
| `backup_memory_root()` | memory_router.py | Creates snapshot file, calls ensure_memory_scaffold() |
| `backup_file()` | memory_router.py | Creates snapshot file, calls ensure_memory_scaffold() |
| `ensure_root_status_fields()` | memory_router.py | Backfills status, calls backup + write + append_event |
| `_ensure_auto_category()` | runtime_memory_writer.py | Creates category, writes root, creates index, appends event |
| `perform_safe_memory_action()` | runtime_memory_writer.py | Calls create_memory_item() or update_memory_item() + append_event() |
| `maybe_auto_write_memory()` | runtime_memory_writer.py | Calls perform_safe_memory_action() + enqueue_review_item() |

### 15.2 Review Queue Write Functions

| Function | File | Write Effects |
|----------|------|--------------|
| `_ensure_paths()` | memory_review_queue.py | Creates review directories |
| `atomic_write_review_json()` | memory_review_queue.py | Writes/updates review JSON file |
| `append_review_event()` | memory_review_queue.py | Appends to review events.jsonl |
| `enqueue_review_item()` | memory_review_queue.py | Creates/updates review item JSON + appends event |
| `approve_review_item()` | memory_review_queue.py | Updates review item + may call create/update_memory_item + events |
| `reject_review_item()` | memory_review_queue.py | Updates review item JSON + appends event |

### 15.3 CLI Write Commands

| Function | File | Write Effects |
|----------|------|--------------|
| `cmd_memory_add()` | memory_router.py | Calls create_memory_item() |
| `cmd_memory_update()` | memory_router.py | Calls update_memory_item() |
| `cmd_memory_archive()` | memory_router.py | Calls update_memory_item(archive=True) |
| `cmd_memory_category_add()` | memory_router.py | Creates category + index + event |
| `cmd_memory_category_update()` | memory_router.py | Updates category + event |
| `cmd_memory_category_archive()` | memory_router.py | Archives category + event |

---

## 16. Hidden Write Risks

### 16.1 `ensure_memory_scaffold()` (CRITICAL)

Called by: `append_event()`, `backup_memory_root()`, `backup_file()`, `ensure_root_status_fields()`, all CLI commands.

**Effects:**
- Creates `memory/indexes/`, `memory/records/`, `memory/snapshots/` directories.
- Creates empty `memory/events.jsonl` if missing.
- Creates `MEMORY.md` from template if missing.
- Creates category index files for any category in root that lacks an index.

**Risk for dry-run:** `append_event()` calls `ensure_memory_scaffold()`. Even though dry-run won't call `append_event()` directly, any function that transitively calls it will create files.

**Mitigation:** Phase 1D dry-run must NOT call `append_event()`, `backup_memory_root()`, `backup_file()`, `ensure_memory_scaffold()`, or any CLI write command.

### 16.2 `_ensure_paths()` (Review Queue)

Called by: `enqueue_review_item()`, `approve_review_item()`, `reject_review_item()`.

**Effects:** Creates `memory/reviews/items/` directory.

**Mitigation:** Dry-run must NOT call any review queue write function.

### 16.3 `find_best_memory_match()` — Safe

This function calls `list_items(include_all=True)` which calls `parse_root()` → `parse_index()` per category. These are all pure reads. **No hidden writes.**

### 16.4 `allocate_memory_id()` — Safe

Reads all items to compute next sequential number. No file writes.

### 16.5 `get_review_queue_config()` / `should_enqueue_evaluation()` — Safe

Pure config parsing and computation. No I/O.

---

## 17. Proposed Routes

Phase 1D implementation will add 3 dry-run POST routes:

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/dev/v1/memory/write/dry-run` | Evaluate candidate for WRITE decision |
| POST | `/api/dev/v1/memory/items/{memoryId}/update/dry-run` | Evaluate candidate for UPDATE against target |
| POST | `/api/dev/v1/memory/items/{memoryId}/archive/dry-run` | Evaluate archive conditions for target |

**Suffix requirement:** All routes MUST use the `/dry-run` suffix. Routes without `/dry-run` (e.g. `/memory/write`, `/memory/items/{id}/update`) are permanently prohibited.

**No execute routes in Phase 1D.** Real Memory Writer execute is a future independent phase.

---

## 18. Request DTOs

### 18.1 WRITE Dry-Run Request

```json
{
  "query": "string (max 2000 chars)",
  "candidate": {
    "title": "string (max 120 chars)",
    "summary": "string (max 1000 chars)",
    "category": "string (max 100 chars, must match [a-z0-9][a-z0-9_-]*)",
    "type": "string (max 50 chars)",
    "importance": "P0 | P1 | P2 | P3",
    "ttl": "permanent | project | session | temporary",
    "tags": ["string (max 20 items, each max 50 chars)"],
    "sourceConfidence": "user_confirmed | assistant_inferred"
  },
  "options": {
    "allowReviewRecommendation": true,
    "includeSimilarity": true,
    "includeEffects": true
  }
}
```

**Validation rules:**
- `query`: required, max 2000 chars.
- `candidate`: required.
- `candidate.summary`: required, max 1000 chars.
- `candidate.category`: required, must match `CATEGORY_NAME_RE`.
- `candidate.importance`: required, must be in `VALID_IMPORTANCE`.
- `candidate.ttl`: required, must be in `VALID_TTL`.
- `candidate.tags`: required, 1–20 items.
- `candidate.title`: optional (derived from summary if omitted), max 120 chars.
- `candidate.type`: optional, max 50 chars.
- `candidate.sourceConfidence`: optional, defaults to `"user_confirmed"`.
- `options`: optional, all fields default to `true`.

**Forbidden fields:** `storage`, `path`, `memoryId`, `recordPath`, absolute paths, file URIs.

### 18.2 UPDATE Dry-Run Request

```json
{
  "candidate": {
    "summary": "string (max 1000 chars)",
    "type": "string (max 50 chars)",
    "importance": "P0 | P1 | P2 | P3",
    "ttl": "permanent | project | session | temporary",
    "tags": ["string (max 20 items, each max 50 chars)"]
  },
  "options": {
    "includeDiff": true,
    "includeSimilarity": true,
    "includeEffects": true
  }
}
```

**Path parameter:** `memoryId` — must match `MEMORY_ID_RE`.

**Validation rules:**
- `memoryId`: required, must be valid, target must exist and be in an active category.
- `candidate.summary`: required, max 1000 chars.
- `candidate.tags`: required, 1–20 items.
- All other fields optional.
- Target must not be archived (returns `MEMORY_ALREADY_ARCHIVED` if so).
- P0/permanent protection must be checked.

### 18.3 ARCHIVE Dry-Run Request

```json
{
  "reason": "string (max 500 chars)",
  "options": {
    "includeEffects": true,
    "includeReferences": true
  }
}
```

**Path parameter:** `memoryId` — must match `MEMORY_ID_RE`.

**Validation rules:**
- `memoryId`: required, must be valid, target must exist.
- `reason`: optional, max 500 chars, local paths redacted.
- P0/permanent protection must be checked.
- Target already archived: returns `MEMORY_ALREADY_ARCHIVED`.

---

## 19. Response DTO

Unified response structure for all 3 dry-run routes:

```json
{
  "data": {
    "dryRun": true,
    "operation": "WRITE | UPDATE | ARCHIVE",
    "allowed": true,
    "blockedReason": null,
    "decision": "WRITE | UPDATE | REVIEW | SKIP | SKIP_DUPLICATE",
    "target": {
      "memoryId": "MEM-HERMES-010",
      "title": "Memory Title Preview",
      "category": "hermes",
      "importance": "P1",
      "ttl": "project",
      "status": "active",
      "protected": false,
      "protectionReason": null
    },
    "candidate": {
      "titlePreview": "...",
      "summaryPreview": "...",
      "category": "hermes",
      "type": "project_status",
      "importance": "P1",
      "ttl": "project",
      "tags": ["hermes", "gateway"]
    },
    "score": {
      "total": 85,
      "breakdown": [
        {"rule": "progress_keyword", "value": 20}
      ]
    },
    "similarity": {
      "title": 0.0,
      "summary": 0.0,
      "combined": 0.0,
      "overall": 0.0,
      "tagOverlap": [],
      "coreTagOverlap": [],
      "matchedMemoryId": null,
      "matchedMemoryTitle": null
    },
    "checks": [
      {
        "code": "CATEGORY_EXISTS",
        "passed": true,
        "message": "Category 'hermes' exists and is active."
      }
    ],
    "effects": [
      {
        "type": "CREATE_MEMORY_RECORD",
        "wouldOccur": true,
        "description": "A new memory record would be created."
      }
    ],
    "noEffects": [
      "No files were modified.",
      "No memory event was appended.",
      "No snapshot was created.",
      "No review item was created."
    ],
    "safety": {
      "readOnly": true,
      "writeEnabled": false,
      "executeAvailable": false,
      "sideEffects": false
    },
    "config": {
      "autoWriteEnabled": false,
      "autoUpdateEnabled": false,
      "autoCreateCategories": false,
      "writeThreshold": 80,
      "reviewThreshold": 65
    },
    "warnings": []
  },
  "meta": {
    "requestId": "...",
    "timestamp": "..."
  }
}
```

---

## 20. Field Whitelist

### 20.1 Allowed Response Fields

```
data.dryRun
data.operation
data.allowed
data.blockedReason
data.decision

data.target.memoryId
data.target.title
data.target.category
data.target.importance
data.target.ttl
data.target.status
data.target.protected
data.target.protectionReason

data.candidate.titlePreview
data.candidate.summaryPreview
data.candidate.category
data.candidate.type
data.candidate.importance
data.candidate.ttl
data.candidate.tags

data.score.total
data.score.breakdown[].rule
data.score.breakdown[].value

data.similarity.title
data.similarity.summary
data.similarity.combined
data.similarity.overall
data.similarity.tagOverlap[]
data.similarity.coreTagOverlap[]
data.similarity.matchedMemoryId
data.similarity.matchedMemoryTitle

data.checks[].code
data.checks[].passed
data.checks[].message

data.effects[].type
data.effects[].wouldOccur
data.effects[].description

data.noEffects[]

data.safety.readOnly
data.safety.writeEnabled
data.safety.executeAvailable
data.safety.sideEffects

data.config.autoWriteEnabled
data.config.autoUpdateEnabled
data.config.autoCreateCategories
data.config.writeThreshold
data.config.reviewThreshold

data.warnings[]
```

### 20.2 Forbidden Response Fields

- `storage`, `index`, `path` — internal file paths
- Absolute filesystem paths
- `file://` URIs
- Raw record content
- Raw MEMORY.md content
- Raw category index content
- Raw event lines
- Internal fingerprint hash
- Internal source object references
- System prompt text
- User conversation content
- API keys, tokens, secrets, cookies
- Tracebacks, exception repr, internal stack frames

---

## 21. Redaction and Truncation Rules

### 21.1 Path Redaction (Reuses existing `redact_local_paths()`)

| Pattern | Replacement |
|---------|-------------|
| `/Users/...` | `[local-path]` |
| `/home/...` | `[local-path]` |
| `C:\...` | `[local-path]` |
| `file://...` | `[file-uri-redacted]` |

**Preserved:** `memory://` URIs, `https://` URLs.

### 21.2 Truncation Limits

| Field | Max Length |
|-------|-----------|
| `titlePreview` | 120 chars |
| `summaryPreview` | 300 chars |
| `target.title` | 120 chars |
| `checks[].message` | 200 chars |
| `effects[].description` | 200 chars |
| `warnings[]` | 200 chars each |
| `blockedReason` | 200 chars |
| `protectionReason` | 200 chars |
| Archive `reason` (input) | 500 chars |

Error responses must NOT return the full input text.

---

## 22. Error Model

### 22.1 Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `MEMORY_DRY_RUN_UNAVAILABLE` | 503 | Memory system not available |
| `INVALID_MEMORY_DRY_RUN_REQUEST` | 400 | Request validation failed |
| `INVALID_MEMORY_ID` | 400 | memoryId format invalid |
| `MEMORY_NOT_FOUND` | 404 | Target memory item not found |
| `MEMORY_CATEGORY_NOT_FOUND` | 404 | Category does not exist |
| `MEMORY_CATEGORY_NOT_ACTIVE` | 409 | Category exists but is not active |
| `MEMORY_WRITE_BLOCKED` | 409 | WRITE blocked by protection or config |
| `MEMORY_UPDATE_BLOCKED` | 409 | UPDATE blocked by protection or conditions |
| `MEMORY_ARCHIVE_BLOCKED` | 409 | ARCHIVE blocked by protection |
| `MEMORY_PROTECTED` | 409 | General protection violation |
| `MEMORY_P0_PROTECTED` | 409 | Target is P0 importance |
| `MEMORY_PERMANENT_PROTECTED` | 409 | Target has permanent TTL |
| `MEMORY_DUPLICATE_BLOCKED` | 409 | Exact duplicate detected |
| `MEMORY_ALREADY_ARCHIVED` | 409 | Target already archived |
| `UNSAFE_ENVIRONMENT` | 503 | Environment safety check failed |
| `MEMORY_STORE_ERROR` | 500 | Unexpected memory store error |
| `INTERNAL_ERROR` | 500 | Unexpected internal error |

### 22.2 Error Envelope

Reuses existing Dev API error envelope:

```json
{
  "error": {
    "code": "MEMORY_P0_PROTECTED",
    "message": "Target memory is P0 importance and cannot be updated.",
    "requestId": "...",
    "timestamp": "..."
  }
}
```

### 22.3 Error Safety Requirements

- Must include `requestId` and `timestamp`.
- No absolute paths.
- No tracebacks.
- No raw record content.
- No secrets/tokens/cookies.
- Input text truncated in error messages.

---

## 23. Decision and Effects Model

### 23.1 Decision vs Operation

Phase 1D dry-run must clearly distinguish:

| Field | Meaning |
|-------|---------|
| `operation` | What the user requested (WRITE, UPDATE, ARCHIVE) |
| `decision` | What the Memory Writer would decide (WRITE, UPDATE, REVIEW, SKIP, SKIP_DUPLICATE) |
| `allowed` | Whether the requested operation would be permitted |
| `effects[].wouldOccur` | Whether each specific side effect would happen |

### 23.2 Example Combinations

| operation | decision | allowed | Meaning |
|-----------|----------|---------|---------|
| WRITE | WRITE | true | New memory would be created |
| WRITE | REVIEW | true | Score in review range, would enqueue |
| WRITE | SKIP_DUPLICATE | false | Exact duplicate exists |
| WRITE | SKIP | false | Score too low |
| UPDATE | UPDATE | true | Memory would be updated |
| UPDATE | REVIEW | true | Similar but not safe for auto-update |
| UPDATE | — | false | Target is P0/permanent protected |
| ARCHIVE | ARCHIVE | true | Status would change to archived |
| ARCHIVE | — | false | Target is P0/permanent protected |

### 23.3 Effect Type Whitelist

| Effect Type | Description |
|-------------|-------------|
| `CREATE_MEMORY_RECORD` | New record file would be created |
| `UPDATE_MEMORY_RECORD` | Record file would be rewritten |
| `ARCHIVE_MEMORY_RECORD` | Record status would change to archived |
| `UPDATE_CATEGORY_INDEX` | Category index would be updated |
| `APPEND_MEMORY_EVENT` | Event would be appended to events.jsonl |
| `CREATE_INDEX_SNAPSHOT` | Index backup would be created |
| `CREATE_RECORD_SNAPSHOT` | Record backup would be created |
| `CREATE_MEMORY_ROOT_SNAPSHOT` | MEMORY.md backup would be created |
| `CREATE_CATEGORY` | New category would be auto-created |
| `ENQUEUE_REVIEW` | Review Queue item would be enqueued |
| `NO_OPERATION` | No modifications would occur |

### 23.4 Review Recommendation Handling

Phase 1D dry-run must NOT call `enqueue_review_item()`. Instead:
- When decision is `REVIEW`, return `wouldEnqueueReview: true` in effects.
- The `ENQUEUE_REVIEW` effect type has `wouldOccur: true` but is never actually executed.
- The `noEffects` array must always confirm "No review item was created."

---

## 24. Frontend Information Architecture

### 24.1 Panel Placement

**Recommended:** Add a new **"Writer Preview"** sub-tab within the existing Memory panel in the Workspace panel.

| Tab | Sub-tab | Purpose |
|-----|---------|---------|
| Memory | Browse | Current read-only memory browser (existing) |
| Memory | Writer Preview | New Memory Writer dry-run panel |

**Rationale:** Keeps read-only browsing and writer preview in the same domain area but clearly separated. Avoids adding a new top-level workspace tab.

### 24.2 WRITE Preview UI

**Input area:**
- Query text input (textarea, max 2000 chars)
- Candidate fields: title, summary, category (dropdown), type, importance (dropdown), TTL (dropdown), tags (multi-select/input)
- "Preview WRITE" button

**Result area:**
- Dry-run badge
- Decision badge (WRITE/REVIEW/SKIP/SKIP_DUPLICATE)
- Allowed/Blocked indicator
- Score breakdown
- Similarity panel (if match found)
- Checks panel (pass/fail list)
- Would-be effects panel
- No-effects confirmation list
- Warnings

**Forbidden:** "Write now", "Save memory", "Execute", "Confirm write" buttons.

### 24.3 UPDATE Preview UI

**Input area:**
- Target memory ID input (or select from memory browser)
- Updated candidate fields: summary, type, importance, TTL, tags
- "Preview UPDATE" button

**Result area:** Same as WRITE, plus:
- Diff preview (old vs new summary, tags, importance, TTL)

**Forbidden:** "Update now", "Save changes", "Execute" buttons.

### 24.4 ARCHIVE Preview UI

**Input area:**
- Target memory ID input
- Archive reason text input (max 500 chars)
- "Preview ARCHIVE" button

**Result area:** Same as WRITE, plus:
- Protection status prominently displayed
- Would-be effects (status change, event, snapshots)

**Forbidden:** "Archive now", "Confirm archive", "Execute" buttons.

### 24.5 Accessibility Requirements

- All form fields have `<label>` elements.
- Error messages use `role="alert"`.
- Result panel uses `aria-live="polite"`.
- Buttons are keyboard-reachable.
- Tab/tabpanel semantics correct.
- Loading states use `aria-busy="true"`.
- Disabled states have `aria-disabled="true"`.
- `prefers-reduced-motion` respected.

---

## 25. OpenAPI Strategy

### 25.1 Current State

- 18 paths (unchanged in Phase 1D-00).

### 25.2 Phase 1D Implementation Plan

- Add 3 dry-run POST routes.
- OpenAPI paths: 18 → 21.

### 25.3 Forbidden Routes (Permanent)

```
POST /api/dev/v1/memory/write
POST /api/dev/v1/memory/items/{memoryId}/update
POST /api/dev/v1/memory/items/{memoryId}/archive
PATCH /api/dev/v1/memory/items/{memoryId}
DELETE /api/dev/v1/memory/items/{memoryId}
```

---

## 26. dev-check Strategy

### 26.1 Current State

dev-check validates 18 OpenAPI paths. Phase 1D-00 does not modify dev-check.

### 26.2 Phase 1D Implementation Plan

dev-check will be updated to:
- Validate OpenAPI path count: 18 → 21.
- Allow 3 memory dry-run POST routes.
- Continue prohibiting real memory write/update/archive routes.
- Check that dry-run routes exist.
- Check that real Memory Writer execute routes are absent.
- Check `sideEffects=false` semantic compliance.
- Check Memory Writer execute capability is absent.

---

## 27. Playwright Smoke Strategy

Phase 1D implementation smoke tests must cover:

- Memory Writer panel is visible.
- WRITE / UPDATE / ARCHIVE preview controls are visible.
- No execute buttons exist.
- No real write requests are sent.
- Dry-run requests use `127.0.0.1:5181`.
- Results display "No files were modified."
- `sideEffects=false` displayed.
- All 5 themes render correctly.
- All viewports have no horizontal overflow.
- Console errors = 0.
- CORS errors = 0.
- Asset 404 errors = 0.

**Smoke runner must not create real Memory items.**

---

## 28. Side-Effect Validation Strategy

### 28.1 Formal dev-home Hash Validation

Before and after calling all 3 dry-run routes, compute SHA-256 hashes of:

- `state.db`
- `MEMORY.md`
- `memory/indexes/` (all files)
- `memory/records/` (all files)
- `memory/events.jsonl`
- `memory/snapshots/` (all files)
- `memory/reviews/` (all files)

All hashes must be identical after dry-run calls.

### 28.2 Additional Checks

- No new directories created.
- No new lock files.
- No event append.
- No snapshot files.
- No Review Queue items.
- No mtime changes that alter file content.

### 28.3 Temp Fixture Tests

Unit tests use `pytest tmp_path` with fabricated memory data. Tests must not copy the formal dev-home.

---

## 29. Test Fixture Strategy

### 29.1 Required Fixtures

| Fixture | Purpose |
|---------|---------|
| WRITE allowed | Score ≥ 80, no match, valid candidate |
| WRITE duplicate | Score ≥ 80, exact match exists |
| WRITE review range | Score 65–79, valid candidate |
| WRITE skip | Score < 65 |
| UPDATE allowed | High similarity, same category, core tags match, not protected |
| UPDATE protected P0 | Target importance P0 |
| UPDATE protected permanent | Target TTL permanent |
| UPDATE category mismatch | Different category |
| UPDATE no core tag overlap | Only generic tags overlap |
| ARCHIVE allowed | Active item, not protected |
| ARCHIVE P0 blocked | P0 importance item |
| ARCHIVE permanent blocked | permanent TTL item |
| ARCHIVE already archived | Status already "archived" |
| REVIEW recommendation | Decision is REVIEW, verify wouldEnqueue |
| SKIP decision | Score too low, verify no effects |
| SKIP_DUPLICATE decision | Near-exact match |
| Invalid category | Category name validation |
| Invalid memory ID | ID format validation |
| Missing memory | ID valid but item not found |

### 29.2 Test Isolation

- All tests use `tmp_path` for HERMES_HOME.
- Tests create minimal memory scaffolding (MEMORY.md, category index, items).
- Tests verify zero side effects by comparing directory state before/after.

---

## 30. Risks

### P0 (Blockers)

None identified. The dry-run can be built entirely from safe read-only functions.

If audit reveals that read-only functions create files (e.g., `ensure_memory_scaffold()` called transitively), this would be a P0 blocker that must be resolved before Phase 1D implementation.

### P1 (Must Resolve Before Phase 1D Implementation)

1. **P0/permanent archive protection not enforced in core.** The `update_memory_item(archive=True)` path does not check P0/permanent. Phase 1D dry-run must enforce this independently.
2. **`ensure_memory_scaffold()` creates files.** Any accidental call to `append_event()`, `backup_file()`, or `ensure_memory_scaffold()` directly would create directories and files. Dry-run service must avoid all such calls.
3. **Multi-file writes are non-transactional.** WRITE creates backup + updates index + creates record + appends event — no rollback. Dry-run is safe because it never writes, but documentation should note this for future execute phases.
4. **`_ensure_auto_category()` is highly invasive.** It creates category, writes root, creates index, appends event. Dry-run must detect "would auto-create category" but never call this function.
5. **Similarity thresholds may depend on runtime config.** Phase 1D must use default thresholds but display the config values used.
6. **Archive is status change, not file move.** Recovery requires manual status update.

### P2 (Should Resolve During Phase 1D Implementation)

1. **Full item scan performance.** `find_best_memory_match()` scans all items. Large memory stores may be slow.
2. **Score breakdown exposure.** Should the full breakdown be returned or a summary?
3. **Snapshot naming uses timestamps.** Dry-run should predict snapshot names but not create them.
4. **Tag merge rules.** UPDATE replaces tags entirely — no merge logic.
5. **TTL format semantics.** `temporary` and `session` TTLs may have unclear expiration behavior.

---

## 31. Non-Goals

Phase 1D-00 and Phase 1D do NOT include:

- Implementing any Memory Writer API routes.
- Implementing real WRITE, UPDATE, or ARCHIVE execution.
- Auto-enqueueing Review Queue items.
- Calling the Agent or LLM.
- Executing any tools.
- Adding SSE or WebSocket connections.
- Modifying the current 18-path OpenAPI.
- Modifying dev-check.
- Modifying frontend code.
- Modifying backend business code.
- Modifying the formal dev-home (`/Users/huangruibang/Code/hermes-home-dev`).
- Accessing or modifying the production environment (`/Users/huangruibang/.hermes`).
- Starting Phase 1D implementation.

---

## 32. Acceptance Criteria

1. ✅ Current branch is `dev-huangruibang`.
2. ✅ Local and remote baselines match (HEAD `79b92142b`).
3. ✅ Worktree was clean before execution.
4. ✅ Memory Writer core code fully audited.
5. ✅ WRITE decision flow documented.
6. ✅ UPDATE decision flow documented.
7. ✅ ARCHIVE flow documented.
8. ✅ REVIEW decision documented.
9. ✅ SKIP decision documented.
10. ✅ Duplicate detection strategy documented.
11. ✅ Similarity scoring strategy documented.
12. ✅ P0/permanent/protected strategy documented.
13. ✅ Snapshot/backup behavior documented.
14. ✅ Lock/concurrency behavior documented.
15. ✅ Hidden side effects documented.
16. ✅ Side-effect matrix completed.
17. ✅ Safe read-only functions listed.
18. ✅ Forbidden write functions listed.
19. ✅ 3 dry-run route drafts frozen.
20. ✅ WRITE request DTO frozen.
21. ✅ UPDATE request DTO frozen.
22. ✅ ARCHIVE request DTO frozen.
23. ✅ Unified response DTO frozen.
24. ✅ DTO whitelist frozen.
25. ✅ Redaction and truncation rules frozen.
26. ✅ Error model frozen.
27. ✅ Protection rules frozen.
28. ✅ Frontend information architecture frozen.
29. ✅ OpenAPI strategy: current 18 paths unchanged.
30. ✅ dev-check strategy defined.
31. ✅ Playwright smoke strategy defined.
32. ✅ Side-effect validation strategy defined.
33. ✅ Test fixture strategy defined.
34. ✅ No API implemented.
35. ✅ No business code modified.
36. ✅ No frontend code modified.
37. ✅ No OpenAPI modified.
38. ✅ No Memory files modified.
39. ✅ No Review Queue modified.
40. ✅ memory-check PASS.
41. ✅ dev-check PASS.
42. ✅ compileall PASS.
43. ✅ Documentation completed.
44. ✅ Local commit created.
45. ✅ Not pushed.
46. ✅ Final worktree clean.
47. ✅ Production Gateway PID 1717 unaffected.
48. ✅ Dev Gateway stopped.
49. ✅ Ports 5180/5181 free.
50. ✅ Phase 1D implementation not started.

---

## 33. Next Phase

**Phase 1D: Memory Writer Dry-Run Panel Implementation.**

This scope freeze document provides the complete contract for that implementation. The implementation phase must:

1. Create a new `DevMemoryWriterService` class with dry-run methods.
2. Add 3 dry-run POST routes to `dev_web_api.py`.
3. Add request/response DTOs to `dev_web_schemas.py`.
4. Add error codes to `dev_web_errors.py`.
5. Update OpenAPI spec (18 → 21 paths).
6. Update dev-check.
7. Build the frontend Writer Preview panel.
8. Write unit tests with isolated fixtures.
9. Run side-effect hash validation on formal dev-home.
10. Run Playwright smoke tests.

This scope freeze does NOT authorize beginning Phase 1D implementation.
