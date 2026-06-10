# Phase 1G-02-00: Tool Policy Read-Only API and Panel — Scope, Contract and Safety Freeze

| Field | Value |
|-------|-------|
| **Document** | Phase 1G-02-00 Scope Freeze |
| **Status** | Completed |
| **Date** | 2026-06-10 |
| **Author** | Dev Agent (Phase 1G-02-00 scope freeze) |
| **Type** | Documentation-only Scope Freeze |
| **Baseline Commit** | `773fb0bb8500b8663a3145258c33f1f60ef0a640` |

---

## 1. Document Information

This document freezes the scope, contracts, DTO whitelist, frontend information architecture,
route governance, testing strategy, and zero-side-effect boundary for Phase 1G-02:
Tool Policy Read-Only API and Panel Implementation.

**This is a documentation-only scope freeze.** No API, frontend, service, or runtime capability
may be implemented during this phase.

Phase 1G-02-00 produces this document and updates the implementation plan. Phase 1G-02
implementation is a separate future task that must not begin automatically.

---

## 2. Baseline

### 2.1 Git Baseline

| Item | Value |
|------|-------|
| Branch | `dev-huangruibang` |
| Local HEAD | `773fb0bb8500b8663a3145258c33f1f60ef0a640` |
| Remote HEAD | `773fb0bb8500b8663a3145258c33f1f60ef0a640` |
| Ahead / Behind | 0 / 0 |
| Tracked Worktree | Clean |
| `.claude/` | Pre-existing, untracked |

### 2.2 Environment Baseline

| Item | Value |
|------|-------|
| HERMES_HOME | `/Users/huangruibang/Code/hermes-home-dev` |
| HERMES_AGENT_RUN_ENABLED | `<unset>` |
| HERMES_TOOL_EXECUTION_ENABLED | `<unset>` |
| HERMES_AGENT_TOOLS_ENABLED | `<unset>` |
| Production Gateway | PID 1717 running (untouched) |
| Dev Gateway | Stopped |
| Port 5180 | Free |
| Port 5181 | Free |

### 2.3 Dev-Home Before Baseline

| Item | Value |
|------|-------|
| `state.db` SHA-256 | `b1911d16c1b5ad76b301ed5cd48bf6437be054490632ade79a5440923ee67945` |
| `state.db` Size | 360,607,744 bytes |
| `state.db` Mtime | 2026-06-09T20:29:57 |
| SQLite Tables | 17 (sessions, messages, messages_fts*, schema_version, state_meta, compression_locks) |
| `tool_execution_audit` table | Does not exist |
| Session Count | 417 |
| Message Count | 22,552 |
| `MEMORY.md` SHA-256 | `44be12a08bbe826132f9c67940e15433f2f8aebaf5680693dea5955b7ea51515` |
| Memory Indexes | 7 files (learning, projects, travel, user, preferences, hermes, dev-env) |
| Memory Records | 3 files |
| Memory Events | 9 lines |
| Snapshots | 9 files |
| Review Items | 4 files |
| Review Events | 9 lines |

### 2.4 API Baseline

| Item | Value |
|------|-------|
| OpenAPI Paths | 27 |
| Tool Routes | 0 |
| Agent Run Routes | 5 |
| POST Operations | Present (dry-run, preview, execute, agent runs) |
| Forbidden Legacy Routes | Absent |

### 2.5 Static Policy Baseline

| Item | Value |
|------|-------|
| Module | `hermes_cli/dev_web_tool_policy.py` |
| Inventory Count | 71 |
| Risk R0 | 1 (Pure Computation) |
| Risk R1 | 5 (Read-only Local) |
| Risk R2 | 19 (Read-only External) |
| Risk R3 | 26 (Controlled Write) |
| Risk R4 | 17 (Process/Code Execution) |
| Risk R5 | 3 (High-Risk System) |
| Permanent Denylist | 26 |
| Candidate Allowlist | 6 (clarify, read_file, search_files, session_search, skill_view, skills_list) |
| Static Allowlist | 0 (empty) |
| All `allowed` | `false` |
| Policy Tests | 81 passed |

---

## 3. Phase 1G-01 Inputs

Phase 1G-01 produced the static tool policy module (`hermes_cli/dev_web_tool_policy.py`) with:

- **Immutable Inventory**: 71 tools in a `MappingProxyType` with build-time integrity verification
- **Immutable Classifications**: Risk levels, capabilities, denylist, candidate list, allowlist
- **Pure Query Functions**: 9 public functions that only read in-memory data
- **Schema Safety Validation**: Pure function checking `additionalProperties: false`, depth, forbidden keys
- **Argument Structure Validation**: Pure function checking payload size, nesting, string/array limits
- **Default-Deny Decision**: All tools return `allowed=False` with reason codes
- **Zero External Dependencies**: No FastAPI, Provider, SessionDB, Registry, filesystem, database, or network imports
- **81 Tests**: Inventory integrity, risk classification, denylist, candidate, decisions, schema validation, argument validation, import safety, immutability, limits, completeness

Phase 1G-00 established the safety framework including:
- Primary Risk Model (R0–R5)
- Default-Deny Policy with 20-step decision chain
- Kill Switch: `HERMES_TOOL_EXECUTION_ENABLED`
- Provider Tool Schema boundary (never sent unless all conditions met)
- Dev-only environment guard

---

## 4. Static Policy Capability Audit

### 4.1 Safe Query Functions

The following functions from `dev_web_tool_policy.py` are **safe for direct API reuse**:

| Function | Signature | Returns | External Access |
|----------|-----------|---------|-----------------|
| `get_tool_policy` | `(canonical_name: str) -> ToolPolicyEntry \| None` | Single tool policy or None | None |
| `get_all_tool_policies` | `() -> tuple[ToolPolicyEntry, ...]` | All 71 entries | None |
| `get_tools_by_risk` | `(risk: ToolRiskLevel) -> tuple[ToolPolicyEntry, ...]` | Filtered entries | None |
| `is_permanently_denied` | `(canonical_name: str) -> bool` | Denylist check | None |
| `is_candidate_allowlisted` | `(canonical_name: str) -> bool` | Candidate check | None |
| `is_statically_allowed` | `(canonical_name: str) -> bool` | Allowlist check | None |
| `evaluate_static_tool_policy` | `(requested_name: str) -> ToolPolicyDecision` | Full decision | None |
| `validate_tool_schema_safety` | `(schema: Mapping) -> ToolSchemaValidationResult` | Schema validation | None |
| `validate_argument_structure` | `(arguments: object) -> ToolArgumentValidationResult` | Argument validation | None |

### 4.2 Immutable Data

| Constant | Type | Size |
|----------|------|------|
| `TOOL_POLICY_INVENTORY` | `MappingProxyType[str, ToolPolicyEntry]` | 71 |
| `ALL_CANONICAL_TOOLS` | `frozenset[str]` | 71 |
| `TOOLS_BY_RISK` | `MappingProxyType[ToolRiskLevel, frozenset[str]]` | 6 risk levels |
| `STATIC_DENYLIST` | `frozenset[str]` | 26 |
| `CANDIDATE_ALLOWLIST` | `frozenset[str]` | 6 |
| `STATIC_ALLOWLIST` | `frozenset[str]` | 0 |
| `RISK_RANK` | `MappingProxyType[ToolRiskLevel, int]` | 6 levels |

### 4.3 Dependency Verification

| Dependency | Present |
|------------|---------|
| Registry import | No |
| Filesystem access | No |
| Database access | No |
| Network access | No |
| Provider initialization | No |
| Tool Handler call | No |
| Tool Dispatch | No |
| Thread/subprocess creation | No |

### 4.4 API Suitability Mapping

| Static Function | Suitable For |
|-----------------|--------------|
| `get_all_tool_policies()` | Catalog List API, Policy Overview |
| `get_tools_by_risk()` | Catalog Risk Filter |
| `is_permanently_denied()` | Policy Status Badge |
| `is_candidate_allowlisted()` | Policy Status Badge |
| `is_statically_allowed()` | Policy Status Badge |
| `evaluate_static_tool_policy()` | Policy Detail, Capability Summary |
| `TOOL_POLICY_INVENTORY` | Inventory Count, Risk Distribution |
| `STATIC_DENYLIST` / `CANDIDATE_ALLOWLIST` / `STATIC_ALLOWLIST` | Policy Summary Counts |

---

## 5. Scope

Phase 1G-02 implementation is limited to:

1. **Tool Policy Read-Only API** — Two GET routes serving policy status and catalog data
2. **Tool Catalog Read-Only API** — Filtered, sorted, paginated tool inventory listing
3. **Tool Policy Read-Only Frontend Panel** — Workspace tab with Policy Overview and Catalog sub-tabs
4. **OpenAPI Documentation** — Update from 27 to 29 paths
5. **dev-check and Route Boundary Updates** — Verify 29 paths, verify no write routes
6. **Backend, Frontend, and Browser Smoke Tests** — Full test coverage
7. **Zero Side-Effect Validation** — Before/after dev-home hash verification

---

## 6. Non-Goals

The following are explicitly excluded from Phase 1G-02:

- Schema Preview / Validation API
- Tool Call Dry-Run
- Tool Execute
- Provider Tool Schema
- Tool Dispatch
- Tool Audit
- Tool Runtime Registry
- Tool Worker
- Tool Cancel
- Agent Tool Loop Integration
- Static Allowlist Enablement
- Candidate Promotion
- Policy Mutation (enable/disable tools)
- Denylist Mutation
- Catalog Detail Route (use Catalog List DTO locally)
- Any POST/PATCH/PUT/DELETE tool route

---

## 7. Architecture

### 7.1 Layer Boundary

```
Static Policy Module (dev_web_tool_policy.py)
  ↓ immutable data, pure functions
Read-Only Query Service (dev_web_tool_policy_service.py)
  ↓ DTO adaptation, filtering, sorting, pagination, redaction
FastAPI Routes (dev_web_api.py registration)
  ↓ parameter parsing, service call, error mapping, envelope
Frontend Panel (ToolPolicyPanel.vue)
  ↓ read-only display only
```

### 7.2 Single Source of Truth

`hermes_cli/dev_web_tool_policy.py` remains the sole source of truth for:

- Tool inventory
- Risk classifications
- Denylist membership
- Candidate membership
- Allowlist membership
- Policy decisions
- Limits and constraints

The API service must not re-define inventory data. The frontend must not duplicate policy rules.
The OpenAPI spec must not hardcode different counts.

---

## 8. Routes

### 8.1 Allowed Routes

| Method | Route | Purpose |
|--------|-------|---------|
| GET | `/api/dev/v1/tools/policy` | Policy status overview |
| GET | `/api/dev/v1/tools/catalog` | Filtered, paginated tool catalog |

### 8.2 Route Count Strategy

| Stage | OpenAPI Paths |
|-------|---------------|
| Before Phase 1G-02 | 27 |
| After Phase 1G-02 | 29 |
| Delta | +2 |

### 8.3 Forbidden Routes

The following routes must NOT exist in Phase 1G-02:

```
POST   /api/dev/v1/tools/policy
PATCH  /api/dev/v1/tools/policy
PUT    /api/dev/v1/tools/policy
DELETE /api/dev/v1/tools/policy

POST   /api/dev/v1/tools/catalog
PATCH  /api/dev/v1/tools/catalog
DELETE /api/dev/v1/tools/catalog
GET    /api/dev/v1/tools/catalog/{toolName}

POST   /api/dev/v1/tools/schema/preview
POST   /api/dev/v1/tools/calls/dry-run
POST   /api/dev/v1/tools/calls
GET    /api/dev/v1/tools/calls/{callId}
POST   /api/dev/v1/tools/calls/{callId}/cancel

PATCH  /api/dev/v1/tools/policy
POST   /api/dev/v1/tools/allowlist
DELETE /api/dev/v1/tools/denylist
```

Any write-like Tool Route must not exist, not merely return disabled.

### 8.4 Catalog Detail Rationale

Catalog Detail is not a separate route because:

- Inventory is only 71 items
- DTO item size is bounded (~200–500 bytes each)
- Full catalog at `pageSize=100` fits in one response
- Frontend can select detail from cached list items
- Reduces API surface area
- Maintains complete read-only guarantee

---

## 9. Policy Status Contract

### 9.1 Response Structure

```
GET /api/dev/v1/tools/policy → 200

{
  "data": {
    "mode": "DEFAULT_DENY",
    "inventoryCount": 71,
    "riskCounts": {
      "R0": 1,
      "R1": 5,
      "R2": 19,
      "R3": 26,
      "R4": 17,
      "R5": 3
    },
    "permanentDenylistCount": 26,
    "candidateAllowlistCount": 6,
    "enabledAllowlistCount": 0,
    "execution": {
      "implemented": false,
      "enabled": false,
      "providerSchemaSent": false,
      "dispatchAvailable": false,
      "auditAvailable": false
    },
    "limits": {
      "maxArgumentPayloadBytes": 32768,
      "maxArgumentNestingDepth": 8,
      "maxArgumentStringLength": 4000,
      "maxArgumentArrayLength": 100,
      "defaultR0TimeoutSeconds": 2,
      "defaultR1TimeoutSeconds": 5,
      "maxToolTimeoutSeconds": 30,
      "maxToolCallsPerRun": 3,
      "maxGlobalConcurrency": 1,
      "maxConcurrencyPerRun": 1,
      "maxSerializedOutputBytes": 65536,
      "maxAgentVisibleOutputBytes": 16384,
      "maxWebPreviewOutputBytes": 8192
    },
    "safety": {
      "readOnly": true,
      "sideEffects": false,
      "writeEnabled": false,
      "executeAvailable": false,
      "policyMutationAvailable": false
    }
  },
  "meta": {
    "requestId": "<uuid>",
    "timestamp": "<ISO 8601>"
  }
}
```

### 9.2 Field Names

Field naming follows the existing Dev API camelCase convention established in `dev_web_schemas.py`.

### 9.3 Execution Flags

All execution flags must be `false` / `false` / `false` / `false` / `false`.

### 9.4 Safety Flags

All safety flags must be `true` / `false` / `false` / `false` / `false`.

### 9.5 Counts

- `inventoryCount` = 71 (exact)
- `permanentDenylistCount` = 26 (exact)
- `candidateAllowlistCount` = 6 (exact)
- `enabledAllowlistCount` = 0 (exact)

### 9.6 Forbidden Output

The response must NOT contain:

- Internal `MappingProxyType` or Python Enum repr
- Local absolute paths (`/Users/...`, `/home/...`)
- Registry handler references
- Handler callable objects
- Provider configuration
- API keys, tokens, or secrets
- Base URLs
- Environment variable values
- Complete tool schemas
- Complete tool source code
- Tracebacks
- Module import paths beyond safe relative identifiers

---

## 10. Catalog Contract

### 10.1 Query Parameters

| Parameter | Type | Required | Default | Constraints |
|-----------|------|----------|---------|-------------|
| `q` | string | No | `null` | Max 120 chars, case-insensitive, matches `canonicalName` and `rationalePreview` |
| `risk` | string enum | No | `null` | One of: `R0`, `R1`, `R2`, `R3`, `R4`, `R5` |
| `capability` | string enum | No | `null` | Must match `ToolCapability` enum values |
| `policyStatus` | string enum | No | `null` | One of: `PERMANENTLY_DENIED`, `CANDIDATE`, `UNLISTED`, `STATICALLY_ALLOWED` |
| `page` | integer | No | `1` | `>= 1` |
| `pageSize` | integer | No | `25` | `1` to `100` |
| `sort` | string enum | No | `nameAsc` | One of: `nameAsc`, `nameDesc`, `riskAsc`, `riskDesc` |

### 10.2 Query Parameter Rules

**`q` (search):**
- Maximum 120 characters
- Case-insensitive matching
- Matches `canonicalName` and safe `rationalePreview` only
- No regex support
- No glob support
- No arbitrary expression evaluation

**`risk`:**
- Must be exact enum value: `R0`, `R1`, `R2`, `R3`, `R4`, `R5`
- Invalid value → 400 `INVALID_TOOL_RISK`

**`capability`:**
- Must match `ToolCapability` enum values exactly
- No arbitrary capability strings
- Invalid value → 400 `INVALID_TOOL_CAPABILITY`

**`policyStatus`:**
- Allowed values: `PERMANENTLY_DENIED`, `CANDIDATE`, `UNLISTED`, `STATICALLY_ALLOWED`
- Priority order (for classification): `PERMANENTLY_DENIED` > `STATICALLY_ALLOWED` > `CANDIDATE` > `UNLISTED`
- Currently `STATICALLY_ALLOWED` results must be 0
- Invalid value → 400 `INVALID_TOOL_POLICY_STATUS`

**`page` / `pageSize`:**
- `page >= 1`, `pageSize` default 25, min 1, max 100
- Page beyond `totalPages` → 200 with empty items (not an error)

**`sort`:**
- Allowed: `nameAsc`, `nameDesc`, `riskAsc`, `riskDesc`
- No arbitrary field name sorting
- Invalid value → 400 `INVALID_TOOL_SORT`

**Unknown dangerous parameters:**
- Parameters named `execute`, `force`, `enable`, `write`, `dispatch`, `override` → 400 `INVALID_TOOL_POLICY_QUERY`
- Prevents client-side safety flag override attempts

### 10.3 Catalog Item DTO

Each catalog item must contain ONLY these fields:

| Field | Type | Description |
|-------|------|-------------|
| `canonicalName` | string | Unique tool identifier |
| `primaryRisk` | string | Risk level label (e.g. "Pure Computation") |
| `riskRank` | string | Risk rank code (R0–R5) |
| `capabilities` | string[] | Capability flags |
| `permanentlyDenied` | boolean | On permanent denylist |
| `candidateAllowlisted` | boolean | On candidate allowlist |
| `staticallyAllowed` | boolean | On static allowlist |
| `allowed` | boolean | Currently allowed (always `false`) |
| `policyStatus` | string | Derived policy status |
| `reasonCode` | string | Machine-readable reason |
| `sourceModule` | string | Safe relative module identifier |
| `rationalePreview` | string | Truncated rationale (max 200 chars) |
| `executionAvailable` | boolean | Tool execution available (always `false`) |
| `schemaPreviewAvailable` | boolean | Schema preview available (always `false`) |
| `dryRunAvailable` | boolean | Dry-run available (always `false`) |

### 10.4 `sourceModule` Constraints

Must be safe relative module identifiers only, e.g.:
- `tools.file_tools`
- `tools.web_tools`
- `plugins.spotify`

Must NOT return:
- Absolute paths (`/Users/...`, `/home/...`, `file://...`)
- Handler objects or function addresses
- Complete source code
- Complete tool schemas
- Provider schemas
- Internal comments
- Environment variables
- Secrets

### 10.5 `rationalePreview` Constraints

- Maximum 200 characters
- Apply path redaction: `/Users/...` → `[local-path]`, `/home/...` → `[local-path]`, `file://...` → `[file-uri-redacted]`
- Apply secret redaction
- No newlines or stack traces

### 10.6 Current Frozen Values

All items must have:

```
allowed = false
executionAvailable = false
schemaPreviewAvailable = false
dryRunAvailable = false
staticallyAllowed = false
```

### 10.7 Catalog Response Structure

```
GET /api/dev/v1/tools/catalog → 200

{
  "data": {
    "items": [CatalogItem, ...],
    "page": 1,
    "pageSize": 25,
    "total": 71,
    "totalPages": 3,
    "filters": {
      "q": null,
      "risk": null,
      "capability": null,
      "policyStatus": null,
      "sort": "nameAsc"
    },
    "summary": {
      "inventoryCount": 71,
      "permanentDenylistCount": 26,
      "candidateAllowlistCount": 6,
      "enabledAllowlistCount": 0
    },
    "safety": {
      "readOnly": true,
      "sideEffects": false,
      "executeAvailable": false
    }
  },
  "meta": {
    "requestId": "<uuid>",
    "timestamp": "<ISO 8601>"
  }
}
```

### 10.8 Empty Result Behavior

- Empty search results → 200 with `items: []`
- Non-existent filter combination → 200 with `items: []`
- Page beyond totalPages → 200 with `items: []`
- Never return error for empty results

---

## 11. Query Model

### 11.1 Enumeration Sources

| Parameter | Source Enum | Location |
|-----------|-------------|----------|
| `risk` | `ToolRiskLevel` | `dev_web_tool_policy.py` |
| `capability` | `ToolCapability` | `dev_web_tool_policy.py` |
| `policyStatus` | Derived (computed from denylist/candidate/allowlist) | Service layer |
| `sort` | API-level enum | Service or route layer |

### 11.2 Policy Status Derivation

```
if permanentlyDenied:  "PERMANENTLY_DENIED"
elif staticallyAllowed: "STATICALLY_ALLOWED"
elif candidateAllowlisted: "CANDIDATE"
else: "UNLISTED"
```

Currently:
- `STATICALLY_ALLOWED` count = 0
- `PERMANENTLY_DENIED` count = 26
- `CANDIDATE` count = 6
- `UNLISTED` count = 39

---

## 12. DTO Whitelist

### 12.1 Policy Status DTO Fields

- `mode`
- `inventoryCount`
- `riskCounts` (object with R0–R5)
- `permanentDenylistCount`
- `candidateAllowlistCount`
- `enabledAllowlistCount`
- `execution` (object with 5 booleans)
- `limits` (object with 13 numeric values)
- `safety` (object with 5 booleans)

### 12.2 Catalog Item DTO Fields

- `canonicalName`
- `primaryRisk`
- `riskRank`
- `capabilities`
- `permanentlyDenied`
- `candidateAllowlisted`
- `staticallyAllowed`
- `allowed`
- `policyStatus`
- `reasonCode`
- `sourceModule`
- `rationalePreview`
- `executionAvailable`
- `schemaPreviewAvailable`
- `dryRunAvailable`

### 12.3 Catalog Response DTO Fields

- `items` (array of Catalog Item)
- `page`, `pageSize`, `total`, `totalPages`
- `filters` (active query parameters)
- `summary` (inventory counts)
- `safety` (read-only flags)

---

## 13. Forbidden Fields

Any Tool Policy API response must NOT contain:

```
handler
callable
function
modulePath
sourcePath
absolutePath
registryObject
toolRegistry
toolSchema
providerSchema
apiKey / api_key
baseUrl / base_url
authorization
headers
cookies
proxy
environment / env
secrets
token
password
credentials
fullSource
fullRationale
traceback
stack
thread
process
dispatch
execute (as verb/action)
force
override
```

`executionAvailable` as a boolean safety status indicator is allowed.

The API must not return any URL that could trigger tool execution.

---

## 14. Error Model

### 14.1 Error Codes

| Code | HTTP | Meaning |
|------|------|---------|
| `TOOL_POLICY_UNAVAILABLE` | 503 | Static policy module failed to load |
| `INVALID_TOOL_POLICY_QUERY` | 400 | Invalid search query (too long, dangerous params) |
| `INVALID_TOOL_RISK` | 400 | Risk parameter not in R0–R5 |
| `INVALID_TOOL_CAPABILITY` | 400 | Capability parameter not in ToolCapability enum |
| `INVALID_TOOL_POLICY_STATUS` | 400 | Policy status parameter not in allowed values |
| `INVALID_TOOL_SORT` | 400 | Sort parameter not in allowed values |
| `TOOL_POLICY_DATA_INVALID` | 500 | Policy data failed internal integrity check |
| `INTERNAL_ERROR` | 500 | Unexpected server error |

### 14.2 HTTP Mapping

```
400: INVALID_TOOL_POLICY_QUERY, INVALID_TOOL_RISK,
     INVALID_TOOL_CAPABILITY, INVALID_TOOL_POLICY_STATUS,
     INVALID_TOOL_SORT

500: TOOL_POLICY_DATA_INVALID, INTERNAL_ERROR

503: TOOL_POLICY_UNAVAILABLE
```

### 14.3 Error Envelope

All errors must use the existing Dev API Error Envelope (`ErrorResponse` from `dev_web_schemas.py`):

```json
{
  "error": {
    "code": "INVALID_TOOL_RISK",
    "message": "Risk must be one of: R0, R1, R2, R3, R4, R5",
    "details": null
  },
  "meta": {
    "requestId": "<uuid>",
    "timestamp": "<ISO 8601>"
  }
}
```

### 14.4 Error Redaction

Error responses must NOT contain:

- Tracebacks
- Absolute paths
- Internal object repr
- Complete schemas
- Secrets
- Stack traces
- Thread/process information

---

## 15. Safety Flags

### 15.1 Required Safety Flags

All successful responses must include or allow deriving:

| Flag | Value | Override |
|------|-------|----------|
| `readOnly` | `true` | Cannot be overridden by client |
| `sideEffects` | `false` | Cannot be overridden by client |
| `writeEnabled` | `false` | Cannot be overridden by client |
| `executeAvailable` | `false` | Cannot be overridden by client |
| `providerSchemaSent` | `false` | Cannot be overridden by client |
| `dispatchAvailable` | `false` | Cannot be overridden by client |
| `auditAvailable` | `false` | Cannot be overridden by client |

### 15.2 Override Prevention

Even if a request carries parameters like `execute=true`, `force=true`, `enable=true`,
`write=true`, or `dispatch=true`, safety flags must not change.

Recommended strategy: **explicitly reject dangerous unknown parameters** with
400 `INVALID_TOOL_POLICY_QUERY`.

---

## 16. Frontend Information Architecture

### 16.1 Workspace Tab Placement

**Tools** is a new first-level Workspace tab.

Updated Workspace tabs:

| Tab | Icon Source | Status |
|-----|-------------|--------|
| Files | FolderTree | Existing |
| Memory | Brain | Existing |
| Context | Layers | Existing |
| Reviews | ClipboardCheck | Existing |
| Agent | Activity | Existing |
| **Tools** | **Wrench / Shield** | **New** |

### 16.2 Tab Placement Rationale

- Tool Policy is an independent governance domain
- Future expansion: Catalog, Schema Preview, Dry-Run, Execution Monitor
- Should not be embedded in Agent status panel
- Avoids AgentPanel over-complexity
- Consistent with Memory and Reviews governance panels

### 16.3 Tools Panel Sub-Tabs

| Sub-Tab | Content |
|---------|---------|
| Policy Overview | Mode, counts, risk distribution, execution status, limits, safety flags |
| Catalog | Searchable, filterable, sortable, paginated tool list with detail view |

### 16.4 Future Sub-Tabs (Not in Phase 1G-02)

The following sub-tabs must NOT appear in Phase 1G-02:

- Schema Preview
- Call Dry-Run
- Execute
- Audit Log
- Runtime Calls

These may appear as "Future capability / Not available" or not appear at all.

---

## 17. Policy Overview UI

### 17.1 Required Elements

- **Mode Badge**: "DEFAULT DENY" with prominent styling
- **Inventory Count**: 71 tools
- **Risk Distribution**: Visual breakdown (R0: 1, R1: 5, R2: 19, R3: 26, R4: 17, R5: 3)
- **Denylist Count**: 26 permanently denied
- **Candidate Count**: 6 candidates (not enabled)
- **Enabled Count**: 0 enabled
- **Execution Status**: Disabled / Not Implemented
- **Provider Schema**: Not Sent
- **Dispatch**: Unavailable
- **Audit**: Unavailable
- **Limits Table**: All 13 limit values displayed
- **Safety Flags**: All 7 safety flags displayed

### 17.2 Required Safety Banner

A prominent, always-visible safety notice:

```
🔒 Read-only policy view
   No tools are enabled
   No tool calls can be executed
   No provider schemas are sent
```

### 17.3 Forbidden Controls

The Policy Overview must NOT contain:

- Enable / Disable buttons
- Approve / Reject buttons
- Promote / Demote buttons
- "Add to Allowlist" controls
- "Remove from Denylist" controls
- Execute / Test / Try buttons
- "Send Schema" controls
- Any form that modifies policy state

---

## 18. Catalog UI

### 18.1 Required Elements

**Toolbar:**
- Search input (binds to `q` parameter)
- Risk filter dropdown (R0–R5 + "All")
- Capability filter dropdown (ToolCapability enum + "All")
- Policy Status filter dropdown (4 values + "All")
- Sort dropdown (4 options)

**Tool List:**
- Each item shows: `canonicalName`, risk badge, policy status badge, capabilities, `allowed=false`
- Click/keyboard to select item for detail view
- Pagination controls (prev/next, page indicator)

**Detail View:**
- Canonical Name
- Primary Risk (label + rank code)
- Capabilities (list of tags)
- Policy Status (permanently denied / candidate / unlisted / statically allowed)
- Reason Code
- Source Module (safe identifier only)
- Rationale Preview (truncated, redacted)
- Safety Flags (all unavailable)

### 18.2 Required Unavailable Indicators

Detail view must display:

```
Execution: unavailable
Schema Preview: unavailable
Dry-Run: unavailable
```

### 18.3 Forbidden Controls

The Catalog must NOT contain:

- Enable / Execute / Test / Try buttons
- Schema Preview buttons
- Dry-Run buttons
- Allowlist mutation controls
- Denylist mutation controls
- Any form that modifies tool state

---

## 19. Frontend State

### 19.1 Proposed Files

| File | Purpose |
|------|---------|
| `types/api/toolPolicy.ts` | TypeScript interfaces for API types |
| `api/tools.ts` | API client functions |
| `stores/toolPolicy.ts` | Pinia store for policy and catalog state |
| `components/workspace/ToolPolicyPanel.vue` | Main panel component |

### 19.2 Store State

```typescript
interface ToolPolicyState {
  // Policy Overview
  policyState: LoadingState
  policy: PolicyStatusData | null

  // Catalog
  catalogState: LoadingState
  items: CatalogItem[]
  selectedTool: CatalogItem | null
  filters: CatalogFilters
  pagination: PaginationState

  // Shared
  error: string
  abortController: AbortController | null
}
```

### 19.3 Loading State Machine

```
idle → loading → success
                 ↓
                error → loading (retry)
                 ↓
               empty
```

### 19.4 Request Cancellation

- Store must hold `AbortController` reference
- New filter/search request cancels previous in-flight request
- Stale responses are discarded (check request identity before committing state)
- Component unmount cancels in-flight requests

### 19.5 Persistence Prohibition

Tool Policy state must NOT be persisted to:

- `localStorage`
- `IndexedDB`
- `SessionDB`
- Any persistent storage

Policy data is always fetched fresh from the API (static, immutable, fast).

---

## 20. Accessibility

### 20.1 Required ARIA Attributes

| Element | ARIA |
|---------|------|
| Workspace Tools Tab | `aria-controls="workspace-tools-panel"` |
| Sub-tab list | `role="tablist"` |
| Sub-tab button | `role="tab"`, `aria-selected`, `aria-controls` |
| Sub-tab panel | `role="tabpanel"`, `aria-labelledby` |
| Filter inputs | `label` or `aria-label` |
| Loading state | `aria-busy="true"` |
| Error state | `role="alert"` |
| Result changes | `aria-live="polite"` on list container |
| Tool list items | Keyboard navigable (arrow keys, Enter, Space) |
| Selected tool detail | Clear focus ring |

### 20.2 Keyboard Navigation

- Arrow keys navigate tool list items
- Enter/Space selects item for detail view
- Tab moves between filter controls
- Escape clears selection

### 20.3 Non-Color Requirements

- Risk level and Policy Status must not be communicated by color alone
- Must use text labels, icons, or patterns in addition to color
- High contrast for all text on all themes

### 20.4 Motion

- Must respect `prefers-reduced-motion`
- No essential animations for information transfer

---

## 21. Theme and Responsive

### 21.1 Theme Compatibility

Must render correctly on all 5 built-in themes:

| Theme | Category | Scheme |
|-------|----------|--------|
| Obsidian | Modern | Dark |
| Paper | Modern | Light |
| 宋韵 Song | Eastern | Dark |
| 墨境 Ink | Eastern | Light |
| 夜樱 Sakura Night | Eastern | Dark |

No per-theme business logic branches. Use semantic CSS variables only.

### 21.2 Target Viewports

| Viewport | Category |
|----------|----------|
| 1440×900 | Desktop |
| 1280×800 | Desktop |
| 1024×768 | Tablet landscape |
| 768×900 | Tablet portrait |

### 21.3 Responsive Behavior

- Catalog List and Detail may stack vertically on narrow viewports
- No horizontal overflow at any supported viewport
- Filter controls may wrap or collapse
- All content must remain readable and functional

---

## 22. OpenAPI Strategy

### 22.1 Path Count Roadmap

| Stage | Paths | Delta |
|-------|-------|-------|
| Phase 1F Release | 27 | — |
| After Phase 1G-02 | 29 | +2 |

### 22.2 New Paths

| Method | Path | Summary |
|--------|------|---------|
| GET | `/api/dev/v1/tools/policy` | Read-only tool policy status overview |
| GET | `/api/dev/v1/tools/catalog` | Filtered, paginated tool catalog |

### 22.3 OpenAPI Safety Markers

Both new paths must document:

- `readOnly: true`
- `sideEffects: false`
- `executeAvailable: false`

### 22.4 No New Write Operations

Phase 1G-02 must not add any POST, PATCH, PUT, or DELETE tool routes.

---

## 23. dev-check Strategy

### 23.1 Post-Phase 1G-02 dev-check Rules

After Phase 1G-02 implementation, dev-check must verify:

**Path Count:**
- OpenAPI paths = 29

**Required Routes:**
- `GET /tools/policy` present
- `GET /tools/catalog` present

**Forbidden Routes:**
- `POST /tools/policy` absent
- `PATCH /tools/policy` absent
- `PUT /tools/policy` absent
- `DELETE /tools/policy` absent
- `POST /tools/catalog` absent
- `PATCH /tools/catalog` absent
- `DELETE /tools/catalog` absent
- `GET /tools/catalog/{toolName}` absent
- `POST /tools/schema/preview` absent
- `POST /tools/calls/dry-run` absent
- `POST /tools/calls` absent
- `GET /tools/calls/{callId}` absent
- `POST /tools/calls/{callId}/cancel` absent

**Static Policy State:**
- `STATIC_ALLOWLIST` empty
- Tool Execution disabled
- Provider Tool Schema not sent

---

## 24. Route Boundary

### 24.1 Legal Tool Routes

```
GET /api/dev/v1/tools/policy
GET /api/dev/v1/tools/catalog
```

### 24.2 Illegal Tool Routes (Must Not Exist)

```
POST   /api/dev/v1/tools/policy
PATCH  /api/dev/v1/tools/policy
PUT    /api/dev/v1/tools/policy
DELETE /api/dev/v1/tools/policy

POST   /api/dev/v1/tools/catalog
PATCH  /api/dev/v1/tools/catalog
DELETE /api/dev/v1/tools/catalog
GET    /api/dev/v1/tools/catalog/{toolName}

POST   /api/dev/v1/tools/schema/preview
POST   /api/dev/v1/tools/calls/dry-run
POST   /api/dev/v1/tools/calls
GET    /api/dev/v1/tools/calls/{callId}
POST   /api/dev/v1/tools/calls/{callId}/cancel
```

Any write-like Tool Route must not exist (404), not merely return disabled.

---

## 25. Backend Tests

### 25.1 Policy Status Tests

| Test Case | Assertion |
|-----------|-----------|
| GET /tools/policy returns 200 | Status code |
| Inventory count = 71 | Exact count |
| Risk counts match | R0=1, R1=5, R2=19, R3=26, R4=17, R5=3 |
| Denylist count = 26 | Exact count |
| Candidate count = 6 | Exact count |
| Enabled count = 0 | Exact count |
| All execution flags false | 5 booleans |
| All safety flags correct | 5 booleans |
| DTO whitelist enforced | No forbidden fields |
| No sensitive fields | No paths, secrets, handlers |
| Limits match static module | All 13 values |

### 25.2 Catalog Tests

| Test Case | Assertion |
|-----------|-----------|
| Default list returns 71 total | Exact total |
| Pagination correct | Page size, total pages, items |
| Search by canonical name | Matching items returned |
| Search by rationale | Matching items returned |
| Risk filter | Only matching risk level |
| Capability filter | Only matching capabilities |
| Policy status filter | Correct classification |
| Sort nameAsc | Alphabetical order |
| Sort nameDesc | Reverse alphabetical |
| Sort riskAsc | R0 before R5 |
| Sort riskDesc | R5 before R0 |
| Empty result returns 200 | Not 404 |
| Invalid risk returns 400 | Error envelope |
| Invalid capability returns 400 | Error envelope |
| Invalid status returns 400 | Error envelope |
| Invalid sort returns 400 | Error envelope |
| Page size max enforced | Max 100 items |
| Dangerous param rejected | `execute=true` → 400 |
| Combined filters | Multiple filters interact correctly |

### 25.3 Safety Tests

| Test Case | Assertion |
|-----------|-----------|
| No Registry import | Import check |
| No Handler import | Import check |
| No Provider initialization | Runtime check |
| No SessionDB access | Runtime check |
| No filesystem access | Runtime check |
| No network access | Runtime check |
| No Tool Dispatch | Runtime check |
| No Tool Audit | Runtime check |
| No state mutation | Before/after comparison |

### 25.4 DTO Tests

| Test Case | Assertion |
|-----------|-----------|
| No handler field | Key absent |
| No callable field | Key absent |
| No full schema | Key absent |
| No absolute path | Redaction check |
| No secret | Redaction check |
| No traceback | Key absent |
| No internal repr | Value format check |

### 25.5 Route Boundary Tests

| Test Case | Assertion |
|-----------|-----------|
| GET /tools/policy exists | 200 |
| GET /tools/catalog exists | 200 |
| All Tool POST routes absent | 404 |
| All Tool PATCH routes absent | 404 |
| All Tool PUT routes absent | 404 |
| All Tool DELETE routes absent | 404 |
| OpenAPI 29 paths | Exact count |

---

## 26. Frontend Tests

### 26.1 Tab Structure

- Tools top-level Workspace tab exists
- Policy Overview sub-tab exists
- Catalog sub-tab exists
- Tab switching works correctly

### 26.2 Policy Overview

- Policy counts render correctly (71, 26, 6, 0)
- Risk distribution renders
- "No tools enabled" warning visible
- Execution status shows all disabled
- Limits render correctly
- Safety flags render correctly

### 26.3 Catalog

- Catalog list renders with items
- Search input updates API request
- Risk filter works
- Capability filter works
- Policy status filter works
- Sort changes applied
- Pagination works
- Selected tool detail renders
- All unavailable indicators shown

### 26.4 State Management

- Loading state displays spinner
- Error state displays message with retry
- Empty result displays empty message
- Retry triggers new request
- Abort stale request on filter change
- Stale response discarded

### 26.5 Forbidden Controls

- No Enable button
- No Execute button
- No Dry-Run button
- No Schema Preview button
- No Allowlist mutation control
- No Denylist mutation control

### 26.6 Accessibility

- ARIA roles correct (tablist, tab, tabpanel)
- Keyboard navigation works
- aria-live on result changes
- Labels on all filters

---

## 27. Browser Smoke

### 27.1 Smoke Test Coverage

After Phase 1G-02, browser smoke must verify:

- Tools Workspace Tab visible
- Policy Overview loads
- Inventory = 71
- Denylist = 26
- Candidate = 6
- Enabled = 0
- Catalog loads
- Search returns results
- Risk filter applies
- Tool detail selection works
- All execution capabilities show unavailable
- No execution buttons present

### 27.2 Theme × Viewport Matrix

5 themes × 4 viewports = 20 combinations

Can integrate into existing 24-item smoke matrix or add drill-down tests.

### 27.3 Console Verification

- `console.errors` = 0
- CORS errors = 0
- Asset 404s = 0
- Horizontal overflow = 0

### 27.4 Prohibited Smoke Actions

Browser smoke must NOT:

- Call Provider
- Send Tool Schema
- Call Tool Dispatch
- Create Tool Audit
- Modify `state.db`
- Write to filesystem
- Access external network

---

## 28. Side-Effect Validation

### 28.1 Before/After Hash Comparison

Before and after running all Phase 1G-02 tests, verify:

| Artifact | Check |
|----------|-------|
| `state.db` SHA-256 | Unchanged |
| `state.db` size | Unchanged |
| `state.db` mtime | Unchanged |
| SQLite schema | Unchanged |
| `tool_execution_audit` table | Still absent |
| Session count | Unchanged |
| Message count | Unchanged |
| `MEMORY.md` SHA-256 | Unchanged |
| Memory indexes | Unchanged |
| Memory records | Unchanged |
| Memory events line count | Unchanged |
| Snapshots | Unchanged |
| Review items | Unchanged |
| Review events line count | Unchanged |

### 28.2 No New Artifacts

Verify no new files or directories were created:

- No new files in dev-home
- No lock files
- No tool cache
- No tool logs
- No provider network traffic
- No registry dispatch

### 28.3 Test Isolation

Unit tests may use the static policy module directly from memory.
No `tmp_path` or temporary filesystem required for pure policy tests.

Integration tests using the real dev-home for read-only GET verification
must still verify no write side effects.

---

## 29. Performance

### 29.1 No Caching Required

- Inventory is only 71 items
- All data is static, immutable, in-memory
- No database queries
- No filesystem reads
- No network calls

### 29.2 Strategy

- Each request generates DTOs from static read-only Mapping
- No global mutable cache
- No background threads
- No database
- No file cache

### 29.3 Performance Targets (Dev Environment)

| Endpoint | p95 Target |
|----------|------------|
| `GET /tools/policy` | < 50ms |
| `GET /tools/catalog` | < 100ms |

These are development environment targets, not production SLAs.

---

## 30. Security Risks

### 30.1 P0 (Acceptable: none if all gates pass)

None — documentation-only phase produces no runtime code.

### 30.2 P1 (Must track)

1. API DTO must prevent `handler`/`schema`/`path` leakage at serialization time
2. Catalog query must strictly limit enum values (no arbitrary strings)
3. Static Policy counts and OpenAPI counts may drift — must stay synchronized
4. Frontend must not display Candidate tools as Enabled
5. Future Schema Preview must not auto-send Provider Schema
6. Future Dry-Run must not Dispatch
7. Real Tool Schemas not yet fully `additionalProperties: false`
8. `read_file` Root Allowlist not yet implemented
9. Symlink escape prevention not yet implemented
10. Tool Result Redaction not yet implemented

### 30.3 P2 (Advisory)

1. Catalog query over 71 items needs no caching now; re-evaluate if inventory grows
2. Future tool count increase may affect pagination performance
3. Capability tag readability may need UX iteration
4. Risk explanation text length may need tuning
5. Provider Schema format differences may affect future phases
6. Audit retention policy undefined for future Tool Audit feature

---

## 31. Future Phase Boundary

### 31.1 Phase 1G-03: Tool Schema Preview / Validation API

- May add: `POST /api/dev/v1/tools/schema/preview`
- Still does not send Provider Schema
- Validates schema structure against safety rules
- OpenAPI paths: 29 → 30

### 31.2 Phase 1G-04: Tool Call Dry-Run Policy Evaluation

- May add: `POST /api/dev/v1/tools/calls/dry-run`
- Evaluates policy without dispatching
- Returns decision + reason without execution
- OpenAPI paths: 30 → 31

### 31.3 Phase 1G-05+: Advanced Capabilities

Future phases may consider:

- Tool Audit (`tool_execution_audit` table)
- Runtime Call Registry
- Dev-only Execute (with kill switch)
- Provider Schema Integration
- Agent Tool Loop Integration

Phase 1G-02 must not preempt any of these capabilities.

---

## 32. Implementation Commit Plan

### 32.1 Commit 1: Backend

```
feat(webui): add tool policy read-only api
```

Contains:

- `hermes_cli/dev_web_tool_policy_service.py` (Read-only Query Service)
- `hermes_cli/dev_web_schemas.py` (DTO model additions)
- `hermes_cli/dev_web_api.py` (2 GET routes)
- `docs/webui/openapi/dev-web-api-v1.yaml` (27 → 29 paths)
- `tests/test_dev_web_tool_policy_api.py` (backend tests)
- `tests/test_dev_check_webui.py` (route boundary update)
- `tests/test_dev_web_0c06_closure.py` (forbidden route update)

### 32.2 Commit 2: Frontend

```
feat(webui): add tool policy read-only panel
```

Contains:

- `apps/hermes-dev-webui/src/types/api/toolPolicy.ts` (TypeScript types)
- `apps/hermes-dev-webui/src/api/tools.ts` (API client)
- `apps/hermes-dev-webui/src/stores/toolPolicy.ts` (Pinia store)
- `apps/hermes-dev-webui/src/components/workspace/ToolPolicyPanel.vue` (Panel)
- `apps/hermes-dev-webui/src/components/layout/WorkspacePanel.vue` (tab addition)
- Frontend tests
- Smoke test updates

### 32.3 Commit 3: Docs

```
docs(webui): complete phase 1g-02 tool policy panel
```

Contains:

- Phase 1G-02 implementation closure document
- Updated implementation plan

### 32.4 Commit Order Constraint

Commits must be in order: Backend → Frontend → Docs.
Each commit must pass all quality gates independently.

---

## 33. Acceptance Criteria

Phase 1G-02 implementation must satisfy all of the following:

### 33.1 API (10 items)

1. 2 GET routes exist (`/tools/policy`, `/tools/catalog`)
2. OpenAPI = 29 paths
3. No Tool write routes (POST/PATCH/PUT/DELETE all 404)
4. Policy Inventory = 71
5. Risk counts exact (R0=1, R1=5, R2=19, R3=26, R4=17, R5=3)
6. Denylist = 26
7. Candidate = 6
8. Enabled = 0
9. All `allowed = false`
10. All `executionAvailable = false`

### 33.2 Security (12 items)

11. DTO whitelist enforced (no forbidden fields)
12. No path leakage
13. No secret leakage
14. No Registry initialization
15. No Handler initialization
16. No Provider initialization
17. No Tool Dispatch
18. No Tool Audit
19. No Session writes
20. No Memory writes
21. No Review writes
22. Static Policy unchanged

### 33.3 Frontend (14 items)

23. Workspace Tools Tab exists
24. Policy Overview sub-tab renders
25. Catalog sub-tab renders
26. Search works
27. Risk filter works
28. Capability filter works
29. Policy Status filter works
30. Sort works
31. Pagination works
32. Tool detail renders
33. No Enable/Execute/Dry-Run/Schema Preview buttons
34. Loading/Error/Empty/Retry states work
35. Stale request abort works
36. Accessibility (ARIA roles, keyboard nav)

### 33.4 Theme & Responsive (2 items)

37. All 5 themes render correctly
38. All 4 viewports render correctly (no overflow)

### 33.5 Quality Gates (7 items)

39. Backend tests PASS
40. Frontend tests PASS
41. Browser Smoke PASS
42. `compileall` PASS
43. Ruff PASS
44. `memory-check` PASS
45. `dev-check` PASS

### 33.6 Side-Effect Validation (5 items)

46. `state.db` unchanged (hash, size, mtime)
47. Sessions/Messages unchanged
48. Memory unchanged (MEMORY.md, indexes, records, events)
49. Reviews unchanged
50. Production Gateway unaffected

### 33.7 Final State (1 item)

51. Working tree clean (tracked)

---

## 34. Risks and Open Questions

### 34.1 Open Questions

1. Should Catalog search also match `sourceModule`, or only `canonicalName` and `rationalePreview`?
   → Recommendation: Only `canonicalName` and `rationalePreview` for Phase 1G-02.

2. Should dangerous unknown query parameters be silently ignored or explicitly rejected?
   → Recommendation: Explicitly reject with 400 `INVALID_TOOL_POLICY_QUERY`.

3. Should the frontend pre-fetch both policy and catalog on tab activation, or lazy-load?
   → Recommendation: Lazy-load on sub-tab activation.

4. Should the Catalog response include a `riskDistribution` summary alongside `summary`?
   → Recommendation: No — Policy Overview already provides this. Catalog summary is limited to counts.

### 34.2 Mitigated Risks

- **Registry initialization**: Static module has zero Registry dependency (verified by audit)
- **Path leakage**: DTO whitelist + redaction functions prevent absolute paths
- **Secret leakage**: DTO whitelist + redaction functions prevent secrets
- **Policy drift**: Single source of truth (static module) for all counts
- **Client override**: Dangerous parameters explicitly rejected

---

## 35. Conclusion

This document freezes the complete scope, contract, DTO whitelist, frontend information
architecture, route governance, testing strategy, and zero-side-effect boundary for
Phase 1G-02: Tool Policy Read-Only API and Panel Implementation.

**Key frozen decisions:**

- Exactly 2 new GET routes (Policy Status + Catalog)
- OpenAPI 27 → 29 paths
- No write-like tool routes
- DTO whitelist of 15 fields per catalog item
- Forbidden fields list of 30+ entries
- Tools as first-level Workspace tab with 2 sub-tabs
- Backend service reads only from static immutable module
- No Registry, Handler, Provider, SessionDB, filesystem, or network access
- All tools return `allowed = false`
- All execution flags return `false`
- 51 acceptance criteria for implementation
- 3-commit implementation plan

Phase 1G-02-01 implementation may begin after this scope freeze is committed.
This document must not be modified during implementation except to record deviations
with explicit justification.
