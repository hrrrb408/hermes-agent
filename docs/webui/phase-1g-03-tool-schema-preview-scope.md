# Phase 1G-03: Tool Schema Preview — Scope, Contract and Safety Freeze

## Document Information

| Field | Value |
|-------|-------|
| Phase | 1G-03-00 |
| Title | Tool Schema Preview Scope, Contract and Safety Freeze |
| Status | Scope Frozen |
| Date | 2026-06-11 |
| Author | Dev Agent (Phase 1G-03-00 scope freeze) |
| Dependencies | Phase 1G-02 completed and pushed |
| Branch | dev-huangruibang |
| Base commit | 401fd07a4 |
| Implementation | Documentation only — no business code modified |

### Scope

This document:

1. Records the Phase 1G-02 completion baseline
2. Evaluates candidate directions for Phase 1G-03
3. Selects Tool Schema Preview as the Phase 1G-03 scope
4. Freezes the data model boundary for Schema Preview
5. Freezes redaction and sanitization rules
6. Freezes DTO field whitelists and forbidden fields
7. Freezes API design principles (GET-only, no side effects)
8. Freezes frontend display principles (read-only panel)
9. Freezes the testing matrix
10. Freezes acceptance criteria
11. Freezes the phase breakdown into implementation sub-tasks
12. Does **not** implement any API, service, frontend component, or test

### Freeze Declaration

All contracts in this document are **frozen** — they may only be modified by a subsequent scope document or explicit user instruction. No implementation task may deviate from these contracts without a formal amendment.

---

## 1. Background

Phase 1G established a Tool Execution Safety Framework. The sub-phase roadmap is:

| Phase | Name | Scope | Status |
|-------|------|-------|--------|
| 1G-00 | Tool Execution Safety Framework Scope Freeze | Inventory, risk classification, denylist, candidate allowlist | ✅ Completed |
| 1G-01 | Tool Inventory + Static Policy Module | Static policy data, TOOL_POLICY_INVENTORY | ✅ Completed |
| 1G-02 | Tool Policy Read-Only API / Panel | GET /policy, GET /catalog, frontend panel | ✅ Completed |
| **1G-03** | **Tool Schema Preview** | **Build and display minimal Schema, do NOT send to Provider** | **Scope Frozen** |
| 1G-04 | Tool Call Dry-Run | Validate tool name + args without dispatch | Not Started |
| 1G-05 | Fake Tool Fixture Execute | Temporary HERMES_HOME, fake implementations | Not Started |
| 1G-06 | Dev-Only R0/R1 Execute | Final approved R0/R1 tools with full safety chain | Not Started |

Phase 1G-02 delivered a read-only Tool Policy API with two GET routes, a frontend panel showing policy status and tool catalog, and full browser integration. The catalog currently exposes policy metadata (risk level, capabilities, policy status) but does **not** expose any tool schema information — all three capability flags are hardcoded to `false`:

- `schemaPreviewAvailable = false`
- `dryRunAvailable = false`
- `executionAvailable = false`

Phase 1G-03 will enable `schemaPreviewAvailable` for appropriate tools by generating safe, redacted schema previews from static tool registration data.

---

## 2. Phase 1G-02 Baseline

### Git Baseline

| Field | Value |
|-------|-------|
| Branch | dev-huangruibang |
| Local HEAD | 401fd07a4337d1960d6448168fafc8ad20a7d621 |
| Remote HEAD | 401fd07a4337d1960d6448168fafc8ad20a7d621 |
| Local ahead | 0 |
| Remote ahead | 0 |
| Diverged | No |
| Tracked worktree | Clean |
| Untracked | .claude/ (pre-existing, untouched) |

### Phase 1G-02 Completion Metrics

| Metric | Value |
|--------|-------|
| Tool Inventory | 71 tools |
| Risk total | 71 (unique Primary Risk model) |
| STATIC_DENYLIST | 26 tools |
| CANDIDATE_ALLOWLIST | 6 tools (R0/R1 only) |
| STATIC_ALLOWLIST | 0 (empty frozenset) |
| Tool GET routes | 2 (`/policy`, `/catalog`) |
| Tool write routes | 0 |
| OpenAPI paths | 29 |
| Runtime routes | 29 |
| Tool Execution | Disabled |
| Provider Tool Schema | Not sent |
| Tool Dispatch | 0 |
| Tool Audit | Absent |
| `schemaPreviewAvailable` | `false` (all tools) |
| `dryRunAvailable` | `false` (all tools) |
| `executionAvailable` | `false` (all tools) |

### Tool Policy Data Available

The current `DevToolPolicyQueryService` reads from the static `TOOL_POLICY_INVENTORY` in `dev_web_tool_policy.py`. Each entry has:

- `canonical_name`, `primary_risk`, `capabilities`, `policy_status`
- `permanently_denied`, `candidate_allowlisted`, `statically_allowed`
- `rationale` (free text, currently truncated to 200 chars as `rationale_preview`)

The tool registry (`tools/registry.py`) stores per-tool schema definitions in JSON Schema format, accessible via `registry.get_schema(name)` without executing the tool. This is the data source for Schema Preview.

---

## 3. Why Phase 1G-03 Starts with Schema Preview

Schema Preview is the natural next step after the Tool Policy Read-Only API because:

1. **Low risk**: Reading static schema data from the registry is a pure read operation. No tool execution, no handler invocation, no network calls.
2. **Builds on existing foundation**: The 71-tool inventory, risk classification, and policy framework from 1G-01/1G-02 provide the policy context for which schemas to show and how to redact them.
3. **Developer value**: Before any tool can be dry-run or executed, developers need to understand its input/output structure. Schema Preview provides this understanding without any execution risk.
4. **Incremental safety**: The redaction and sanitization rules established here will be reused by Dry-Run (1G-04) and Execution (1G-05+) phases.
5. **No provider interaction**: Schema Preview is entirely local. It never sends tool schemas to any LLM provider, so there is no risk of prompt injection via tool definitions.

---

## 4. Options Considered

### Option A: Tool Schema Preview (Selected)

**Definition**: Generate and display a redacted preview of each tool's input schema, based on static registration data from `tools/registry.py`. No handler invocation, no provider sending, no execution.

| Aspect | Assessment |
|--------|-----------|
| Risk level | Low — pure read from registry data |
| Side effects | None — no handler, no dispatch, no network |
| Developer value | High — enables understanding of tool parameters |
| Implementation complexity | Medium — requires sanitizer/redactor |
| Foundation for future phases | High — sanitizer reuse in Dry-Run/Execute |
| **Decision** | **Selected for Phase 1G-03** |

### Option B: Tool Dry-Run Preview (Deferred)

**Definition**: Simulate a tool call plan or validate arguments against the schema without executing the tool.

| Aspect | Assessment |
|--------|-----------|
| Risk level | Medium — may require argument generation, context binding, Agent loop involvement |
| Side effects | Low if well-isolated, but boundary is blurry |
| Developer value | High — but depends on Schema Preview |
| Implementation complexity | High — parameter generation, validation chain |
| Dependency | Should build on Schema Preview, not precede it |
| **Decision** | **Deferred to Phase 1G-04** |

### Option C: Controlled Tool Execution (Out of Scope)

**Definition**: Allow selected tools to execute under strict allowlist and sandbox.

| Aspect | Assessment |
|--------|-----------|
| Risk level | High — involves real side effects |
| Side effects | Yes — filesystem, network, process execution |
| Prerequisites | Schema Preview + Dry-Run + Audit + Kill Switch |
| **Decision** | **Out of scope for 1G-03, planned for 1G-05/1G-06** |

### Option D: Provider Tool Schema Sending (Out of Scope)

**Definition**: Send tool schemas to the LLM provider so the model can invoke tools.

| Aspect | Assessment |
|--------|-----------|
| Risk level | High — model may attempt tool calls, prompt injection surface |
| Side effects | Yes — triggers provider-side tool use contract |
| Prerequisites | Schema Preview + Dry-Run + full safety chain |
| **Decision** | **Out of scope, not planned until much later** |

### Decision Summary

| Option | Risk | Decision | Rationale |
|--------|------|----------|-----------|
| A: Schema Preview | Low | **Selected** | Pure read, no side effects, foundation for future phases |
| B: Dry-Run | Medium | Deferred to 1G-04 | Depends on Schema Preview |
| C: Execution | High | Out of scope | Requires full safety chain |
| D: Provider Sending | High | Out of scope | Requires full safety chain + provider contract |

---

## 5. Frozen Scope

### Selected Scope

**Phase 1G-03 = Tool Schema Preview: Read-only, local-only, no Provider Schema send, no Tool Dispatch, no Tool Execution, no Tool Audit, no allowlist change.**

### In Scope

1. Define a static Tool Schema Preview data model (DTO)
2. Generate safe schema previews from static tool registry metadata
3. Sanitize and redact schema data before any API exposure
4. Expose field types, required fields, descriptions, enum values, constraints
5. Indicate per-tool `schemaPreviewAvailable` status (replacing the hardcoded `false`)
6. Provide unavailable reasons for tools whose schemas cannot be previewed
7. Frontend read-only Schema Preview panel
8. API uses GET-only routes
9. Does NOT send schemas to any Provider
10. Does NOT execute any tool
11. Does NOT call any tool handler
12. Does NOT dispatch any tool
13. Does NOT create any Tool Audit entries
14. Does NOT modify `STATIC_ALLOWLIST`
15. Does NOT modify `STATIC_DENYLIST`
16. Does NOT modify `CANDIDATE_ALLOWLIST`
17. Does NOT enable Tool Execution

### Explicitly Out of Scope

1. Tool Dry-Run (Phase 1G-04)
2. Tool Execution (Phase 1G-05+)
3. Tool Dispatch (any phase)
4. Tool Audit creation (Phase 1G-05+)
5. Provider Tool Schema Sending (much later)
6. Agent tool use (much later)
7. Modifying `STATIC_ALLOWLIST`
8. Modifying `STATIC_DENYLIST`
9. Modifying `CANDIDATE_ALLOWLIST`
10. Real tool parameter generation
11. Real tool invocation
12. LLM-assisted schema inference
13. Schema versioning or migration
14. Cross-tool dependency analysis

---

## 6. Safety Invariants

The following invariants must hold throughout Phase 1G-03 implementation:

| # | Invariant | Description |
|---|-----------|-------------|
| S1 | No handler invocation | Schema Preview must never call any tool's handler function |
| S2 | No tool dispatch | No tool dispatch mechanism is created or triggered |
| S3 | No provider schema send | Tool schemas are never sent to any LLM provider |
| S4 | No tool execution | No tool is executed, directly or indirectly |
| S5 | No tool audit | No audit entries are created |
| S6 | No allowlist change | `STATIC_ALLOWLIST` remains empty |
| S7 | No denylist change | `STATIC_DENYLIST` remains unchanged (26 tools) |
| S8 | No candidate change | `CANDIDATE_ALLOWLIST` remains unchanged (6 tools) |
| S9 | GET-only API | All new routes must be GET; no POST/PATCH/PUT/DELETE |
| S10 | No write side effects | No file creation, modification, or deletion |
| S11 | Read-only registry access | May read from `registry.get_schema()` but never modify registry state |
| S12 | Sanitized output | All schema data passes through the sanitizer before API response |

---

## 7. Data Model Boundary

### 7.1 Source Data

Schema Preview reads from two sources:

| Source | Location | Access Method | Data Available |
|--------|----------|--------------|----------------|
| Tool Registry | `tools/registry.py` | `registry.get_schema(name)` | JSON Schema dict with name, description, parameters |
| Tool Policy | `hermes_cli/dev_web_tool_policy.py` | `TOOL_POLICY_INVENTORY` | Risk level, capabilities, policy status, denylist/candidate membership |

**The registry schema dict has this structure:**

```python
{
    "name": str,           # Tool canonical name
    "description": str,    # Tool description
    "parameters": {
        "type": "object",
        "properties": {
            "<field_name>": {
                "type": str | list[str],
                "description": str,
                "enum": list[str],       # optional
                "default": Any,          # optional
                "minimum": number,       # optional
                "maximum": number,       # optional
                "items": dict,           # optional (for arrays)
                # ... other JSON Schema keywords
            }
        },
        "required": list[str]
    }
}
```

### 7.2 Allowed DTO Fields

The following fields are allowed in Schema Preview responses:

#### Top-Level Schema Preview DTO

| Field | Type | Description |
|-------|------|-------------|
| `canonicalName` | string | Tool canonical name |
| `risk` | string | Primary risk level (R0–R5) |
| `capabilities` | list[string] | Tool capability tags |
| `schemaPreviewAvailable` | boolean | Whether schema preview is available |
| `schemaShape` | string | Top-level schema shape: `"object"`, `"array"`, `"primitive"`, or `"unknown"` |
| `inputFields` | list[SchemaFieldDTO] | Redacted field definitions |
| `redactionStatus` | string | `"clean"`, `"redacted"`, or `"unavailable"` |
| `reasonCode` | string \| null | Unavailability reason code |
| `unavailableReason` | string \| null | Human-readable unavailability reason |

#### Per-Field DTO (SchemaFieldDTO)

| Field | Type | Description |
|-------|------|-------------|
| `fieldName` | string | Parameter name |
| `fieldType` | string | JSON Schema type (sanitized to one of: `"string"`, `"number"`, `"integer"`, `"boolean"`, `"array"`, `"object"`, `"null"`, `"unknown"`) |
| `required` | boolean | Whether this field is required |
| `descriptionPreview` | string \| null | Truncated description (max 240 chars) |
| `enumPreview` | list[string] \| null | Enum values (max 20 items, each max 80 chars) |
| `defaultPresence` | boolean | Whether a default value exists (value NOT exposed) |
| `constraintsPreview` | string \| null | Brief constraint summary (max 120 chars) |

### 7.3 Forbidden Fields

The following fields must NEVER appear in any Schema Preview response:

| Category | Forbidden Values |
|----------|-----------------|
| Callable internals | `handler`, `callable`, `function object`, `module object`, `check_fn`, `is_async` |
| Filesystem paths | `absolute path`, `source path`, `module path`, `file_path` of handler |
| Runtime internals | `stack trace`, `thread id`, `process id`, `memory address` |
| Secrets | `environment variables`, `API key`, `token`, `authorization header`, `cookie`, `secret`, `password`, `credential` |
| Raw data | `raw provider schema`, `raw tool object`, `runtime object repr`, `unbounded docstring` |
| Dynamic overrides | `dynamic_schema_overrides` callable or its return value |
| Execution config | `max_result_size_chars`, `override` flag |
| Environment requirements | `requires_env` (exposes which API keys are needed) |

**If any forbidden field is encountered during schema generation, the entire schema preview must return `redactionStatus = "unavailable"` with an appropriate reason code.**

### 7.4 Description Truncation Rules

| Field | Max Length | Truncation Strategy |
|-------|-----------|-------------------|
| `descriptionPreview` (per field) | 240 chars | Truncate at last word boundary before limit, append `"…"` |
| `unavailableReason` | 240 chars | Truncate at last word boundary before limit |
| `constraintsPreview` | 120 chars | Truncate at last word boundary before limit, append `"…"` |
| `enumPreview` items | 20 values max | Each value truncated to 80 chars |
| Nested depth | 4 levels max | Deeper nesting → field shows `fieldType = "object"` with `constraintsPreview = "nested structure truncated"` |
| Field count | 100 fields max | Excess fields omitted; `redactionStatus` notes truncation |
| Schema description (top-level) | 240 chars | Truncated same as field description |

### 7.5 Redaction Rules

The sanitizer must apply these rules in order:

1. **Forbidden field check**: If any field name in the raw schema matches a forbidden pattern (e.g., contains `password`, `secret`, `token`, `key`, `credential`), set `redactionStatus = "redacted"` and omit the field's `descriptionPreview` and `enumPreview`.
2. **Description sanitization**: Remove any file paths, URLs, API endpoints, or implementation details from descriptions. Replace with `"[redacted]"`.
3. **Enum sanitization**: If enum values contain file paths, URLs, or secrets, redact the entire `enumPreview` for that field.
4. **Type normalization**: Map all JSON Schema types to the allowed set. Unknown or complex types → `"unknown"`.
5. **Nesting truncation**: At depth > 4, replace nested structure with a summary.
6. **Count truncation**: If > 100 fields, truncate and note in `redactionStatus`.

---

## 8. Risk-Based Availability

Schema Preview availability is governed by the tool's risk classification and policy status:

| Risk / Policy | `schemaPreviewAvailable` | Behavior |
|---------------|--------------------------|----------|
| R0 (Pure computation) | `true` | Full schema preview with all fields |
| R1 (Read-only local query) | `true` | Full schema preview, environment requirements hidden |
| R2 (Read-only external network) | `true` | Full schema preview, API key requirements hidden |
| R3 (Controlled write) | `true` | Schema preview with enhanced redaction — hide sensitive field details that could reveal write targets |
| R4 (Process/execution) | `false` | Show `reasonCode = "RISK_R4_EXECUTION"` and `unavailableReason` |
| R5 (High-risk system) | `false` | Show `reasonCode = "RISK_R5_SYSTEM"` and `unavailableReason` |
| Permanent Denylist (26 tools) | `false` | Show `reasonCode = "PERMANENTLY_DENIED"` and `unavailableReason` |
| Candidate Allowlist (6 tools) | `true` | Full schema preview (still cannot execute) |
| STATIC_ALLOWLIST | N/A | Remains empty; no tool gets special preview treatment from allowlist |
| Unlisted tools | `false` | Show `reasonCode = "UNLISTED"` and `unavailableReason` |

### Critical Principle

> **Schema Preview availability does NOT imply execution availability.**
>
> A tool may have `schemaPreviewAvailable = true` while `executionAvailable = false` and `dryRunAvailable = false`. Preview is a read-only inspection capability, not an authorization to execute.

### Availability Count Estimate

Based on the current 71-tool inventory:

| Category | Count | `schemaPreviewAvailable` |
|----------|-------|--------------------------|
| R0 tools | 1 | `true` |
| R1 tools | 5 | `true` |
| R2 tools | 19 | `true` |
| R3 tools | 26 | `true` (with enhanced redaction) |
| R4 tools | 17 | `false` |
| R5 tools | 3 | `false` |
| **Preview available** | **51** | |
| **Preview unavailable** | **20** | |

Note: Some R4/R5 tools are also on the Denylist. The Denylist check takes priority — if a tool is both Denylisted and R4, the reason code is `PERMANENTLY_DENIED`.

---

## 9. API Design Principles

### 9.1 Allowed Methods

- **GET only** — no mutations of any kind

### 9.2 Forbidden Methods

- POST, PATCH, PUT, DELETE
- OPTIONS (beyond CORS preflight)
- Any method that could trigger side effects

### 9.3 Candidate Routes

Two approaches are considered:

#### Option A: Dedicated Schema Routes

```
GET /api/dev/v1/tools/schemas              # List all schema previews
GET /api/dev/v1/tools/schemas/{canonicalName}  # Single tool schema preview
```

- OpenAPI paths: 29 → 31 (+2)
- Clean separation from policy/catalog routes
- Requires new route registration

#### Option B: Extend Existing Catalog

Add `schemaPreview` embedded object to existing catalog items:

```
GET /api/dev/v1/tools/catalog?include=schema  # Embed schema in catalog
```

- OpenAPI paths: 29 (no new paths)
- Requires query parameter support
- Larger response payloads

### 9.4 Recommendation

**Option A is recommended** because:

1. Clean separation of concerns (policy vs. schema)
2. Schema preview is optional — users who don't need it don't pay the cost
3. Easier to test and audit independently
4. Follows the pattern established by 1G-02 (dedicated routes)

### 9.5 API Invariants

| Invariant | Value |
|-----------|-------|
| All new routes are GET-only | Yes |
| No POST/PATCH/PUT/DELETE routes | Yes |
| No tool write routes | Yes (Tool write routes = 0) |
| No provider schema sending | Yes |
| No execution triggers | Yes |
| No audit creation | Yes |
| OpenAPI path count after 1G-03 | 31 (29 + 2, if Option A) |

### 9.6 Pre-Implementation Re-evaluation

Before implementing any API route, the following must be re-evaluated:

1. Whether new paths are needed or existing catalog can be extended
2. Impact on OpenAPI total path count
3. GET-only constraint maintained
4. Tool write routes remain at 0
5. Provider schema sending remains disabled
6. Response payload size with 51 schema previews

---

## 10. Frontend Design Principles

### 10.1 Allowed UI Elements

- Read-only Schema Preview Panel (sub-tab under existing Tools tab)
- Schema summary cards (tool name, risk badge, field count)
- Expandable field list (field name, type, required status, description)
- Search/filter by field name
- Filter by `schemaPreviewAvailable` (available / unavailable)
- Redaction badge for sanitized fields
- Risk badge per tool
- Unavailable reason display
- Copy-safe-summary button (copies redacted text, never raw schema)

### 10.2 Forbidden UI Elements

The following must NOT appear in the Schema Preview panel:

| Forbidden Element | Reason |
|-------------------|--------|
| "Run" button | Implies execution capability |
| "Execute" button | Implies execution capability |
| "Dry Run" button | Not available in 1G-03 |
| "Send to Provider" button | Provider schema sending is out of scope |
| "Generate Args" button | Parameter generation is out of scope |
| "Autofill Args" button | Implies execution intent |
| "Call Tool" button | Implies execution capability |
| "Test Tool" button | Implies execution capability |
| "Save Allowlist" button | Allowlist modification is out of scope |
| "Enable Tool" button | Tool enabling is out of scope |
| "Edit Schema" button | Schema editing is out of scope |
| Any button whose label implies execution or mutation | Safety principle |

**Button and action labels must not imply execution capability, even implicitly.**

### 10.3 Copy Behavior

- The "Copy Summary" action must copy only the redacted, sanitized text representation
- Never copy raw JSON Schema
- Never copy handler references, file paths, or environment variable names

### 10.4 Network Safety

- Frontend must use GET-only requests
- No POST/PATCH/PUT/DELETE requests to schema endpoints
- No requests to external services (no provider, no tool execution)
- No WebSocket connections for schema preview

### 10.5 Accessibility

- Schema field table must be keyboard navigable
- ARIA labels for risk badges, redaction indicators
- Screen reader announces field type and required status
- Color is not the sole indicator for risk level or availability

---

## 11. Testing Strategy

### 11.1 Backend Tests

| Area | What to Test |
|------|-------------|
| Schema sanitizer | Correct redaction of forbidden fields |
| Field whitelist | Only allowed fields appear in output |
| Forbidden field redaction | Any forbidden field in input → redacted or unavailable |
| Nested depth limit | Depth > 4 → truncated |
| Enum limit | > 20 enum values → truncated |
| Description truncation | > 240 chars → truncated with "…" |
| Risk-based availability | R0–R3 → available, R4–R5 → unavailable |
| Denylist unavailable | Denylisted tools → `PERMANENTLY_DENIED` reason |
| Candidate allowlist preview | Candidate tools → available, but `executionAvailable` still `false` |
| STATIC_ALLOWLIST unchanged | Still empty |
| No dispatch | No dispatch mechanism called |
| No audit | No audit entries created |
| No provider schema sent | No provider API calls |
| GET-only API | All routes are GET |
| OpenAPI schema | New paths documented correctly |
| Error handling | Invalid tool name → 404, denied tool → 200 with unavailable reason |
| Pagination | Schema list supports pagination |
| Sanitization of raw registry schema | Verifies no handler, path, secret leaks |

### 11.2 Frontend Tests

| Area | What to Test |
|------|-------------|
| API client | GET-only requests, no mutation methods |
| Store loading/error/retry | Schema loading states, error handling |
| Schema panel render | Cards, fields, badges render correctly |
| Risk badge | Correct risk level display |
| Redaction badge | Redacted fields show indicator |
| Unavailable reason | Unavailable tools show reason |
| Search/filter | Filter by name, availability |
| No execute button | No Run/Execute/Dry-Run buttons present |
| No mutation request | No POST/PATCH/PUT/DELETE in network layer |
| Network safety | No external requests |
| Accessibility | Keyboard nav, ARIA labels, focus management |
| Responsive | Works at mobile/tablet/desktop breakpoints |
| Theme matrix | All 5 themes render schema panel correctly |
| `schemaPreviewAvailable` flag | Store validates flag consistency with backend |

### 11.3 Browser Smoke Tests

| Check | Expected |
|-------|----------|
| Policy panel still works | No regression from 1G-02 |
| Schema panel loads | New panel renders without errors |
| No POST/PATCH/PUT/DELETE | Network tab shows only GET requests |
| No provider requests | No requests to LLM provider URLs |
| No external requests | No requests outside dev WebUI backend |
| No console errors | No JavaScript errors |
| No overflow | Long descriptions and field names don't break layout |
| Schema unavailable tools | Display reason correctly |
| Schema available tools | Show fields correctly |

### 11.4 Security Regression Tests

| Check | Expected |
|-------|----------|
| OpenAPI paths = 31 | 29 + 2 new GET routes |
| Runtime routes = 31 | Matching OpenAPI |
| Tool GET routes = 4 | 2 from 1G-02 + 2 new schema routes |
| Tool write routes = 0 | No write routes |
| STATIC_ALLOWLIST = empty | Not modified |
| Tool Execution = disabled | Still disabled |
| Provider Schema = not sent | Still not sent |
| Tool Dispatch = 0 | Still zero |
| Tool Audit = absent | Still absent |

---

## 12. Browser Smoke Strategy

Browser smoke tests for Phase 1G-03 must verify:

1. **Existing Tool Policy panel** — no regression from 1G-02
2. **New Schema Preview sub-tab** — renders correctly under Tools tab
3. **Schema available tools** — show expandable field list
4. **Schema unavailable tools** — show reason and risk badge
5. **Search and filter** — work as expected
6. **All 5 themes** — schema panel renders in Obsidian, Paper, Song, Ink, Sakura Night
7. **Responsive breakpoints** — mobile, tablet, desktop
8. **No network violations** — only GET requests to dev backend
9. **No console errors** — clean JavaScript console
10. **No layout overflow** — long text handled gracefully

---

## 13. Phase Breakdown

### Phase 1G-03-01: Static Schema Preview Model and Sanitizer

**Description**: Define the Schema Preview DTO model and implement the schema sanitizer/redactor.

| Aspect | Detail |
|--------|--------|
| Allowed files | `hermes_cli/dev_web_schemas.py` (new DTOs), `hermes_cli/dev_web_schema_preview.py` (new sanitizer), `tests/test_dev_web_schema_sanitizer.py` (new tests) |
| Forbidden files | `tools/registry.py`, `toolsets.py`, `hermes_cli/dev_web_api.py`, `apps/hermes-dev-webui/src/` |
| Test gate | Sanitizer unit tests pass (field whitelist, forbidden redaction, truncation, depth limit) |
| Acceptance | DTO matches Section 7.2; sanitizer enforces Sections 7.3, 7.4, 7.5; all backend sanitizer tests pass |
| Push | No (only after 1G-03-07) |

### Phase 1G-03-02: Schema Preview Read-Only Service

**Description**: Implement `DevSchemaPreviewQueryService` that reads from registry and policy inventory, applies sanitizer, and produces DTOs.

| Aspect | Detail |
|--------|--------|
| Allowed files | `hermes_cli/dev_web_schema_preview.py` (service methods), `tests/test_dev_web_schema_preview_service.py` (new tests) |
| Forbidden files | `tools/registry.py` (read-only access, no modifications), `hermes_cli/dev_web_api.py`, `apps/hermes-dev-webui/src/` |
| Test gate | Service tests pass (risk-based availability, denylist, candidate, pagination, error handling) |
| Acceptance | Service reads from registry via `get_schema()` only; applies sanitizer; no handler calls; no dispatch; no audit; availability per Section 8 |
| Push | No |

### Phase 1G-03-03: Schema Preview GET-only API and OpenAPI

**Description**: Add 2 GET routes for schema preview and update OpenAPI specification.

| Aspect | Detail |
|--------|--------|
| Allowed files | `hermes_cli/dev_web_api.py` (2 new GET routes), `docs/webui/openapi/dev-web-api-v1.yaml` (29 → 31 paths), `tests/test_dev_web_schema_preview_api.py` (new tests) |
| Forbidden files | `apps/hermes-dev-webui/src/`, `tools/`, `toolsets.py` |
| Test gate | API tests pass (GET-only, correct DTOs, error codes, no POST/PATCH/PUT/DELETE) |
| Acceptance | 2 new GET routes; OpenAPI at 31 paths; Tool GET routes = 4; Tool write routes = 0; no side effects |
| Push | No |

### Phase 1G-03-04: Frontend Types, API Client and Store

**Description**: Add TypeScript types, API client methods, and Pinia store for Schema Preview.

| Aspect | Detail |
|--------|--------|
| Allowed files | `apps/hermes-dev-webui/src/api/tool-schema.ts` (new), `apps/hermes-dev-webui/src/stores/toolSchemaPreview.ts` (new), `apps/hermes-dev-webui/src/tests/tool-schema-preview-store.spec.ts` (new) |
| Forbidden files | `hermes_cli/`, `tools/`, `docs/webui/openapi/` |
| Test gate | Store unit tests pass (loading, error, retry, validation, no mutation methods) |
| Acceptance | GET-only API client; store validates `schemaPreviewAvailable` flag; no POST/PATCH/PUT/DELETE; all 5 themes compatible |
| Push | No |

### Phase 1G-03-05: Schema Preview Panel UI

**Description**: Implement the Schema Preview sub-tab in the Workspace Tools panel.

| Aspect | Detail |
|--------|--------|
| Allowed files | `apps/hermes-dev-webui/src/components/workspace/` (new/modified components), `apps/hermes-dev-webui/src/tests/tool-schema-preview-panel.spec.ts` (new tests) |
| Forbidden files | `hermes_cli/`, `tools/`, `docs/webui/openapi/` |
| Test gate | Component tests pass (render, search, filter, risk badge, redaction badge, no execute buttons) |
| Acceptance | Sub-tab renders under Tools; shows schema fields; shows unavailable reasons; no execute/dry-run buttons; accessible; responsive |
| Push | No |

### Phase 1G-03-06: Browser Smoke, A11y and Network Safety

**Description**: Run browser smoke tests, accessibility checks, and network safety verification across all 5 themes.

| Aspect | Detail |
|--------|--------|
| Allowed files | Test files only |
| Forbidden files | All source files |
| Test gate | Smoke tests pass across 5 themes × 4 viewports |
| Acceptance | No regression; schema panel works; no POST/PATCH/PUT/DELETE; no external requests; no console errors; a11y passes |
| Push | No |

### Phase 1G-03-07: Docs, Release Verification and Push

**Description**: Update documentation, run final verification, and push.

| Aspect | Detail |
|--------|--------|
| Allowed files | `docs/webui/` (documentation updates) |
| Forbidden files | All source and test files (no changes) |
| Test gate | Full dev-check passes; memory-check passes; OpenAPI = 31; Tool write routes = 0 |
| Acceptance | Implementation plan updated; release notes written; all gates pass; push to origin/dev-huangruibang |
| Push | Yes (this is the only sub-phase that pushes) |

---

## 14. Acceptance Criteria

### 14.1 Scope Document

| # | Criterion |
|---|-----------|
| 1 | Phase 1G-03 scope document created |
| 2 | Tool Schema Preview selected as scope |
| 3 | Tool Dry-Run explicitly excluded |
| 4 | Tool Execution explicitly excluded |
| 5 | Provider Schema Sending explicitly excluded |
| 6 | Read-only constraint documented |
| 7 | No side effects constraint documented |
| 8 | No allowlist change constraint documented |

### 14.2 Safety Boundary

| # | Criterion |
|---|-----------|
| 9 | DTO whitelist defined (Section 7.2) |
| 10 | Forbidden fields defined (Section 7.3) |
| 11 | Redaction rules defined (Section 7.5) |
| 12 | Nested depth limit defined (Section 7.4) |
| 13 | Description truncation defined (Section 7.4) |
| 14 | Risk-based availability defined (Section 8) |
| 15 | Denylist handling defined (Section 8) |
| 16 | Candidate allowlist handling defined (Section 8) |

### 14.3 Phase Breakdown

| # | Criterion |
|---|-----------|
| 17 | Phase 1G-03-01 defined (Model/Sanitizer) |
| 18 | Phase 1G-03-02 defined (Service) |
| 19 | Phase 1G-03-03 defined (API/OpenAPI) |
| 20 | Phase 1G-03-04 defined (Frontend Data Layer) |
| 21 | Phase 1G-03-05 defined (Panel UI) |
| 22 | Phase 1G-03-06 defined (Smoke/A11y/Network) |
| 23 | Phase 1G-03-07 defined (Docs/Release) |

### 14.4 Non-Implementation

| # | Criterion |
|---|-----------|
| 24 | No API implementation in this scope document |
| 25 | No OpenAPI modification |
| 26 | No frontend implementation |
| 27 | No backend service implementation |
| 28 | No test modifications |
| 29 | No Tool Execution |
| 30 | No Provider Schema sending |
| 31 | No runtime writes |
| 32 | Production Gateway unaffected |

---

## 15. Risks and Non-Goals

### 15.1 Risks

| Risk | Mitigation |
|------|-----------|
| Schema data contains sensitive implementation details | Sanitizer enforces strict field whitelist and forbidden field patterns |
| Dynamic schema overrides may produce different schemas at runtime | Only base schema used; dynamic overrides are explicitly excluded |
| Large schemas may cause performance issues | Field count limit (100) and description truncation (240 chars) |
| Frontend may accidentally imply execution capability | Strict forbidden button list; test for absent buttons |
| Schema preview may be confused with execution authorization | Explicit "Schema Preview availability ≠ execution availability" principle |

### 15.2 Non-Goals

- This document does NOT design the Tool Dry-Run system (Phase 1G-04)
- This document does NOT design the Tool Execution system (Phase 1G-05+)
- This document does NOT design the Provider Tool Schema Sending system
- This document does NOT implement any code
- This document does NOT modify any existing code

---

## 16. Phase 1G-03-01 Completion Record

**Phase:** 1G-03-01 — Static Schema Preview Model and Sanitizer
**Status:** Completed
**Date:** 2026-06-11
**Base commit:** 287142c7411643a5091fa7394bcdba303961e9bd

### Deliverables

| File | Status |
|------|--------|
| `hermes_cli/dev_web_tool_schema_preview.py` | New — Static schema preview model, sanitizer, and availability logic |
| `tests/test_dev_web_tool_schema_preview.py` | New — 147 unit tests covering all sanitizer behaviors |

### Implementation Summary

1. **Data models:** `SchemaPreviewField`, `SchemaPreviewAvailability`, `ToolSchemaPreview` (frozen dataclasses)
2. **Sanitizer:** `sanitize_schema()` — pure function with forbidden field redaction, secret pattern detection, description/enum/constraints truncation, nested depth limit (4), field count limit (100), cycle-safe recursion
3. **Risk-based availability:** `determine_schema_preview_availability()` — R0/R1/R2 available, R3 available with enhanced redaction, R4/R5 unavailable, permanent denylist unavailable, candidate allowlist available
4. **Builder:** `build_schema_preview()` — top-level pure function producing JSON-safe `ToolSchemaPreview`
5. **Convenience:** `preview_from_policy_name()` — looks up tool in policy inventory
6. **Serialization:** `to_safe_dict()` — whitelist-only JSON-safe output on all models

### Architecture Constraints Verified

- stdlib only (no third-party imports)
- import side effects = 0 (beyond static policy constants)
- no file IO, no network IO, no environment reads
- no provider imports, no tool handler imports, no runtime DB access
- deterministic, JSON-serializable output
- explicit constants for all limits
- explicit reason codes for all outcomes

### Test Coverage

| Category | Tests |
|----------|-------|
| Import safety | 4 |
| Basic sanitization | 7 |
| Forbidden field redaction | 28 |
| Secret pattern redaction | 12 |
| Truncation | 12 |
| Depth limit | 2 |
| Field count limit | 2 |
| Cycle safety | 2 |
| Risk-based availability | 12 |
| No execution boundaries | 3 |
| JSON-safe output | 6 |
| Empty/invalid schema | 5 |
| Type normalization | 14 |
| Schema shape detection | 8 |
| STATIC_ALLOWLIST invariant | 2 |
| Denylist override | 2 |
| Candidate allowlist | 3 |
| preview_from_policy_name | 4 |
| Inventory counts | 4 |
| R3 enhanced redaction | 2 |
| Default presence | 3 |
| **Total** | **147** |

### Boundary Verification

| Metric | Value |
|--------|-------|
| API routes added | 0 |
| OpenAPI paths | 29 (unchanged) |
| Runtime routes | 29 (unchanged) |
| Tool GET routes | 2 (unchanged) |
| Tool write routes | 0 (unchanged) |
| STATIC_ALLOWLIST | empty (unchanged) |
| Tool Execution | disabled (unchanged) |
| Provider Tool Schema | not sent (unchanged) |
| Tool Dispatch | 0 (unchanged) |
| Tool Audit | absent (unchanged) |
| Frontend files modified | 0 |
| `hermes_cli/dev_web_api.py` modified | No |
| `docs/webui/openapi/` modified | No |
| `apps/hermes-dev-webui/src/` modified | No |

### What Was NOT Done

- No API routes added
- No OpenAPI specification modified
- No frontend code modified
- No provider schema sending
- No tool execution enabled
- No tool dispatch mechanism
- No tool audit created
- No STATIC_ALLOWLIST change
- No STATIC_DENYLIST change
- No CANDIDATE_ALLOWLIST change
- Phase 1G-03-02 not started

---

## 17. Next Step

Phase 1G-03-01 is completed. The next sub-phase is:

- Phase 1G-03-02 (Schema Preview Read-Only Service) may begin
- Phase 1G-03-02 must comply with all contracts in this document
- Phase 1G-03-02 must not deviate from any frozen boundary

---

## 18. Git Commit

| Field | Value |
|-------|-------|
| Commit type | `docs` |
| Scope | `webui` |
| Message | `docs(webui): define phase 1g-03 schema preview scope` |
| Files added | `docs/webui/phase-1g-03-tool-schema-preview-scope.md` |
| Files modified | `docs/webui/phase-1-implementation-plan.md` |
| Pushed | No |

---

*Phase 1G-03-00 Scope Freeze — Tool Schema Preview: read-only, local-only, no Provider Schema send, no Tool Dispatch, no Tool Execution, no Tool Audit, no allowlist change.*
