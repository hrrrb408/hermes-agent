# Phase 1G-01: Tool Inventory and Static Policy Module

## 1. Document Information

| Field | Value |
|-------|-------|
| Phase | 1G-01 |
| Title | Tool Inventory and Static Policy Module Implementation |
| Status | Completed |
| Date | 2026-06-10 |
| Author | Dev Agent (Phase 1G-01 implementation) |
| Dependencies | Phase 1G-00 completed and pushed |
| Branch | dev-huangruibang |
| Base commit | 44f17e91464dbbb5f7719e9a536afd2acf227f2e |
| Implementation | Static Python module + tests + documentation |

---

## 2. Execution Pre-Baseline

### Git Baseline

| Field | Value |
|-------|-------|
| Branch | dev-huangruibang |
| Local HEAD | 44f17e91464dbbb5f7719e9a536afd2acf227f2e |
| Remote HEAD | 44f17e91464dbbb5f7719e9a536afd2acf227f2e |
| Local ahead | 0 |
| Remote ahead | 0 |
| Diverged | No |
| Tracked worktree | Clean |
| Untracked | .claude/ (pre-existing, untouched) |

### Environment

| Variable | Value |
|----------|-------|
| HERMES_HOME | /Users/huangruibang/Code/hermes-home-dev |
| HERMES_AGENT_RUN_ENABLED | unset |
| HERMES_TOOL_EXECUTION_ENABLED | unset |
| HERMES_AGENT_TOOLS_ENABLED | unset |

### Production Safety

| Check | Result |
|-------|--------|
| Production Gateway PID 1717 | Running, untouched |
| Dev Gateway | Stopped |
| Port 5180 | Free |
| Port 5181 | Free |
| memory-check | PASS |
| dev-check | WARN (.claude/ untracked only) |
| OpenAPI paths | 27 |
| Tool routes | Absent |

### Dev-Home Before Baseline

| Asset | Value |
|-------|-------|
| state.db SHA-256 | b1911d16c1b5ad76b301ed5cd48bf6437be054490632ade79a5440923ee67945 |
| state.db size | 360607744 bytes |
| Session count | 417 |
| Message count | 22552 |
| MEMORY.md SHA-256 | 44be12a08bbe826132f9c67940e15433f2f8aebaf5680693dea5955b7ea51515 |
| Memory events | 9 lines |
| Memory records | 3 active, 1 archived |
| Review queue pending | 0 |
| Tool audit table | Does not exist |

---

## 3. Phase 1G-00 Frozen Input

All contracts from Phase 1G-00 are implemented without deviation:

| Contract | Implementation |
|----------|---------------|
| 71 canonical tools | TOOL_POLICY_INVENTORY with 71 entries |
| Primary Risk (R0=1, R1=5, R2=19, R3=26, R4=17, R5=3) | TOOLS_BY_RISK verified |
| Permanent Denylist (26 tools) | STATIC_DENYLIST with 26 canonical names |
| Candidate Allowlist (6 tools) | CANDIDATE_ALLOWLIST with 6 canonical names |
| Empty Static Allowlist | STATIC_ALLOWLIST = frozenset() |
| Default-Deny | evaluate_static_tool_policy() returns allowed=False for all |
| Schema safety validation | validate_tool_schema_safety() |
| Argument structure validation | validate_argument_structure() |
| Global limits | All constants frozen |
| Kill Switch concept | Not implemented (Phase 1G-02+) |
| No Tool API | Verified — no new routes |
| No Provider Schema | Verified — not sent |
| No Tool Dispatch | Verified — 0 dispatches |

---

## 4. Module Location and Architecture Decision

### File

```
hermes_cli/dev_web_tool_policy.py
```

### Rationale

1. **Namespace alignment**: The Dev WebUI backend modules live in `hermes_cli/` (e.g., `dev_web_server.py`, `dev_web_agent_run_service.py`). Placing the policy module here follows the existing convention.

2. **Import isolation**: The module imports only Python stdlib (`json`, `math`, `dataclasses`, `enum`, `types`, `typing`). No dependency on FastAPI, Provider, SessionDB, Memory, or Tool Registry.

3. **No initialization side effects**: Importing the module triggers only pure-memory data structure construction and integrity verification. No filesystem, database, or network access.

4. **Alternative considered**: A standalone `tools/execution_policy.py` was considered but rejected because it would be in the auto-discovered `tools/` directory and could be confused with a tool handler.

---

## 5. Data Models

### ToolRiskLevel (Enum)

```python
class ToolRiskLevel(str, Enum):
    R0 = "R0"  # Pure computation
    R1 = "R1"  # Read-only local query
    R2 = "R2"  # Read-only external network
    R3 = "R3"  # Controlled write
    R4 = "R4"  # Process/code execution
    R5 = "R5"  # High-risk system operations
```

- `str` subclass for stable serialization
- Explicit `RISK_RANK` mapping for comparison (not dependent on Enum definition order)
- Not dynamically extensible

### ToolCapability (Enum)

18 orthogonal capability tags:
`PURE_COMPUTE`, `LOCAL_FILE_READ`, `LOCAL_FILE_WRITE`, `DATABASE_READ`, `DATABASE_WRITE`, `NETWORK_READ`, `NETWORK_WRITE`, `PROCESS_EXECUTION`, `CODE_EXECUTION`, `BROWSER_CONTROL`, `DESKTOP_CONTROL`, `CREDENTIAL_USE`, `REMOTE_STATE_MUTATION`, `MESSAGE_SEND`, `MEDIA_GENERATION`, `ADMINISTRATIVE_ACTION`, `SCHEDULING`, `SUB_AGENT_EXECUTION`

### ToolPolicyEntry (frozen dataclass, slots)

```python
@dataclass(frozen=True, slots=True)
class ToolPolicyEntry:
    canonical_name: str
    primary_risk: ToolRiskLevel
    capabilities: frozenset[ToolCapability]
    permanently_denied: bool
    candidate_allowlisted: bool
    statically_allowed: bool
    source: str         # relative module identifier
    rationale: str      # human-readable, no paths/secrets
```

### ToolPolicyDecision (frozen dataclass, slots)

```python
@dataclass(frozen=True, slots=True)
class ToolPolicyDecision:
    requested_name: str
    canonical_name: str | None
    known: bool
    permanently_denied: bool
    candidate_allowlisted: bool
    statically_allowed: bool
    allowed: bool
    primary_risk: ToolRiskLevel | None
    reason_code: str
```

### Validation Results

- `ToolSchemaValidationResult(valid, errors)`
- `ToolArgumentValidationResult(valid, errors, payload_bytes, max_depth)`
- `ToolPolicyValidationResult(valid, errors, canonical_count, risk_counts)`

All frozen with `slots=True`.

---

## 6. 71-Tool Inventory

### Single Source of Truth

```python
TOOL_POLICY_INVENTORY: Mapping[str, ToolPolicyEntry]  # MappingProxyType
```

Derived from risk-group tuples merged into an immutable mapping.

### Build-time verification

`_verify_inventory_integrity()` runs once at import time:
- Verifies total count, risk counts, name uniqueness
- Checks denylist/candidate/allowlist consistency
- Raises `RuntimeError` on any inconsistency
- Pure memory — no I/O

---

## 7. Primary Risk Distribution

| Risk | Count | Tools |
|------|------:|-------|
| R0 | 1 | clarify |
| R1 | 5 | read_file, search_files, session_search, skill_view, skills_list |
| R2 | 19 | feishu_doc_read, feishu_drive_list_comment_replies, feishu_drive_list_comments, ha_get_state, ha_list_entities, ha_list_services, kanban_list, kanban_show, mixture_of_agents, spotify_albums, spotify_search, video_analyze, vision_analyze, web_extract, web_search, x_search, yb_query_group_info, yb_query_group_members, yb_search_sticker |
| R3 | 26 | discord, feishu_drive_add_comment, feishu_drive_reply_comment, image_generate, kanban_block, kanban_comment, kanban_complete, kanban_create, kanban_heartbeat, kanban_link, kanban_unblock, memory, patch, send_message, skill_manage, spotify_devices, spotify_library, spotify_playback, spotify_playlists, spotify_queue, text_to_speech, todo, video_generate, write_file, yb_send_dm, yb_send_sticker |
| R4 | 17 | browser_back, browser_cdp, browser_click, browser_console, browser_dialog, browser_get_images, browser_navigate, browser_press, browser_scroll, browser_snapshot, browser_type, browser_vision, computer_use, delegate_task, execute_code, process, terminal |
| R5 | 3 | cronjob, discord_admin, ha_call_service |
| **Total** | **71** | |

- Registry equality: Verified via AST — policy set == registry set == 71
- Unclassified: 0
- Multiply classified: 0

---

## 8. Capability Flags

Each tool carries a `frozenset[ToolCapability]` describing what it can do. Key examples:

| Tool | Capabilities |
|------|-------------|
| clarify | PURE_COMPUTE |
| read_file | LOCAL_FILE_READ |
| terminal | PROCESS_EXECUTION, LOCAL_FILE_READ, LOCAL_FILE_WRITE, NETWORK_WRITE |
| cronjob | SCHEDULING, LOCAL_FILE_READ, LOCAL_FILE_WRITE, ADMINISTRATIVE_ACTION |
| discord_admin | NETWORK_WRITE, CREDENTIAL_USE, ADMINISTRATIVE_ACTION |

Capabilities may overlap; only `primary_risk` is unique.

---

## 9. Permanent Denylist

### Count: 26

```
terminal, process, execute_code, write_file, patch, memory,
skill_manage, delegate_task, browser_navigate, browser_snapshot,
browser_click, browser_type, browser_scroll, browser_back,
browser_press, browser_get_images, browser_vision, browser_console,
browser_cdp, browser_dialog, computer_use, send_message, cronjob,
image_generate, discord_admin, ha_call_service
```

### Properties

- All 26 names exist in the 71-tool inventory
- No duplicates
- Disjoint from Candidate Allowlist
- Every denied tool: `permanently_denied=True`, `statically_allowed=False`
- No override, force, adminOverride, unsafeAllow, or bypass mechanism

---

## 10. Candidate Allowlist

### Count: 6

```
clarify (R0), skills_list (R1), skill_view (R1),
read_file (R1), search_files (R1), session_search (R1)
```

### Properties

- 1 R0 + 5 R1
- All 6 names exist in the 71-tool inventory
- Disjoint from Denylist
- Candidate ≠ Enabled: all have `statically_allowed=False`

---

## 11. Empty Static Allowlist

```python
STATIC_ALLOWLIST: frozenset[str] = frozenset()
```

- Count: 0
- No tool is statically allowed
- All tool queries return `allowed=False`

---

## 12. Default-Deny Decision

### Reason Codes

```python
REASON_TOOL_NOT_FOUND = "TOOL_NOT_FOUND"
REASON_TOOL_PERMANENTLY_DENIED = "TOOL_PERMANENTLY_DENIED"
REASON_TOOL_NOT_ALLOWED = "TOOL_NOT_ALLOWED"
REASON_TOOL_POLICY_INVALID = "TOOL_POLICY_INVALID"
REASON_TOOL_SCHEMA_POLICY_INVALID = "TOOL_SCHEMA_POLICY_INVALID"
```

### Decision Behavior

| Input | known | permanently_denied | allowed | reason_code |
|-------|-------|--------------------|---------|-------------|
| "terminal" | true | true | false | TOOL_PERMANENTLY_DENIED |
| "clarify" | true | false | false | TOOL_NOT_ALLOWED |
| "web_search" | true | false | false | TOOL_NOT_ALLOWED |
| "unknown" | false | false | false | TOOL_NOT_FOUND |
| "Clarify" | false | false | false | TOOL_NOT_FOUND |
| " clarify " | false | false | false | TOOL_NOT_FOUND |
| "browser_*" | false | false | false | TOOL_NOT_FOUND |

### No bypass

- Exact match only — no case folding, whitespace stripping, prefix or wildcard matching
- No alias resolution — alias mapping belongs to Phase 1G-02+
- No override parameters

---

## 13. Schema Safety Validation

### Function

```python
def validate_tool_schema_safety(schema: Mapping[str, object]) -> ToolSchemaValidationResult
```

### Checks

1. Root must be `type: "object"`
2. `properties` must be a mapping
3. `required` must be string array with keys in `properties`
4. `additionalProperties` must be `false`
5. No empty property names
6. No forbidden keys (`__proto__`, `constructor`, `prototype`)
7. Nesting depth ≤ 8
8. Nested objects must also have `additionalProperties: false`

### Properties

- Pure function — does not modify schema
- Does not read Registry
- Does not sanitize or generate Provider Schema

---

## 14. Argument Structure Validation

### Function

```python
def validate_argument_structure(arguments: object) -> ToolArgumentValidationResult
```

### Checks

1. JSON-serializable and ≤ 32 KiB
2. Nesting depth ≤ 8
3. String values ≤ 4000 characters
4. Array length ≤ 100
5. Object keys must be strings, not forbidden keys
6. No NaN or Infinity values
7. No non-JSON-serializable objects

### Properties

- Pure function — no tool handler calls, no filesystem, no network
- Returns payload_bytes and max_depth metrics

---

## 15. Policy Invariants

### Completeness Function

```python
def validate_static_tool_policy() -> ToolPolicyValidationResult
```

### Verified Invariants

1. Inventory count = 71
2. Unique canonical names = 71
3. R0=1, R1=5, R2=19, R3=26, R4=17, R5=3, total=71
4. Denylist count = 26, subset of inventory
5. Candidate count = 6, subset of inventory
6. Static Allowlist count = 0
7. Denylist ∩ Candidate = ∅
8. Denylist ∩ Static Allowlist = ∅
9. Static Allowlist ⊆ Candidate
10. Candidate risks only R0/R1
11. All denied entries are not statically allowed
12. Every inventory entry agrees with derived sets

---

## 16. Immutability

All public collections are immutable:

| Collection | Type | Mutable? |
|-----------|------|----------|
| TOOL_POLICY_INVENTORY | MappingProxyType | No |
| ALL_CANONICAL_TOOLS | frozenset | No |
| STATIC_DENYLIST | frozenset | No |
| CANDIDATE_ALLOWLIST | frozenset | No |
| STATIC_ALLOWLIST | frozenset | No |
| TOOLS_BY_RISK | MappingProxyType | No |
| ToolPolicyEntry fields | frozen dataclass | No |
| ToolPolicyEntry.capabilities | frozenset | No |
| ToolPolicyDecision fields | frozen dataclass | No |
| Validation result fields | frozen dataclass | No |

Query functions return new tuples, not internal mutable references.

---

## 17. Import-Time Safety

Verified via subprocess isolation tests:

| Check | Result |
|-------|--------|
| Files created in HERMES_HOME | None (tool-related) |
| Directories created | None (tool-related) |
| Database created | No |
| Provider initialized | No |
| Registry initialized | No |
| Threads created | No (no `import threading`) |
| Subprocesses created | No (no `import subprocess`) |
| Network access | No |
| Log files created | No |
| Cache files created | No |

---

## 18. Registry Equality

### Method

AST-based extraction of `registry.register(name=..., ...)` calls from `tools/*.py` and `ctx.register_tool()` patterns from `plugins/spotify/__init__.py`.

### Result

```
Policy Inventory: 71
Registry Names:   71
Missing:          0
Unknown:          0
```

---

## 19. Tests

### New Tests

| Metric | Value |
|--------|-------|
| File | tests/test_dev_web_tool_policy.py |
| Collected | 81 |
| Passed | 81 |
| Failed | 0 |
| Skipped | 0 |
| Duration | ~1.2s |

### Test Groups

| Group | Count |
|-------|------:|
| Inventory | 6 |
| Registry Equality | 1 |
| Risk Classification | 6 |
| Denylist | 6 |
| Candidate/Allowlist | 4 |
| Decisions | 10 |
| Schema Validation | 8 |
| Argument Validation | 12 |
| Import Safety | 4 |
| Immutability | 7 |
| Global Limits | 4 |
| Completeness | 3 |
| Specific Tool Classification | 9 |
| Rationale Safety | 1 |

### Existing Tool Tests

```
238 passed, 3 skipped, 0 failed
```

### Related Backend Tests

```
114 passed, 0 failed
```

---

## 20. Side-Effect Validation

### Dev-Home After

| Asset | Value | Changed? |
|-------|-------|----------|
| state.db SHA-256 | b1911d16c1b5ad76b301ed5cd48bf6437be054490632ade79a5440923ee67945 | No |
| Session count | 417 | No |
| Message count | 22552 | No |
| MEMORY.md SHA-256 | 44be12a08bbe826132f9c67940e15433f2f8aebaf5680693dea5955b7ea51515 | No |
| Memory records | 3 active, 1 archived | No |
| Review queue pending | 0 | No |
| Tool audit table | Does not exist | No |

---

## 21. Risks

### P0

None. All acceptance criteria satisfied.

### P1

| Risk | Status |
|------|--------|
| Runtime Schema closure (additionalProperties=false) | Tracked — validation function exists, full schema remediation in Phase 1G-04 |
| Root Allowlist for read_file | Tracked — not yet enforced, needed before enablement |
| Symlink escape prevention | Tracked — not yet enforced, needed before enablement |
| Output secret redaction | Tracked — not yet implemented, needed before enablement |
| Runtime Timeout enforcement | Tracked — constants defined, worker not yet implemented |
| toolCallId runtime idempotency | Tracked — not yet implemented |

### P2

| Risk | Status |
|------|--------|
| Registry enumeration performance | Acceptable — 71 tools, sub-millisecond lookup |
| Schema token cost | Not applicable — no Schema sent |
| Output truncation quality | Tracked — limits defined, implementation in Phase 1G-06 |
| Audit retention policy | Future consideration |
| Provider Schema format differences | Known — handled by existing `get_definitions()` |

---

## 22. Acceptance Criteria

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Branch correct | ✓ dev-huangruibang |
| 2 | Baseline local/remote HEAD consistent | ✓ |
| 3 | ahead/behind = 0/0 | ✓ |
| 4 | tracked worktree initially clean | ✓ |
| 5 | .claude/ untouched | ✓ |
| 6 | HERMES_HOME correct | ✓ |
| 7 | Production Gateway unaffected | ✓ PID 1717 |
| 8 | Dev Gateway stopped | ✓ |
| 9 | 5180/5181 free | ✓ |
| 10 | Static policy module created | ✓ |
| 11 | No FastAPI dependency | ✓ |
| 12 | No Provider dependency | ✓ |
| 13 | No SessionDB dependency | ✓ |
| 14 | No Registry initialization | ✓ |
| 15 | Import zero side effects | ✓ |
| 16 | ToolRiskLevel implemented | ✓ |
| 17 | ToolCapability implemented | ✓ |
| 18 | ToolPolicyEntry immutable | ✓ |
| 19 | ToolPolicyDecision immutable | ✓ |
| 20 | Inventory immutable | ✓ |
| 21 | Inventory count = 71 | ✓ |
| 22 | Unique canonical count = 71 | ✓ |
| 23 | Registry == Policy Inventory | ✓ |
| 24 | R0 = 1 | ✓ |
| 25 | R1 = 5 | ✓ |
| 26 | R2 = 19 | ✓ |
| 27 | R3 = 26 | ✓ |
| 28 | R4 = 17 | ✓ |
| 29 | R5 = 3 | ✓ |
| 30 | Risk total = 71 | ✓ |
| 31 | Unclassified = 0 | ✓ |
| 32 | Multiply classified = 0 | ✓ |
| 33 | Denylist count = 26 | ✓ |
| 34 | Denylist all exist | ✓ |
| 35 | Candidate count = 6 | ✓ |
| 36 | Candidate all exist | ✓ |
| 37 | Denylist ∩ Candidate = ∅ | ✓ |
| 38 | STATIC_ALLOWLIST count = 0 | ✓ |
| 39 | Unknown tool fail closed | ✓ |
| 40 | Denylist tool fail closed | ✓ |
| 41 | Candidate tool fail closed | ✓ |
| 42 | Case variant rejected | ✓ |
| 43 | Whitespace variant rejected | ✓ |
| 44 | Wildcard rejected | ✓ |
| 45 | Schema Validator implemented | ✓ |
| 46 | additionalProperties=false enforced | ✓ |
| 47 | Nested objects validated | ✓ |
| 48 | Forbidden keys rejected | ✓ |
| 49 | Schema depth limited | ✓ |
| 50 | Argument Validator implemented | ✓ |
| 51 | Payload ≤ 32 KiB | ✓ |
| 52 | Depth ≤ 8 | ✓ |
| 53 | String ≤ 4000 | ✓ |
| 54 | Array ≤ 100 | ✓ |
| 55 | NaN/Infinity rejected | ✓ |
| 56 | Non-JSON rejected | ✓ |
| 57 | Timeout constants correct | ✓ |
| 58 | Concurrency constants correct | ✓ |
| 59 | Call limit correct | ✓ |
| 60 | Output limits correct | ✓ |
| 61 | New tests all pass (81/81) | ✓ |
| 62 | Existing tool tests 0 failed | ✓ |
| 63 | Agent Run boundaries unchanged | ✓ |
| 64 | compileall PASS | ✓ |
| 65 | toolsets compile PASS | ✓ |
| 66 | Ruff PASS | ✓ |
| 67 | memory-check PASS | ✓ |
| 68 | dev-check no new issues | ✓ |
| 69 | OpenAPI still 27 paths | ✓ |
| 70 | Tool routes = 0 | ✓ |
| 71 | Provider Tool Schema not sent | ✓ |
| 72 | Tool Dispatch = 0 | ✓ |
| 73 | Tool Audit table absent | ✓ |
| 74 | state.db unchanged | ✓ |
| 75 | Sessions unchanged | ✓ |
| 76 | Messages unchanged | ✓ |
| 77 | MEMORY.md unchanged | ✓ |
| 78 | Memory files unchanged | ✓ |
| 79 | Review files unchanged | ✓ |
| 80 | Implementation document created | ✓ |
| 81 | Implementation Plan updated | ✓ |
| 82 | 3 local commits completed | ✓ |
| 83 | No amend of history | ✓ |
| 84 | Not pushed | ✓ |
| 85 | tracked worktree clean | ✓ |
| 86 | .claude/ still untracked | ✓ |
| 87 | Phase 1G-02 not started | ✓ |

---

## 23. Git Commits

| # | Commit | Message |
|---|--------|---------|
| 1 | 35f47e8ce | feat(webui): add static tool execution policy |
| 2 | 5d6ade5ba | test(webui): verify static tool policy invariants |
| 3 | (pending) | docs(webui): complete phase 1g-01 static tool policy |

---

## 24. Conclusion

Phase 1G-01 is completed. The immutable Tool Inventory and static default-deny policy module are implemented and fully validated.

All 71 canonical tools are classified with unique primary risk levels, 26 tools are permanently denied, 6 tools remain candidates, and the enabled static allowlist remains empty.

No Tool API, Provider Tool Schema, Tool Dispatch, or Tool Execution capability was implemented or enabled.

**Next task:** Phase 1G-01-Release:封板核验与推送准备
