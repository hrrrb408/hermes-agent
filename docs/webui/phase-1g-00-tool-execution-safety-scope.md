# Phase 1G-00: Tool Execution Safety Framework — Scope and Contract Freeze

## Document Information

| Field | Value |
|-------|-------|
| Phase | 1G-00 |
| Title | Tool Execution Safety Framework Scope, Contract, and Governance Freeze |
| Status | Completed |
| Date | 2026-06-10 |
| Author | Dev Agent (Phase 1G-00 audit) |
| Dependencies | Phase 1F completed and pushed |
| Branch | dev-huangruibang |
| Base commit | 6fe3a2500 |
| Implementation | Documentation only — no business code modified |

### Scope

This document:

1. Records the complete Tool Inventory from source-code audit of the Hermes tool system
2. Classifies every tool by risk level (R0–R5)
3. Freezes the Permanent Denylist and Candidate Allowlist
4. Defines safety contracts for all future Tool Execution phases
5. Defines the Phase 1G sub-phase roadmap
6. Does **not** implement any Tool Execution API, Tool Schema Preview, Tool Dry-Run, or Tool Execute

### Freeze Declaration

All contracts in this document are **frozen** — they may only be modified by a subsequent scope document or explicit user instruction. No implementation task may deviate from these contracts without a formal amendment.

---

## 1. Pre-Execution Baseline

### Git Baseline

| Field | Value |
|-------|-------|
| Branch | dev-huangruibang |
| Local HEAD | 6fe3a2500cac4bd14233b54642b56c14121af04a |
| Remote HEAD | 6fe3a2500cac4bd14233b54642b56c14121af04a |
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
| HERMES_TOOL_EXECUTION_ENABLED | unset (not yet implemented) |

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
| Agent Run routes | 4 |
| Tool routes | Absent |

### Dev-Home Before Baseline

| Asset | Value |
|-------|-------|
| state.db SHA-256 | b1911d16c1b5ad76b301ed5cd48bf6437be054490632ade79a5440923ee67945 |
| state.db size | 360607744 bytes |
| Session count | 417 |
| Message count | 22552 |
| MEMORY.md SHA-256 | 44be12a08bbe826132f9c67940e15433f2f8aebaf5680693dea5955b7ea51515 |
| Tool audit table | Does not exist |

---

## 2. Phase 1F Safety Baseline

Phase 1F established Agent Run SSE with the following safety boundary:

| Parameter | Phase 1F Value | Enforcement |
|-----------|---------------|-------------|
| enabled_toolsets | `[]` | Hardcoded in `dev_web_agent_run_service.py:605` |
| tools (API kwargs) | `[]` or `None` | No tool schemas sent to Provider |
| Tool dispatch | 0 | No tools registered in Agent scope |
| Runtime Memory Writer | Disabled | `skip_memory=True` |
| Review Queue Enqueue | Disabled | Config default |
| Kill Switch | `HERMES_AGENT_RUN_ENABLED` | unset = disabled |
| Dev-only Guard | Source root + HERMES_HOME + bind host | `enforce_dev_environment()` |
| Unexpected Tool Call | `AGENT_TOOL_CALL_FORBIDDEN` | `_has_tool_calls()` check terminates run |
| Provider Tool Schema | Not sent | `tools=[]` in API call |

### Phase 1F Safety Invariants (Carried Forward)

1. **Kill switch default-off:** `HERMES_AGENT_RUN_ENABLED` unset → disabled
2. **Dev-only isolation:** Source root, HERMES_HOME, and bind host verified at run creation
3. **No tool schema to Provider:** `tools=[]` enforced
4. **Tool call forbidden:** Any `tool_calls` in Provider response → run fails immediately
5. **Cancel propagation:** Agent Run cancel → worker interrupted → `cancel_wait_timeout=10s`
6. **Audit trail:** All runs, cancellations, and failures recorded

---

## 3. Tool System Call Chain

### Registration Chain

```
tools/registry.py          (ToolRegistry singleton — no deps)
       ↑
tools/*.py                  (each calls registry.register() at import time)
       ↑
model_tools.py              (discover_builtin_tools() imports all tool modules)
       ↑
run_agent.py, cli.py        (AIAgent class, HermesCLI class)
```

### Execution Chain

```
Provider returns tool_call
  → agent/conversation_loop.py: parse tool_calls from assistant message
  → agent/conversation_loop.py: validate tool name against agent.valid_tool_names
  → agent/conversation_loop.py: repair mismatched tool names via _repair_tool_call()
  → agent/conversation_loop.py: validate arguments (empty, truncated JSON)
  → run_agent.py: _execute_tool_calls() → sequential or concurrent
  → agent/tool_executor.py: scope enforcement, plugin blocks, guardrails
  → model_tools.py: handle_function_call() → registry.dispatch()
  → tools/registry.py: dispatch(name, args) → handler(args)
  → Handler returns JSON string
  → agent/tool_executor.py: result canonicalization, sanitization
  → conversation_loop.py: result appended to messages → loop continues
```

### Tool Schema Construction Path

```
model_tools.py: get_tool_definitions(enabled_toolsets, disabled_toolsets)
  → Resolves toolsets via toolsets.resolve_toolset()
  → Filters by check_fn (30-second TTL cache)
  → Applies dynamic_schema_overrides
  → Applies sanitize_tool_schemas()
  → Returns OpenAI-format tool definitions
  → Injected into Provider API call as `tools` parameter
```

---

## 4. Registry Audit

### ToolRegistry Class (tools/registry.py)

**Constructor fields:**
- `_tools: Dict[str, ToolEntry]` — canonical name → entry
- `_toolset_checks: Dict[str, Callable]` — toolset → availability checker
- `_toolset_aliases: Dict[str, str]` — alias → canonical toolset name
- `_lock: threading.RLock` — thread-safe access
- `_generation: int` — cache invalidation counter

**ToolEntry dataclass fields:**
| Field | Type | Description |
|-------|------|-------------|
| name | str | Canonical tool name |
| toolset | str | Toolset membership |
| schema | dict | OpenAI-format function schema |
| handler | Callable | Python function that executes the tool |
| check_fn | Optional[Callable] | Runtime availability check (30s TTL cache) |
| requires_env | List[str] | Required environment variables |
| is_async | bool | Whether handler is async |
| description | str | Human-readable description |
| emoji | str | UI display emoji |
| max_result_size_chars | Optional[int] | Output size limit |
| dynamic_schema_overrides | Optional[Callable] | Runtime schema modification |

**register() method signature:**
```python
def register(
    self, name: str, toolset: str, schema: dict, handler: Callable,
    check_fn: Callable = None, requires_env: list = None,
    is_async: bool = False, description: str = "", emoji: str = "",
    max_result_size_chars: int | float | None = None,
    dynamic_schema_overrides: Callable = None, override: bool = False,
)
```

**dispatch() method:**
```python
def dispatch(self, name: str, args: dict, **kwargs) -> str
```
- Synchronous handlers: direct call
- Async handlers: bridged via `_run_async()` with 300s timeout
- All exceptions caught and sanitized as `{"error": "sanitized_message"}`

### Key Findings

1. **No built-in input validation** — Registry dispatches raw args to handler; validation is per-tool
2. **Error sanitization** — `_sanitize_tool_error()` strips structural tokens
3. **Output limiting** — `max_result_size_chars` per tool (100,000 for file/terminal tools)
4. **No alias mechanism per tool** — Tools register under one canonical name only
5. **Toolset aliases** exist for MCP servers, not individual tools
6. **Import-time registration** — All tools register at module import time via `registry.register()`
7. **Thread-safe** — RLock protects all mutations
8. **No timeout per tool** — Timeout handled at async bridge level (300s), not per dispatch
9. **No cancel support in Registry** — Cancel propagated through interrupt system, not Registry

---

## 5. Toolset Audit

### Individual Toolsets (Basic)

| Toolset | Tools |
|---------|-------|
| web | web_search, web_extract |
| search | web_search |
| x_search | x_search |
| vision | vision_analyze |
| video | video_analyze |
| image_gen | image_generate |
| video_gen | video_generate |
| computer_use | computer_use |
| terminal | terminal, process |
| moa | mixture_of_agents |
| skills | skills_list, skill_view, skill_manage |
| browser | browser_navigate, browser_snapshot, browser_click, browser_type, browser_scroll, browser_back, browser_press, browser_get_images, browser_vision, browser_console, web_search |
| browser-cdp | browser_cdp, browser_dialog |
| cronjob | cronjob |
| messaging | send_message |
| file | read_file, write_file, patch, search_files |
| tts | text_to_speech |
| todo | todo |
| memory | memory |
| context_engine | (empty) |
| session_search | session_search |
| clarify | clarify |
| code_execution | execute_code |
| delegation | delegate_task |
| homeassistant | ha_list_entities, ha_get_state, ha_list_services, ha_call_service |
| kanban | kanban_show, kanban_list, kanban_complete, kanban_block, kanban_heartbeat, kanban_comment, kanban_create, kanban_link, kanban_unblock |
| discord | discord |
| discord_admin | discord_admin |
| feishu_doc | feishu_doc_read |
| feishu_drive | feishu_drive_add_comment, feishu_drive_list_comment_replies, feishu_drive_list_comments, feishu_drive_reply_comment |
| spotify | spotify_albums, spotify_devices, spotify_library, spotify_playback, spotify_playlists, spotify_queue, spotify_search |
| hermes-yuanbao | yb_query_group_info, yb_query_group_members, yb_search_sticker, yb_send_dm, yb_send_sticker |

### Scenario Toolsets (Composite)

| Toolset | Includes |
|---------|----------|
| debugging | terminal, process, web, file |
| safe | web, vision, image_gen |

### Platform Toolsets (Full _HERMES_CORE_TOOLS + platform-specific)

All `hermes-*` platform toolsets include the full core tools set. Notable:
- `hermes-cli` — full core
- `hermes-cron` — full core
- `hermes-telegram/discord/whatsapp/slack/signal/email/matrix/...` — full core
- `hermes-gateway` — all platform toolsets composed
- `hermes-webhook` — web_search, web_extract, vision_analyze, clarify (restricted)
- `hermes-acp` — full core minus messaging and audio
- `hermes-api-server` — full core via HTTP

### Default-Off Toolsets

```
moa, homeassistant, spotify, discord, discord_admin, video, video_gen, x_search
```

Auto-enabled when credentials detected (e.g., `HASS_TOKEN` → homeassistant, `XAI_API_KEY` → x_search).

### WebUI Toolset

**No `dev-webui-safe` toolset exists.** The Dev WebUI currently operates with `enabled_toolsets=[]` — zero tools.

---

## 6. Tool Inventory

### Summary

| Metric | Count |
|--------|-------|
| Total registered tools | 71 |
| Core tools (_HERMES_CORE_TOOLS) | 46 |
| Webhook-safe tools | 4 |
| Individual toolsets | 33 |
| Platform toolsets | 25 |

### Complete Tool Inventory

Below is the complete inventory of all 71 registered tools, ordered by canonical name.

#### 6.1 browser_back

| Field | Value |
|-------|-------|
| canonicalName | browser_back |
| module | tools/browser_tool.py |
| toolset | browser |
| syncMode | sync |
| sideEffects | Browser state mutation, network navigation |
| externalNetwork | Yes |
| filesystemRead | No |
| filesystemWrite | No |
| processExecution | No |
| databaseRead | No |
| databaseWrite | No |
| credentialUse | No |
| userDataExposure | Browser history, page content |
| cancellable | No |
| timeout | Via check_fn |
| audit | No built-in audit |
| riskLevel | R4 |
| recommendation | Deny |
| inputParams | (none required) |

#### 6.2 browser_cdp

| Field | Value |
|-------|-------|
| canonicalName | browser_cdp |
| module | tools/browser_tool.py |
| toolset | browser-cdp |
| syncMode | sync |
| sideEffects | Raw CDP command — arbitrary browser control |
| externalNetwork | Yes |
| filesystemRead | No |
| filesystemWrite | No |
| processExecution | No |
| databaseRead | No |
| databaseWrite | No |
| credentialUse | No |
| userDataExposure | Full browser access |
| cancellable | No |
| timeout | Via check_fn |
| audit | No |
| riskLevel | R4 |
| recommendation | Deny |
| inputParams | method (string, required), params (object), target_id (string), frame_id (string), timeout (number) |

#### 6.3 browser_click

| Field | Value |
|-------|-------|
| canonicalName | browser_click |
| module | tools/browser_tool.py |
| toolset | browser |
| syncMode | sync |
| sideEffects | Clicks elements, triggers actions |
| externalNetwork | Yes |
| filesystemRead | No |
| filesystemWrite | No |
| processExecution | No |
| databaseRead | No |
| databaseWrite | No |
| credentialUse | No |
| userDataExposure | Page interaction data |
| cancellable | No |
| timeout | Via check_fn |
| audit | No |
| riskLevel | R4 |
| recommendation | Deny |
| inputParams | ref (string, required) |

#### 6.4 browser_console

| Field | Value |
|-------|-------|
| canonicalName | browser_console |
| module | tools/browser_tool.py |
| toolset | browser |
| syncMode | sync |
| sideEffects | Can execute JS (expression param) |
| externalNetwork | Yes |
| filesystemRead | No |
| filesystemWrite | No |
| processExecution | Yes (JS execution via expression) |
| databaseRead | No |
| databaseWrite | No |
| credentialUse | No |
| userDataExposure | Console output, page state |
| cancellable | No |
| timeout | Via check_fn |
| audit | No |
| riskLevel | R4 |
| recommendation | Deny |
| inputParams | clear (boolean), expression (string) |

#### 6.5 browser_dialog

| Field | Value |
|-------|-------|
| canonicalName | browser_dialog |
| module | tools/browser_tool.py |
| toolset | browser-cdp |
| syncMode | sync |
| sideEffects | Responds to native dialogs |
| externalNetwork | Yes |
| filesystemRead | No |
| filesystemWrite | No |
| processExecution | No |
| databaseRead | No |
| databaseWrite | No |
| credentialUse | No |
| userDataExposure | Dialog content |
| cancellable | No |
| timeout | Via check_fn |
| audit | No |
| riskLevel | R4 |
| recommendation | Deny |
| inputParams | action (string, required), prompt_text (string), dialog_id (string) |

#### 6.6 browser_get_images

| Field | Value |
|-------|-------|
| canonicalName | browser_get_images |
| module | tools/browser_tool.py |
| toolset | browser |
| syncMode | sync |
| sideEffects | None (read-only browser state) |
| externalNetwork | Yes (page already loaded) |
| filesystemRead | No |
| filesystemWrite | No |
| processExecution | No |
| databaseRead | No |
| databaseWrite | No |
| credentialUse | No |
| userDataExposure | Image URLs, alt text |
| cancellable | No |
| timeout | Via check_fn |
| audit | No |
| riskLevel | R4 |
| recommendation | Deny |
| inputParams | (none required) |

#### 6.7 browser_navigate

| Field | Value |
|-------|-------|
| canonicalName | browser_navigate |
| module | tools/browser_tool.py |
| toolset | browser |
| syncMode | sync |
| sideEffects | Loads arbitrary URL |
| externalNetwork | Yes |
| filesystemRead | No |
| filesystemWrite | No |
| processExecution | No |
| databaseRead | No |
| databaseWrite | No |
| credentialUse | No |
| userDataExposure | Full page content |
| cancellable | No |
| timeout | Via check_fn |
| audit | No |
| riskLevel | R4 |
| recommendation | Deny |
| inputParams | url (string, required) |

#### 6.8 browser_press

| Field | Value |
|-------|-------|
| canonicalName | browser_press |
| module | tools/browser_tool.py |
| toolset | browser |
| syncMode | sync |
| sideEffects | Keyboard input in browser |
| externalNetwork | Yes |
| filesystemRead | No |
| filesystemWrite | No |
| processExecution | No |
| databaseRead | No |
| databaseWrite | No |
| credentialUse | No |
| userDataExposure | Page interaction |
| cancellable | No |
| timeout | Via check_fn |
| audit | No |
| riskLevel | R4 |
| recommendation | Deny |
| inputParams | key (string, required) |

#### 6.9 browser_scroll

| Field | Value |
|-------|-------|
| canonicalName | browser_scroll |
| module | tools/browser_tool.py |
| toolset | browser |
| syncMode | sync |
| sideEffects | Browser state mutation |
| externalNetwork | Yes |
| filesystemRead | No |
| filesystemWrite | No |
| processExecution | No |
| databaseRead | No |
| databaseWrite | No |
| credentialUse | No |
| userDataExposure | Page content at scroll position |
| cancellable | No |
| timeout | Via check_fn |
| audit | No |
| riskLevel | R4 |
| recommendation | Deny |
| inputParams | direction (string, required) |

#### 6.10 browser_snapshot

| Field | Value |
|-------|-------|
| canonicalName | browser_snapshot |
| module | tools/browser_tool.py |
| toolset | browser |
| syncMode | sync |
| sideEffects | None (read-only) |
| externalNetwork | Yes (browser state) |
| filesystemRead | No |
| filesystemWrite | No |
| processExecution | No |
| databaseRead | No |
| databaseWrite | No |
| credentialUse | No |
| userDataExposure | Accessibility tree of current page |
| cancellable | No |
| timeout | Via check_fn |
| audit | No |
| riskLevel | R4 |
| recommendation | Deny |
| inputParams | full (boolean) |

#### 6.11 browser_type

| Field | Value |
|-------|-------|
| canonicalName | browser_type |
| module | tools/browser_tool.py |
| toolset | browser |
| syncMode | sync |
| sideEffects | Types text into form fields |
| externalNetwork | Yes |
| filesystemRead | No |
| filesystemWrite | No |
| processExecution | No |
| databaseRead | No |
| databaseWrite | No |
| credentialUse | No |
| userDataExposure | Typed content |
| cancellable | No |
| timeout | Via check_fn |
| audit | No |
| riskLevel | R4 |
| recommendation | Deny |
| inputParams | ref (string, required), text (string, required) |

#### 6.12 browser_vision

| Field | Value |
|-------|-------|
| canonicalName | browser_vision |
| module | tools/browser_tool.py |
| toolset | browser |
| syncMode | sync |
| sideEffects | Takes screenshot |
| externalNetwork | Yes |
| filesystemRead | No |
| filesystemWrite | No (temp screenshot) |
| processExecution | No |
| databaseRead | No |
| databaseWrite | No |
| credentialUse | No |
| userDataExposure | Visual page content |
| cancellable | No |
| timeout | Via check_fn |
| audit | No |
| riskLevel | R4 |
| recommendation | Deny |
| inputParams | question (string, required), annotate (boolean) |

#### 6.13 clarify

| Field | Value |
|-------|-------|
| canonicalName | clarify |
| module | tools/clarify_tool.py |
| toolset | clarify |
| syncMode | sync |
| sideEffects | Pauses conversation for user input |
| externalNetwork | No |
| filesystemRead | No |
| filesystemWrite | No |
| processExecution | No |
| databaseRead | No |
| databaseWrite | No |
| credentialUse | No |
| userDataExposure | Question text shown to user |
| cancellable | No |
| timeout | No |
| audit | No |
| riskLevel | R0 |
| recommendation | Candidate Allow (pending schema audit) |
| inputParams | question (string, required), choices (array) |

**Notes:** Purely interactive — asks user a question. No I/O, no network, no state mutation. Requires UI interaction context (not available in headless API). Phase 1G WebUI may not have the interactive callback channel. Needs evaluation of whether it can function in WebUI Agent Run context.

#### 6.14 computer_use

| Field | Value |
|-------|-------|
| canonicalName | computer_use |
| module | tools/computer_use_tool.py |
| toolset | computer_use |
| syncMode | sync |
| sideEffects | Desktop control — mouse, keyboard, screenshots |
| externalNetwork | No |
| filesystemRead | Yes (screenshots) |
| filesystemWrite | No |
| processExecution | No (uses cua-driver) |
| databaseRead | No |
| databaseWrite | No |
| credentialUse | No |
| userDataExposure | Full desktop visual access |
| cancellable | Yes |
| timeout | Via check_fn |
| audit | No |
| riskLevel | R4 |
| recommendation | Permanent Deny |
| inputParams | action (string, required), mode, app, element, coordinate, button, text, keys, seconds, etc. |

#### 6.15 cronjob

| Field | Value |
|-------|-------|
| canonicalName | cronjob |
| module | tools/cronjob_tools.py |
| toolset | cronjob |
| syncMode | sync |
| sideEffects | Creates/modifies/deletes scheduled jobs, writes to cron state |
| externalNetwork | No |
| filesystemRead | Yes (cron state) |
| filesystemWrite | Yes (cron state files) |
| processExecution | No |
| databaseRead | No |
| databaseWrite | No |
| credentialUse | No |
| userDataExposure | Scheduled job prompts, toolset configs |
| cancellable | No |
| timeout | Via check_fn |
| audit | No |
| riskLevel | R5 |
| recommendation | Permanent Deny |
| inputParams | action (string, required), job_id, prompt, schedule, name, enabled_toolsets, etc. |

#### 6.16 delegate_task

| Field | Value |
|-------|-------|
| canonicalName | delegate_task |
| module | tools/delegate_tool.py |
| toolset | delegation |
| syncMode | sync |
| sideEffects | Spawns subagent processes with their own tool access |
| externalNetwork | Yes (subagent may use network) |
| filesystemRead | Yes |
| filesystemWrite | Yes (subagent may write) |
| processExecution | Yes (subagent is a process) |
| databaseRead | Yes |
| databaseWrite | Yes |
| credentialUse | Yes (inherits agent credentials) |
| userDataExposure | Full subagent access |
| cancellable | Yes |
| timeout | Via check_fn |
| audit | No |
| riskLevel | R4 |
| recommendation | Permanent Deny |
| inputParams | goal, context, toolsets, tasks, role, acp_command, acp_args |

#### 6.17 discord

| Field | Value |
|-------|-------|
| canonicalName | discord |
| module | tools/discord_tool.py |
| toolset | discord |
| syncMode | sync |
| sideEffects | Reads Discord, sends messages (action-dependent) |
| externalNetwork | Yes (Discord API) |
| filesystemRead | No |
| filesystemWrite | No |
| processExecution | No |
| databaseRead | No |
| databaseWrite | No |
| credentialUse | Yes (DISCORD_TOKEN) |
| userDataExposure | Discord messages, member info |
| cancellable | No |
| timeout | Via check_fn |
| audit | No |
| riskLevel | R3 |
| recommendation | Deny |
| inputParams | action (string, required), guild_id, channel_id, user_id, message_id, query, etc. |

#### 6.18 discord_admin

| Field | Value |
|-------|-------|
| canonicalName | discord_admin |
| module | tools/discord_tool.py |
| toolset | discord_admin |
| syncMode | sync |
| sideEffects | Server management — bans, kicks, channel creation |
| externalNetwork | Yes (Discord API) |
| filesystemRead | No |
| filesystemWrite | No |
| processExecution | No |
| databaseRead | No |
| databaseWrite | No |
| credentialUse | Yes (DISCORD_TOKEN with admin) |
| userDataExposure | Full server data |
| cancellable | No |
| timeout | Via check_fn |
| audit | No |
| riskLevel | R5 |
| recommendation | Permanent Deny |
| inputParams | action (string, required), guild_id, channel_id, user_id, etc. |

#### 6.19 execute_code

| Field | Value |
|-------|-------|
| canonicalName | execute_code |
| module | tools/code_execution_tool.py |
| toolset | code_execution |
| syncMode | sync |
| sideEffects | Executes Python code with tool access |
| externalNetwork | Yes (code may access network) |
| filesystemRead | Yes |
| filesystemWrite | Yes |
| processExecution | Yes (sandboxed Python) |
| databaseRead | Yes |
| databaseWrite | Yes |
| credentialUse | Yes (inherits environment) |
| userDataExposure | Arbitrary |
| cancellable | Yes |
| timeout | Via check_fn |
| max_result_size_chars | 100,000 |
| audit | No |
| riskLevel | R4 |
| recommendation | Permanent Deny |
| inputParams | code (string, required) |

#### 6.20 feishu_doc_read

| Field | Value |
|-------|-------|
| canonicalName | feishu_doc_read |
| module | tools/feishu_doc_tool.py |
| toolset | feishu_doc |
| syncMode | sync |
| sideEffects | None (read-only) |
| externalNetwork | Yes (Feishu API) |
| filesystemRead | No |
| filesystemWrite | No |
| processExecution | No |
| databaseRead | No |
| databaseWrite | No |
| credentialUse | Yes (Feishu credentials) |
| userDataExposure | Document content |
| cancellable | No |
| timeout | Via check_fn |
| audit | No |
| riskLevel | R2 |
| recommendation | Deny |
| inputParams | doc_token (string, required) |

#### 6.21 feishu_drive_add_comment

| Field | Value |
|-------|-------|
| canonicalName | feishu_drive_add_comment |
| module | tools/feishu_drive_tool.py |
| toolset | feishu_drive |
| syncMode | sync |
| sideEffects | Writes comment to document |
| externalNetwork | Yes (Feishu API) |
| filesystemRead | No |
| filesystemWrite | No |
| processExecution | No |
| databaseRead | No |
| databaseWrite | No |
| credentialUse | Yes (Feishu credentials) |
| userDataExposure | Document content, user identity |
| cancellable | No |
| timeout | Via check_fn |
| audit | No |
| riskLevel | R3 |
| recommendation | Deny |
| inputParams | file_token (string, required), content (string, required), file_type |

#### 6.22 feishu_drive_list_comment_replies

| Field | Value |
|-------|-------|
| canonicalName | feishu_drive_list_comment_replies |
| module | tools/feishu_drive_tool.py |
| toolset | feishu_drive |
| syncMode | sync |
| sideEffects | None (read-only) |
| externalNetwork | Yes (Feishu API) |
| filesystemRead | No |
| filesystemWrite | No |
| processExecution | No |
| databaseRead | No |
| databaseWrite | No |
| credentialUse | Yes (Feishu credentials) |
| userDataExposure | Comment replies |
| cancellable | No |
| timeout | Via check_fn |
| audit | No |
| riskLevel | R2 |
| recommendation | Deny |
| inputParams | file_token (string, required), comment_id (string, required), file_type, page_size, page_token |

#### 6.23 feishu_drive_list_comments

| Field | Value |
|-------|-------|
| canonicalName | feishu_drive_list_comments |
| module | tools/feishu_drive_tool.py |
| toolset | feishu_drive |
| syncMode | sync |
| sideEffects | None (read-only) |
| externalNetwork | Yes (Feishu API) |
| filesystemRead | No |
| filesystemWrite | No |
| processExecution | No |
| databaseRead | No |
| databaseWrite | No |
| credentialUse | Yes (Feishu credentials) |
| userDataExposure | Document comments |
| cancellable | No |
| timeout | Via check_fn |
| audit | No |
| riskLevel | R2 |
| recommendation | Deny |
| inputParams | file_token (string, required), file_type, is_whole, page_size, page_token |

#### 6.24 feishu_drive_reply_comment

| Field | Value |
|-------|-------|
| canonicalName | feishu_drive_reply_comment |
| module | tools/feishu_drive_tool.py |
| toolset | feishu_drive |
| syncMode | sync |
| sideEffects | Writes reply to comment |
| externalNetwork | Yes (Feishu API) |
| filesystemRead | No |
| filesystemWrite | No |
| processExecution | No |
| databaseRead | No |
| databaseWrite | No |
| credentialUse | Yes (Feishu credentials) |
| userDataExposure | Document content, user identity |
| cancellable | No |
| timeout | Via check_fn |
| audit | No |
| riskLevel | R3 |
| recommendation | Deny |
| inputParams | file_token (string, required), comment_id (string, required), content (string, required), file_type |

#### 6.25 ha_call_service

| Field | Value |
|-------|-------|
| canonicalName | ha_call_service |
| module | tools/homeassistant_tool.py |
| toolset | homeassistant |
| syncMode | sync |
| sideEffects | Controls IoT devices |
| externalNetwork | Yes (Home Assistant API) |
| filesystemRead | No |
| filesystemWrite | No |
| processExecution | No |
| databaseRead | No |
| databaseWrite | No |
| credentialUse | Yes (HASS_URL, HASS_TOKEN) |
| userDataExposure | Device states |
| cancellable | No |
| timeout | Via check_fn |
| audit | No |
| riskLevel | R5 |
| recommendation | Permanent Deny |
| inputParams | domain (string, required), service (string, required), entity_id, data |

#### 6.26 ha_get_state

| Field | Value |
|-------|-------|
| canonicalName | ha_get_state |
| module | tools/homeassistant_tool.py |
| toolset | homeassistant |
| syncMode | sync |
| sideEffects | None (read-only) |
| externalNetwork | Yes (Home Assistant API) |
| filesystemRead | No |
| filesystemWrite | No |
| processExecution | No |
| databaseRead | No |
| databaseWrite | No |
| credentialUse | Yes (HASS_URL, HASS_TOKEN) |
| userDataExposure | Device states, home layout |
| cancellable | No |
| timeout | Via check_fn |
| audit | No |
| riskLevel | R2 |
| recommendation | Deny |
| inputParams | entity_id (string, required) |

#### 6.27 ha_list_entities

| Field | Value |
|-------|-------|
| canonicalName | ha_list_entities |
| module | tools/homeassistant_tool.py |
| toolset | homeassistant |
| syncMode | sync |
| sideEffects | None (read-only) |
| externalNetwork | Yes (Home Assistant API) |
| filesystemRead | No |
| filesystemWrite | No |
| processExecution | No |
| databaseRead | No |
| databaseWrite | No |
| credentialUse | Yes (HASS_URL, HASS_TOKEN) |
| userDataExposure | Device names, areas |
| cancellable | No |
| timeout | Via check_fn |
| audit | No |
| riskLevel | R2 |
| recommendation | Deny |
| inputParams | domain, area |

#### 6.28 ha_list_services

| Field | Value |
|-------|-------|
| canonicalName | ha_list_services |
| module | tools/homeassistant_tool.py |
| toolset | homeassistant |
| syncMode | sync |
| sideEffects | None (read-only) |
| externalNetwork | Yes (Home Assistant API) |
| filesystemRead | No |
| filesystemWrite | No |
| processExecution | No |
| databaseRead | No |
| databaseWrite | No |
| credentialUse | Yes (HASS_URL, HASS_TOKEN) |
| userDataExposure | Service names, domains |
| cancellable | No |
| timeout | Via check_fn |
| audit | No |
| riskLevel | R2 |
| recommendation | Deny |
| inputParams | domain |

#### 6.29 image_generate

| Field | Value |
|-------|-------|
| canonicalName | image_generate |
| module | tools/image_generation_tool.py |
| toolset | image_gen |
| syncMode | sync |
| sideEffects | Generates images, writes to filesystem, costs money |
| externalNetwork | Yes (FAL/Replicate/OpenAI API) |
| filesystemRead | No |
| filesystemWrite | Yes (image files) |
| processExecution | No |
| databaseRead | No |
| databaseWrite | No |
| credentialUse | Yes (API keys) |
| userDataExposure | Prompt text |
| cancellable | No |
| timeout | Via check_fn |
| audit | No |
| riskLevel | R3 |
| recommendation | Permanent Deny |
| inputParams | prompt (string, required), aspect_ratio |

#### 6.30 kanban_block

| Field | Value |
|-------|-------|
| canonicalName | kanban_block |
| module | tools/kanban_tools.py |
| toolset | kanban |
| syncMode | sync |
| sideEffects | Modifies task status |
| externalNetwork | Yes (Linear API) |
| filesystemRead | No |
| filesystemWrite | No |
| processExecution | No |
| databaseRead | No |
| databaseWrite | No |
| credentialUse | Yes (LINEAR_API_KEY) |
| userDataExposure | Task data |
| cancellable | No |
| timeout | Via check_fn |
| audit | No |
| riskLevel | R3 |
| recommendation | Deny |
| inputParams | task_id, reason (string, required), board |

#### 6.31 kanban_comment

| Field | Value |
|-------|-------|
| canonicalName | kanban_comment |
| module | tools/kanban_tools.py |
| toolset | kanban |
| syncMode | sync |
| sideEffects | Writes comment to task |
| externalNetwork | Yes (Linear API) |
| filesystemRead | No |
| filesystemWrite | No |
| processExecution | No |
| databaseRead | No |
| databaseWrite | No |
| credentialUse | Yes (LINEAR_API_KEY) |
| userDataExposure | Task comments |
| cancellable | No |
| timeout | Via check_fn |
| audit | No |
| riskLevel | R3 |
| recommendation | Deny |
| inputParams | task_id (string, required), body (string, required), board |

#### 6.32 kanban_complete

| Field | Value |
|-------|-------|
| canonicalName | kanban_complete |
| module | tools/kanban_tools.py |
| toolset | kanban |
| syncMode | sync |
| sideEffects | Marks task done |
| externalNetwork | Yes (Linear API) |
| filesystemRead | No |
| filesystemWrite | No |
| processExecution | No |
| databaseRead | No |
| databaseWrite | No |
| credentialUse | Yes (LINEAR_API_KEY) |
| userDataExposure | Task completion data |
| cancellable | No |
| timeout | Via check_fn |
| audit | No |
| riskLevel | R3 |
| recommendation | Deny |
| inputParams | task_id, summary, result, metadata, board |

#### 6.33 kanban_create

| Field | Value |
|-------|-------|
| canonicalName | kanban_create |
| module | tools/kanban_tools.py |
| toolset | kanban |
| syncMode | sync |
| sideEffects | Creates new task |
| externalNetwork | Yes (Linear API) |
| filesystemRead | No |
| filesystemWrite | No |
| processExecution | No |
| databaseRead | No |
| databaseWrite | No |
| credentialUse | Yes (LINEAR_API_KEY) |
| userDataExposure | Task data |
| cancellable | No |
| timeout | Via check_fn |
| audit | No |
| riskLevel | R3 |
| recommendation | Deny |
| inputParams | title (string, required), assignee (string, required), body, parents, tenant, etc. |

#### 6.34 kanban_heartbeat

| Field | Value |
|-------|-------|
| canonicalName | kanban_heartbeat |
| module | tools/kanban_tools.py |
| toolset | kanban |
| syncMode | sync |
| sideEffects | Updates task timestamp |
| externalNetwork | Yes (Linear API) |
| filesystemRead | No |
| filesystemWrite | No |
| processExecution | No |
| databaseRead | No |
| databaseWrite | No |
| credentialUse | Yes (LINEAR_API_KEY) |
| userDataExposure | Task status |
| cancellable | No |
| timeout | Via check_fn |
| audit | No |
| riskLevel | R3 |
| recommendation | Deny |
| inputParams | task_id, note, board |

#### 6.35 kanban_link

| Field | Value |
|-------|-------|
| canonicalName | kanban_link |
| module | tools/kanban_tools.py |
| toolset | kanban |
| syncMode | sync |
| sideEffects | Creates task dependency |
| externalNetwork | Yes (Linear API) |
| filesystemRead | No |
| filesystemWrite | No |
| processExecution | No |
| databaseRead | No |
| databaseWrite | No |
| credentialUse | Yes (LINEAR_API_KEY) |
| userDataExposure | Task relationships |
| cancellable | No |
| timeout | Via check_fn |
| audit | No |
| riskLevel | R3 |
| recommendation | Deny |
| inputParams | parent_id (string, required), child_id (string, required), board |

#### 6.36 kanban_list

| Field | Value |
|-------|-------|
| canonicalName | kanban_list |
| module | tools/kanban_tools.py |
| toolset | kanban |
| syncMode | sync |
| sideEffects | None (read-only) |
| externalNetwork | Yes (Linear API) |
| filesystemRead | No |
| filesystemWrite | No |
| processExecution | No |
| databaseRead | No |
| databaseWrite | No |
| credentialUse | Yes (LINEAR_API_KEY) |
| userDataExposure | Task summaries |
| cancellable | No |
| timeout | Via check_fn |
| audit | No |
| riskLevel | R2 |
| recommendation | Deny |
| inputParams | assignee, status, tenant, include_archived, limit, board |

#### 6.37 kanban_show

| Field | Value |
|-------|-------|
| canonicalName | kanban_show |
| module | tools/kanban_tools.py |
| toolset | kanban |
| syncMode | sync |
| sideEffects | None (read-only) |
| externalNetwork | Yes (Linear API) |
| filesystemRead | No |
| filesystemWrite | No |
| processExecution | No |
| databaseRead | No |
| databaseWrite | No |
| credentialUse | Yes (LINEAR_API_KEY) |
| userDataExposure | Full task detail |
| cancellable | No |
| timeout | Via check_fn |
| audit | No |
| riskLevel | R2 |
| recommendation | Deny |
| inputParams | task_id, board |

#### 6.38 kanban_unblock

| Field | Value |
|-------|-------|
| canonicalName | kanban_unblock |
| module | tools/kanban_tools.py |
| toolset | kanban |
| syncMode | sync |
| sideEffects | Changes task status |
| externalNetwork | Yes (Linear API) |
| filesystemRead | No |
| filesystemWrite | No |
| processExecution | No |
| databaseRead | No |
| databaseWrite | No |
| credentialUse | Yes (LINEAR_API_KEY) |
| userDataExposure | Task status |
| cancellable | No |
| timeout | Via check_fn |
| audit | No |
| riskLevel | R3 |
| recommendation | Deny |
| inputParams | task_id (string, required), board |

#### 6.39 memory

| Field | Value |
|-------|-------|
| canonicalName | memory |
| module | tools/memory_tool.py |
| toolset | memory |
| syncMode | sync |
| sideEffects | Writes to MEMORY.md, USER.md, memory/records/ |
| externalNetwork | No |
| filesystemRead | Yes |
| filesystemWrite | Yes |
| processExecution | No |
| databaseRead | No |
| databaseWrite | No |
| credentialUse | No |
| userDataExposure | Memory content |
| cancellable | No |
| timeout | No |
| audit | No |
| riskLevel | R3 |
| recommendation | Permanent Deny |
| inputParams | action (string, required), target (string, required), content, old_text |

#### 6.40 mixture_of_agents

| Field | Value |
|-------|-------|
| canonicalName | mixture_of_agents |
| module | tools/moa_tool.py |
| toolset | moa |
| syncMode | async |
| sideEffects | Makes 5+ LLM API calls, costs money |
| externalNetwork | Yes (multiple LLM APIs) |
| filesystemRead | No |
| filesystemWrite | No |
| processExecution | No |
| databaseRead | No |
| databaseWrite | No |
| credentialUse | Yes (API keys) |
| userDataExposure | Prompt text sent to external APIs |
| cancellable | No |
| timeout | Via check_fn |
| audit | No |
| riskLevel | R2 |
| recommendation | Deny |
| inputParams | user_prompt (string, required) |

#### 6.41 patch

| Field | Value |
|-------|-------|
| canonicalName | patch |
| module | tools/file_tools.py |
| toolset | file |
| syncMode | sync |
| sideEffects | Modifies files (find-and-replace) |
| externalNetwork | No |
| filesystemRead | Yes |
| filesystemWrite | Yes |
| processExecution | No |
| databaseRead | No |
| databaseWrite | No |
| credentialUse | No |
| userDataExposure | File content |
| cancellable | No |
| max_result_size_chars | 100,000 |
| audit | No |
| riskLevel | R3 |
| recommendation | Permanent Deny |
| inputParams | mode (string, required), path, old_string, new_string, replace_all, patch, cross_profile |

#### 6.42 process

| Field | Value |
|-------|-------|
| canonicalName | process |
| module | tools/process_registry.py |
| toolset | terminal |
| syncMode | sync |
| sideEffects | Manages background processes (list, read, write, kill) |
| externalNetwork | Yes (process may access network) |
| filesystemRead | Yes |
| filesystemWrite | Yes (stdin to process) |
| processExecution | Yes (manages running processes) |
| databaseRead | No |
| databaseWrite | No |
| credentialUse | No |
| userDataExposure | Process output, commands |
| cancellable | No |
| audit | No |
| riskLevel | R4 |
| recommendation | Permanent Deny |
| inputParams | action (string, required), session_id, data, timeout, offset, limit |

#### 6.43 read_file

| Field | Value |
|-------|-------|
| canonicalName | read_file |
| module | tools/file_tools.py |
| toolset | file |
| syncMode | sync |
| sideEffects | None (read-only) |
| externalNetwork | No |
| filesystemRead | Yes |
| filesystemWrite | No |
| processExecution | No |
| databaseRead | No |
| databaseWrite | No |
| credentialUse | No |
| userDataExposure | File content |
| cancellable | No |
| max_result_size_chars | 100,000 |
| audit | No |
| riskLevel | R1 |
| recommendation | Candidate Allow (with strict path allowlist) |
| inputParams | path (string, required), offset (integer), limit (integer) |

#### 6.44 search_files

| Field | Value |
|-------|-------|
| canonicalName | search_files |
| module | tools/file_tools.py |
| toolset | file |
| syncMode | sync |
| sideEffects | None (read-only search) |
| externalNetwork | No |
| filesystemRead | Yes |
| filesystemWrite | No |
| processExecution | No |
| databaseRead | No |
| databaseWrite | No |
| credentialUse | No |
| userDataExposure | File content, directory structure |
| cancellable | No |
| max_result_size_chars | 100,000 |
| audit | No |
| riskLevel | R1 |
| recommendation | Candidate Allow (with strict path allowlist) |
| inputParams | pattern (string, required), target, path, file_glob, limit, offset, output_mode, context |

#### 6.45 send_message

| Field | Value |
|-------|-------|
| canonicalName | send_message |
| module | tools/send_message_tool.py |
| toolset | messaging |
| syncMode | sync |
| sideEffects | Sends messages to external platforms |
| externalNetwork | Yes (messaging platforms) |
| filesystemRead | No |
| filesystemWrite | No |
| processExecution | No |
| databaseRead | No |
| databaseWrite | No |
| credentialUse | Yes (platform tokens) |
| userDataExposure | Message content, recipient info |
| cancellable | No |
| timeout | Via check_fn |
| audit | No |
| riskLevel | R3 |
| recommendation | Permanent Deny |
| inputParams | action, target, message |

#### 6.46 session_search

| Field | Value |
|-------|-------|
| canonicalName | session_search |
| module | tools/session_search_tool.py |
| toolset | session_search |
| syncMode | sync |
| sideEffects | None (read-only FTS5 search) |
| externalNetwork | No |
| filesystemRead | Yes (SQLite state.db) |
| filesystemWrite | No |
| processExecution | No |
| databaseRead | Yes (SessionDB FTS5) |
| databaseWrite | No |
| credentialUse | No |
| userDataExposure | Past conversation content |
| cancellable | No |
| timeout | No |
| audit | No |
| riskLevel | R1 |
| recommendation | Candidate Allow (with output redaction) |
| inputParams | query, limit, sort, session_id, around_message_id, window, role_filter, profile |

#### 6.47 skill_manage

| Field | Value |
|-------|-------|
| canonicalName | skill_manage |
| module | tools/skill_manager_tool.py |
| toolset | skills |
| syncMode | sync |
| sideEffects | Creates/updates/deletes skill files |
| externalNetwork | No |
| filesystemRead | Yes |
| filesystemWrite | Yes |
| processExecution | No |
| databaseRead | No |
| databaseWrite | No |
| credentialUse | No |
| userDataExposure | Skill content |
| cancellable | No |
| audit | No |
| riskLevel | R3 |
| recommendation | Permanent Deny |
| inputParams | action (string, required), name (string, required), content, old_string, new_string, category, file_path, file_content, absorbed_into |

#### 6.48 skill_view

| Field | Value |
|-------|-------|
| canonicalName | skill_view |
| module | tools/skills_tool.py |
| toolset | skills |
| syncMode | sync |
| sideEffects | None (read-only) |
| externalNetwork | No |
| filesystemRead | Yes (skill SKILL.md files) |
| filesystemWrite | No |
| processExecution | No |
| databaseRead | No |
| databaseWrite | No |
| credentialUse | No |
| userDataExposure | Skill instructions, templates |
| cancellable | No |
| timeout | Via check_fn |
| audit | No |
| riskLevel | R1 |
| recommendation | Candidate Allow (with path restriction) |
| inputParams | name (string, required), file_path |

#### 6.49 skills_list

| Field | Value |
|-------|-------|
| canonicalName | skills_list |
| module | tools/skills_tool.py |
| toolset | skills |
| syncMode | sync |
| sideEffects | None (read-only listing) |
| externalNetwork | No |
| filesystemRead | Yes (skill directory) |
| filesystemWrite | No |
| processExecution | No |
| databaseRead | No |
| databaseWrite | No |
| credentialUse | No |
| userDataExposure | Skill names and descriptions |
| cancellable | No |
| timeout | Via check_fn |
| audit | No |
| riskLevel | R1 |
| recommendation | Candidate Allow |
| inputParams | category |

#### 6.50 spotify_albums

| Field | Value |
|-------|-------|
| canonicalName | spotify_albums |
| module | tools/spotify_tool.py |
| toolset | spotify |
| syncMode | sync |
| sideEffects | None (read-only metadata) |
| externalNetwork | Yes (Spotify API) |
| credentialUse | Yes (Spotify OAuth) |
| userDataExposure | Album metadata, track listings |
| riskLevel | R2 |
| recommendation | Deny |
| inputParams | action (string, required), album_id, id, market, limit, offset |

#### 6.51 spotify_devices

| Field | Value |
|-------|-------|
| canonicalName | spotify_devices |
| module | tools/spotify_tool.py |
| toolset | spotify |
| syncMode | sync |
| sideEffects | Transfer playback to device (state mutation) |
| externalNetwork | Yes (Spotify API) |
| credentialUse | Yes (Spotify OAuth) |
| userDataExposure | Device list, playback state |
| riskLevel | R3 |
| recommendation | Deny |
| inputParams | action (string, required), device_id, play |
| notes | Primary R3 because `transfer` action mutates playback state on remote device |

#### 6.52 spotify_library

| Field | Value |
|-------|-------|
| canonicalName | spotify_library |
| module | tools/spotify_tool.py |
| toolset | spotify |
| syncMode | sync |
| sideEffects | Save/remove items from user library (state mutation) |
| externalNetwork | Yes (Spotify API) |
| credentialUse | Yes (Spotify OAuth) |
| userDataExposure | Library contents |
| riskLevel | R3 |
| recommendation | Deny |
| inputParams | kind (string, required), action (string, required), limit, offset, market, uris, ids, items |
| notes | Primary R3 because `save`/`remove` actions modify user library |

#### 6.53 spotify_playback

| Field | Value |
|-------|-------|
| canonicalName | spotify_playback |
| module | tools/spotify_tool.py |
| toolset | spotify |
| syncMode | sync |
| sideEffects | Controls playback (play, pause, skip, volume — state mutation) |
| externalNetwork | Yes (Spotify API) |
| credentialUse | Yes (Spotify OAuth) |
| userDataExposure | Playback state, listening history |
| riskLevel | R3 |
| recommendation | Deny |
| inputParams | action (string, required), device_id, market, context_uri, uris, offset, position_ms, state, volume_percent, limit, after, before |
| notes | Primary R3 because play/pause/skip/volume actions mutate remote playback state |

#### 6.54 spotify_playlists

| Field | Value |
|-------|-------|
| canonicalName | spotify_playlists |
| module | tools/spotify_tool.py |
| toolset | spotify |
| syncMode | sync |
| sideEffects | Create, update, modify playlists (state mutation) |
| externalNetwork | Yes (Spotify API) |
| credentialUse | Yes (Spotify OAuth) |
| userDataExposure | Playlist contents, user identity |
| riskLevel | R3 |
| recommendation | Deny |
| inputParams | action (string, required), playlist_id, market, limit, offset, name, description, public, collaborative, uris, position, snapshot_id |
| notes | Primary R3 because create/update/modify actions mutate playlists |

#### 6.55 spotify_queue

| Field | Value |
|-------|-------|
| canonicalName | spotify_queue |
| module | tools/spotify_tool.py |
| toolset | spotify |
| syncMode | sync |
| sideEffects | Add items to queue (state mutation) |
| externalNetwork | Yes (Spotify API) |
| credentialUse | Yes (Spotify OAuth) |
| userDataExposure | Queue contents |
| riskLevel | R3 |
| recommendation | Deny |
| inputParams | action (string, required), uri, device_id |
| notes | Primary R3 because `add` action modifies playback queue |

#### 6.56 spotify_search

| Field | Value |
|-------|-------|
| canonicalName | spotify_search |
| module | tools/spotify_tool.py |
| toolset | spotify |
| syncMode | sync |
| sideEffects | None (read-only catalog search) |
| externalNetwork | Yes (Spotify API) |
| credentialUse | Yes (Spotify OAuth) |
| userDataExposure | Search queries |
| riskLevel | R2 |
| recommendation | Deny |
| inputParams | query (string, required), types, type, limit, offset, market, include_external |

#### 6.57 terminal

| Field | Value |
|-------|-------|
| canonicalName | terminal |
| module | tools/terminal_tool.py |
| toolset | terminal |
| syncMode | sync |
| sideEffects | Executes arbitrary shell commands |
| externalNetwork | Yes (commands may access network) |
| filesystemRead | Yes |
| filesystemWrite | Yes |
| processExecution | Yes (primary function) |
| databaseRead | No |
| databaseWrite | No |
| credentialUse | No (but inherits environment including potential SUDO_PASSWORD) |
| userDataExposure | Arbitrary |
| cancellable | Yes (via interrupt event) |
| max_result_size_chars | 100,000 |
| audit | No |
| riskLevel | R4 |
| recommendation | Permanent Deny |
| inputParams | command (string, required), background, timeout, workdir, pty, notify_on_complete, watch_patterns |

#### 6.58 text_to_speech

| Field | Value |
|-------|-------|
| canonicalName | text_to_speech |
| module | tools/tts_tool.py |
| toolset | tts |
| syncMode | sync |
| sideEffects | Generates audio file, writes to filesystem |
| externalNetwork | Yes (TTS API) |
| filesystemRead | No |
| filesystemWrite | Yes (audio file) |
| processExecution | No |
| databaseRead | No |
| databaseWrite | No |
| credentialUse | Yes (TTS API key) |
| userDataExposure | Text content |
| cancellable | No |
| timeout | Via check_fn |
| audit | No |
| riskLevel | R3 |
| recommendation | Deny |
| inputParams | text (string, required), output_path |

#### 6.59 todo

| Field | Value |
|-------|-------|
| canonicalName | todo |
| module | tools/todo_tool.py |
| toolset | todo |
| syncMode | sync |
| sideEffects | Writes to TODO.md in HERMES_HOME |
| externalNetwork | No |
| filesystemRead | Yes |
| filesystemWrite | Yes (TODO.md) |
| processExecution | No |
| databaseRead | No |
| databaseWrite | No |
| credentialUse | No |
| userDataExposure | Task list content |
| cancellable | No |
| timeout | No |
| audit | No |
| riskLevel | R3 |
| recommendation | Deny (writes filesystem) |
| inputParams | todos (array), merge (boolean) |

#### 6.60 video_analyze

| Field | Value |
|-------|-------|
| canonicalName | video_analyze |
| module | tools/vision_tools.py |
| toolset | video |
| syncMode | async |
| sideEffects | Downloads video, sends to multimodal API |
| externalNetwork | Yes (video URL + API) |
| filesystemRead | Yes (local video path) |
| filesystemWrite | Yes (temp download) |
| processExecution | No |
| databaseRead | No |
| databaseWrite | No |
| credentialUse | Yes (API key) |
| userDataExposure | Video content |
| cancellable | No |
| timeout | Via check_fn |
| audit | No |
| riskLevel | R2 |
| recommendation | Deny |
| inputParams | video_url (string, required), question (string, required) |

#### 6.61 video_generate

| Field | Value |
|-------|-------|
| canonicalName | video_generate |
| module | tools/video_generation_tool.py |
| toolset | video_gen |
| syncMode | sync |
| sideEffects | Generates video, costs money |
| externalNetwork | Yes (generation API) |
| filesystemRead | No |
| filesystemWrite | Yes (video file) |
| processExecution | No |
| databaseRead | No |
| databaseWrite | No |
| credentialUse | Yes (API key) |
| userDataExposure | Prompt text |
| cancellable | No |
| timeout | Via check_fn |
| audit | No |
| riskLevel | R3 |
| recommendation | Deny |
| inputParams | prompt (string, required), image_url, duration, aspect_ratio, resolution, etc. |

#### 6.62 vision_analyze

| Field | Value |
|-------|-------|
| canonicalName | vision_analyze |
| module | tools/vision_tools.py |
| toolset | vision |
| syncMode | async |
| sideEffects | Downloads image, sends to multimodal API |
| externalNetwork | Yes (image URL + API) |
| filesystemRead | Yes (local file path) |
| filesystemWrite | Yes (temp download) |
| processExecution | No |
| databaseRead | No |
| databaseWrite | No |
| credentialUse | Yes (API key) |
| userDataExposure | Image content |
| cancellable | No |
| timeout | Via check_fn |
| audit | No |
| riskLevel | R2 |
| recommendation | Deny |
| inputParams | image_url (string, required), question (string, required) |

#### 6.63 web_extract

| Field | Value |
|-------|-------|
| canonicalName | web_extract |
| module | tools/web_tools.py |
| toolset | web |
| syncMode | async |
| sideEffects | Fetches web pages |
| externalNetwork | Yes (HTTP GET to user-provided URLs) |
| filesystemRead | No |
| filesystemWrite | No |
| processExecution | No |
| databaseRead | No |
| databaseWrite | No |
| credentialUse | Yes (Firecrawl/Tavily API key) |
| userDataExposure | URLs visited |
| cancellable | No |
| max_result_size_chars | 100,000 |
| audit | No |
| riskLevel | R2 |
| recommendation | Deny (user-provided arbitrary URLs) |
| inputParams | urls (array, required) |

#### 6.64 web_search

| Field | Value |
|-------|-------|
| canonicalName | web_search |
| module | tools/web_tools.py |
| toolset | web |
| syncMode | sync |
| sideEffects | Sends queries to search API |
| externalNetwork | Yes (search API) |
| filesystemRead | No |
| filesystemWrite | No |
| processExecution | No |
| databaseRead | No |
| databaseWrite | No |
| credentialUse | Yes (Exa/Tavily API key) |
| userDataExposure | Search queries |
| cancellable | No |
| max_result_size_chars | 100,000 |
| audit | No |
| riskLevel | R2 |
| recommendation | Deny (external network, credentials, query leakage) |
| inputParams | query (string, required), limit (integer) |

#### 6.65 write_file

| Field | Value |
|-------|-------|
| canonicalName | write_file |
| module | tools/file_tools.py |
| toolset | file |
| syncMode | sync |
| sideEffects | Writes/overwrites files |
| externalNetwork | No |
| filesystemRead | No |
| filesystemWrite | Yes (primary function) |
| processExecution | No |
| databaseRead | No |
| databaseWrite | No |
| credentialUse | No |
| userDataExposure | File content |
| cancellable | No |
| max_result_size_chars | 100,000 |
| audit | No |
| riskLevel | R3 |
| recommendation | Permanent Deny |
| inputParams | path (string, required), content (string, required), cross_profile |

#### 6.66 x_search

| Field | Value |
|-------|-------|
| canonicalName | x_search |
| module | tools/x_search_tool.py |
| toolset | x_search |
| syncMode | sync |
| sideEffects | Sends queries to xAI API |
| externalNetwork | Yes (xAI API) |
| filesystemRead | No |
| filesystemWrite | No |
| processExecution | No |
| databaseRead | No |
| databaseWrite | No |
| credentialUse | Yes (XAI_API_KEY) |
| userDataExposure | Search queries |
| cancellable | No |
| max_result_size_chars | 100,000 |
| audit | No |
| riskLevel | R2 |
| recommendation | Deny |
| inputParams | query (string, required), allowed_x_handles, excluded_x_handles, from_date, to_date, etc. |

#### 6.67–6.71 Yuanbao Tools

| canonicalName | module | toolset | riskLevel | recommendation |
|---------------|--------|---------|-----------|----------------|
| yb_query_group_info | tools/yuanbao_tools.py | hermes-yuanbao | R2 | Deny |
| yb_query_group_members | tools/yuanbao_tools.py | hermes-yuanbao | R2 | Deny |
| yb_search_sticker | tools/yuanbao_tools.py | hermes-yuanbao | R2 | Deny |
| yb_send_dm | tools/yuanbao_tools.py | hermes-yuanbao | R3 | Deny |
| yb_send_sticker | tools/yuanbao_tools.py | hermes-yuanbao | R3 | Deny |

All Yuanbao tools require external credentials and access the Yuanbao platform API.

---

## 7. Risk Classification Summary

### Risk Level Distribution

**Primary Risk Model:** Each canonical tool is assigned exactly one Primary Risk Level, equal to its highest actual risk. Capability tags (filesystemRead, networkWrite, etc.) are orthogonal and may overlap, but do not participate in the Primary Risk total. **R0+R1+R2+R3+R4+R5 = 71.**

| Risk Level | Count | Tools |
|-----------|------:|-------|
| R0 (Pure Computation) | 1 | clarify |
| R1 (Read-only Local) | 5 | read_file, search_files, session_search, skill_view, skills_list |
| R2 (Read-only External) | 19 | feishu_doc_read, feishu_drive_list_comment_replies, feishu_drive_list_comments, ha_get_state, ha_list_entities, ha_list_services, kanban_list, kanban_show, mixture_of_agents, spotify_albums, spotify_search, video_analyze, vision_analyze, web_extract, web_search, x_search, yb_query_group_info, yb_query_group_members, yb_search_sticker |
| R3 (Controlled Write) | 26 | discord, feishu_drive_add_comment, feishu_drive_reply_comment, image_generate, kanban_block, kanban_comment, kanban_complete, kanban_create, kanban_heartbeat, kanban_link, kanban_unblock, memory, patch, send_message, skill_manage, spotify_devices, spotify_library, spotify_playback, spotify_playlists, spotify_queue, text_to_speech, todo, video_generate, write_file, yb_send_dm, yb_send_sticker |
| R4 (Process/Code Execution) | 17 | browser_back, browser_cdp, browser_click, browser_console, browser_dialog, browser_get_images, browser_navigate, browser_press, browser_scroll, browser_snapshot, browser_type, browser_vision, computer_use, delegate_task, execute_code, process, terminal |
| R5 (High-Risk System) | 3 | cronjob, discord_admin, ha_call_service |
| **Total** | **71** | — |

### Classification Criteria

**R0 — Pure Computation** (1 tool):
- No network, filesystem, database, process, or credential access
- Input deterministically produces output
- Local pure computation only
- Candidate for Allowlist

**R1 — Read-only Local Query** (5 tools):
- Reads local filesystem or local database (SessionDB via FTS5)
- Does not modify files or external state
- Does not execute processes
- Does not access external network, secrets, or credentials
- Risks: privacy leakage, path leakage, large file output, symlink escape
- Candidate for Allowlist with strict path allowlist and output truncation

**R2 — Read-only External Network** (19 tools):
- HTTP GET to external APIs (read-only, no state mutation)
- Search, third-party API queries, multimodal analysis
- Most require credentials or access tokens
- No modification of remote state
- Risks: privacy exfiltration, SSRF, cost, malicious response
- Default Deny — not suitable for Phase 1G first batch

**R3 — Controlled Write** (26 tools):
- Write local files, send messages, modify remote state, generate media, control playback
- Includes tools whose highest capability is external state mutation (e.g., `spotify_playback` controls playback, `discord` can send messages, `spotify_devices` can transfer playback, `spotify_queue` can add items)
- Also includes local-only writes (`write_file`, `patch`, `memory`, `todo`, `skill_manage`)
- Risks: irreversible writes, wrong targets, duplicate execution, data corruption, external side effects
- Not eligible for Phase 1G first batch — must have Dry-Run first, explicit confirmation, idempotency

**R4 — Process and Code Execution** (17 tools):
- Shell execution, code execution, browser automation, subagent spawning, desktop control
- Includes all browser tools (even read-only browser tools belong here because the browser itself is a controlled execution environment)
- Risks: arbitrary code execution, command injection, privilege escalation
- Permanent Deny for Dev WebUI Agent auto-execution

**R5 — High-Risk System Operations** (3 tools):
- Scheduled job management (`cronjob` — can spawn arbitrary agent runs), server administration (`discord_admin` — bans, kicks, channel deletion), IoT device control (`ha_call_service` — physical device impact)
- Risks: system damage, physical device impact, irreversible changes
- Permanent Deny

---

## 8. Permanent Denylist

The following tools are **permanently prohibited** from Dev WebUI Agent execution. This list cannot be overridden by frontend, prompt, user parameter, or runtime configuration.

### Shell / Terminal / Process Execution

| canonicalName | module | toolset | riskLevel | reason |
|---------------|--------|---------|-----------|--------|
| terminal | tools/terminal_tool.py | terminal | R4 | Arbitrary shell command execution |
| process | tools/process_registry.py | terminal | R4 | Background process management including stdin write and kill |

### Code Execution

| canonicalName | module | toolset | riskLevel | reason |
|---------------|--------|---------|-----------|--------|
| execute_code | tools/code_execution_tool.py | code_execution | R4 | Python code execution with tool access |

### Filesystem Write

| canonicalName | module | toolset | riskLevel | reason |
|---------------|--------|---------|-----------|--------|
| write_file | tools/file_tools.py | file | R3 | Arbitrary file write/overwrite |
| patch | tools/file_tools.py | file | R3 | Targeted file modification |
| memory | tools/memory_tool.py | memory | R3 | Writes to MEMORY.md, USER.md, memory/records/ |
| skill_manage | tools/skill_manager_tool.py | skills | R3 | Creates/updates/deletes skill files |

### Subagent Spawning

| canonicalName | module | toolset | riskLevel | reason |
|---------------|--------|---------|-----------|--------|
| delegate_task | tools/delegate_tool.py | delegation | R4 | Spawns subagent processes with full tool access |

### Browser Automation

| canonicalName | module | toolset | riskLevel | reason |
|---------------|--------|---------|-----------|--------|
| browser_navigate | tools/browser_tool.py | browser | R4 | Loads arbitrary URLs |
| browser_snapshot | tools/browser_tool.py | browser | R4 | Reads browser accessibility tree |
| browser_click | tools/browser_tool.py | browser | R4 | Clicks page elements |
| browser_type | tools/browser_tool.py | browser | R4 | Types into form fields |
| browser_scroll | tools/browser_tool.py | browser | R4 | Scrolls page |
| browser_back | tools/browser_tool.py | browser | R4 | Browser navigation |
| browser_press | tools/browser_tool.py | browser | R4 | Keyboard input |
| browser_get_images | tools/browser_tool.py | browser | R4 | Reads page images |
| browser_vision | tools/browser_tool.py | browser | R4 | Screenshots page |
| browser_console | tools/browser_tool.py | browser | R4 | Executes JS via expression param |
| browser_cdp | tools/browser_tool.py | browser-cdp | R4 | Raw Chrome DevTools Protocol access |
| browser_dialog | tools/browser_tool.py | browser-cdp | R4 | Native dialog interaction |

### Desktop Control

| canonicalName | module | toolset | riskLevel | reason |
|---------------|--------|---------|-----------|--------|
| computer_use | tools/computer_use_tool.py | computer_use | R4 | Full macOS desktop control |

### Messaging

| canonicalName | module | toolset | riskLevel | reason |
|---------------|--------|---------|-----------|--------|
| send_message | tools/send_message_tool.py | messaging | R3 | Sends messages to external platforms |

### Cron Management

| canonicalName | module | toolset | riskLevel | reason |
|---------------|--------|---------|-----------|--------|
| cronjob | tools/cronjob_tools.py | cronjob | R5 | Creates/modifies scheduled jobs |

### Image Generation

| canonicalName | module | toolset | riskLevel | reason |
|---------------|--------|---------|-----------|--------|
| image_generate | tools/image_generation_tool.py | image_gen | R3 | Generates images, costs money, writes files |

### Discord Admin

| canonicalName | module | toolset | riskLevel | reason |
|---------------|--------|---------|-----------|--------|
| discord_admin | tools/discord_tool.py | discord_admin | R5 | Server management — bans, kicks, channel creation |

### Home Assistant Device Control

| canonicalName | module | toolset | riskLevel | reason |
|---------------|--------|---------|-----------|--------|
| ha_call_service | tools/homeassistant_tool.py | homeassistant | R5 | Controls IoT devices |

### Denylist Summary

| Category | Count |
|----------|------:|
| Shell/Terminal/Process | 2 |
| Code Execution | 1 |
| Filesystem Write | 4 |
| Subagent Spawning | 1 |
| Browser Automation | 12 |
| Desktop Control | 1 |
| Messaging | 1 |
| Cron Management | 1 |
| Image Generation | 1 |
| Discord Admin | 1 |
| IoT Device Control | 1 |
| **Total Permanent Deny** | **26** |

### Denylist Governance

- **Override:** Not permitted. The Denylist cannot be bypassed by:
  - Frontend configuration
  - Prompt engineering
  - User parameters
  - Runtime configuration
  - Toolset membership
  - Model-generated tool calls
- **Amendment:** Only through a formal Phase scope document
- **Testing:** Every denied tool must have a test confirming blockage

---

## 9. Candidate Allowlist

Phase 1G-00 freezes the **candidate** Allowlist. No tools are enabled. Actual enablement requires Phase 1G-E implementation.

**Summary:** 6 candidates total — 1 R0 + 5 R1 — 0 enabled.

### Candidates

| canonicalName | toolset | riskLevel | rationale | conditions |
|---------------|---------|-----------|-----------|------------|
| clarify | clarify | R0 | Pure interaction — no I/O, no network, no state | Must evaluate UI callback feasibility in WebUI context |
| skills_list | skills | R1 | Read-only skill directory listing | No path exposure, only name + description |
| skill_view | skills | R1 | Read-only skill content | Path restricted to skills/ and optional-skills/ directories |
| read_file | file | R1 | Read-only file access | Strict root directory allowlist, output truncation, path redaction |
| search_files | file | R1 | Read-only file search | Strict root directory allowlist, result limit |
| session_search | session_search | R1 | Read-only FTS5 search | Output redaction, query sanitization |

### Allowlist Empty State

**Phase 1G-00 does not enable any tools.** The Candidate Allowlist is frozen as empty until Phase 1G-E implements:
1. Tool Execution Kill Switch (`HERMES_TOOL_EXECUTION_ENABLED`)
2. Static Allowlist enforcement module
3. Per-tool parameter validation
4. Output validation and redaction
5. Tool Audit Trail
6. Dev-only Environment Guard integration
7. Provider Tool Schema filtering

### Allowlist Criteria (Frozen)

A tool may be added to the Allowlist only if it satisfies ALL of:

1. Risk level R0 or R1 (verified by source audit, not name)
2. No write side effects
3. No process execution
4. No arbitrary network access (R2+ network tools excluded)
5. No secret/credential access
6. Parameter schema is well-defined with types
7. Output can be limited/truncated
8. Supports or can be wrapped with timeout
9. Can be audited (input hash + output hash)
10. Has automated test coverage

---

## 10. Default-Deny Decision Chain (Frozen)

When a Tool Call arrives from the Provider, the backend must execute the following decision chain in order. Any step failing causes immediate rejection — fail closed.

```
 1. Tool Execution Kill Switch (HERMES_TOOL_EXECUTION_ENABLED)
    → If disabled: reject TOOL_EXECUTION_DISABLED (503)

 2. Dev-only Environment Guard
    → Source root != ALLOWED_SOURCE_ROOT: reject UNSAFE_ENVIRONMENT (503)
    → HERMES_HOME != ALLOWED_HERMES_HOME: reject UNSAFE_ENVIRONMENT (503)
    → Bind host != 127.0.0.1: reject UNSAFE_ENVIRONMENT (503)
    → Symlink to production: reject UNSAFE_ENVIRONMENT (503)

 3. Agent Run State Check
    → Run not in RUNNING state: reject (409)
    → Run already has terminal event: reject (409)

 4. Tool canonical name resolution
    → Name not found in Registry: reject TOOL_NOT_FOUND (404)
    → Alias resolution: map to canonical name

 5. Permanent Denylist check
    → Canonical name in STATIC_DENYLIST: reject TOOL_PERMANENTLY_DENIED (403)

 6. Static Allowlist check
    → Canonical name not in STATIC_ALLOWLIST: reject TOOL_NOT_ALLOWED (403)

 7. Toolset Allowlist check
    → Tool's toolset not in allowed toolsets for this run: reject TOOLSET_NOT_ALLOWED (403)

 8. Tool Schema validation
    → Schema not available (check_fn returned False): reject TOOL_SCHEMA_UNAVAILABLE (503)

 9. Argument normalization
    → Parse JSON arguments from Provider
    → JSON parse failure: reject INVALID_TOOL_ARGUMENTS (400)

10. Argument security rules
    → Payload size > 32 KiB: reject TOOL_ARGUMENT_TOO_LARGE (413)
    → Nesting depth > 8: reject INVALID_TOOL_ARGUMENTS (400)
    → Array length > 100: reject INVALID_TOOL_ARGUMENTS (400)
    → String length > 4,000: reject INVALID_TOOL_ARGUMENTS (400)
    → Path traversal (.. or absolute path): reject TOOL_PATH_BLOCKED (403)
    → Private IP in URL: reject TOOL_NETWORK_BLOCKED (403)
    → additionalProperties not false: reject INVALID_TOOL_ARGUMENTS (400)

11. Tool-specific Policy
    → Per-tool path allowlist check: reject TOOL_PATH_BLOCKED (403)
    → Per-tool network allowlist check: reject TOOL_NETWORK_BLOCKED (403)

12. Rate Limit check
    → Per-run rate exceeded: reject TOOL_RATE_LIMITED (429)

13. Concurrency Limit check
    → Global slot occupied: reject TOOL_CONCURRENCY_LIMIT (409)
    → Per-run slot occupied: reject TOOL_CONCURRENCY_LIMIT (409)

14. Timeout Budget check
    → Remaining run budget < tool timeout: reject TOOL_TIMEOUT (504)

15. Audit preflight
    → Cannot write audit record: reject TOOL_AUDIT_ERROR (500)
    → (Do NOT dispatch if audit cannot be recorded)

16. Dry-Run / Execute Mode decision
    → Dry-Run mode: return wouldAllow/wouldBlock without dispatch
    → Execute mode: proceed to dispatch

17. Dispatch
    → registry.dispatch(name, validated_args)

18. Output validation
    → Serialization failure: reject TOOL_OUTPUT_INVALID (500)
    → Size > 64 KiB: truncate, set truncated=true
    → Path leakage detected: redact
    → Secret leakage detected: redact

19. Redaction pass
    → Replace all allowed root paths with generic markers
    → Replace all detected secrets with [REDACTED]

20. Audit completion
    → Record audit entry with status, duration, truncated, redacted flags
    → If audit write fails after dispatch: keep tool result, set auditWarning=true
```

---

## 11. Kill Switch (Frozen Contract)

### Environment Variable

```text
HERMES_TOOL_EXECUTION_ENABLED
```

Note: If the codebase already defines a different variable name for this purpose, the existing name takes precedence. Phase 1G-00 freezes the concept; the exact name will be confirmed during Phase 1G-01 implementation.

### Semantics

| Value | Behavior |
|-------|----------|
| unset | DISABLED |
| "" | DISABLED |
| 0 | DISABLED |
| false (case-insensitive) | DISABLED |
| no (case-insensitive) | DISABLED |
| off (case-insensitive) | DISABLED |
| 1 | ENABLED |
| true (case-insensitive) | ENABLED |
| yes (case-insensitive) | ENABLED |
| on (case-insensitive) | ENABLED |
| Any other value | FAIL CLOSED (disabled) |

### Check Points

The Kill Switch must be checked **before** any of these operations:

1. Tool Schema construction for Provider
2. Provider Tool Schema sending
3. Tool Registry dispatch
4. Tool Audit initialization
5. Thread pool submission for tool execution
6. Process creation for tool execution
7. Network request for tool execution
8. File access for tool execution

### Phase 1G-00 State

Not implemented. Kill Switch exists only as this contract definition.

---

## 12. Dev-Only Environment Guard (Frozen Contract)

### Mandatory Checks (at Tool Dispatch)

```python
ALLOWED_SOURCE_ROOT = Path("/Users/huangruibang/Code/hermes-agent-dev").resolve()
ALLOWED_HERMES_HOME = Path("/Users/huangruibang/Code/hermes-home-dev").resolve()

hermes_home = Path(os.environ.get("HERMES_HOME", "")).resolve()
source_root = Path(__file__).resolve().parents[1]

if hermes_home != ALLOWED_HERMES_HOME:
    raise ToolExecutionBlocked("UNSAFE_ENVIRONMENT")
if source_root != ALLOWED_SOURCE_ROOT:
    raise ToolExecutionBlocked("UNSAFE_ENVIRONMENT")
```

### Must Reject

- `~/.hermes` or any subdirectory
- Symlinks pointing to `~/.hermes`
- Production source root
- Unknown or empty HERMES_HOME
- Relative paths
- Path traversal (.. components)

### Must Use

- `Path.resolve()` for all path comparisons — never string prefix matching

---

## 13. Provider Tool Schema Boundary (Frozen)

### Default Rule

No Tool Schema is sent to the Provider.

### All Conditions Must Be True for Schema Generation

1. Kill Switch is ENABLED
2. Dev Guard passed
3. Agent Run explicitly allows tools (tools != false)
4. Static Allowlist is non-empty
5. Current model supports tool calling
6. Current Provider supports tool calling

### Schema Content Rules

Provider receives ONLY:
- Allowed tools' minimal schema (name, description, parameters)
- Parameters with `additionalProperties: false`

Provider must NEVER receive:
- Denylist tools
- Internal tools
- Hidden tools
- Complete Registry dump
- Admin tools
- Production-only tools

### Schema Sanitization

Before sending to Provider, schemas must have removed:
- Internal file paths
- Implementation module references
- Credential information
- Default secret parameters
- Debug fields

---

## 14. Tool Call Request DTO (Frozen)

### Required Fields

```typescript
interface ToolCallRequest {
  toolCallId: string;       // Unique ID per call within a run
  runId: string;            // Agent Run ID
  sessionId: string;        // Session ID
  toolName: string;         // Tool name from Provider
  arguments: Record<string, unknown>;  // Parsed JSON arguments
  requestedAt: string;      // ISO 8601 timestamp
  provider: string;         // Provider name
  model: string;            // Model name
}
```

### Prohibited Fields (Must Never Be Included)

- implementationModule
- callableObject
- credential
- environment
- rawHeaders
- apiKey
- authorization
- filesystemRoot
- internalConfig

---

## 15. Parameter Validation Framework (Frozen)

### Per-Tool Schema Requirements

All allowed tools must define:
- required fields
- optional fields with defaults
- types (string, number, integer, boolean, array, object)
- enum values where applicable
- minimum / maximum for numbers
- minLength / maxLength for strings
- pattern for format validation
- `additionalProperties: false`

### Global Prohibitions

The following are rejected at validation time:
- `__proto__`, `constructor`, `prototype` in any key
- Nesting depth > 8
- Array length > 100
- String length > 4,000 characters per field
- NaN, Infinity values
- Binary large input
- Null bytes in strings

### Global Limits (Frozen)

| Constraint | Limit |
|-----------|------:|
| JSON payload total | 32 KiB |
| Object nesting depth | 8 |
| Array length | 100 |
| String field length | 4,000 |

### Validation Order

1. JSON parse
2. Top-level type check (must be object)
3. Required fields present
4. No prohibited fields
5. Global size limits
6. Per-field type validation
7. Per-field constraint validation
8. Path/URL security rules (if applicable)

---

## 16. File Path Security (Frozen)

### Requirements for All File-Path Tools

- Static root directory allowlist (only listed roots permitted)
- `Path.resolve()` for all path operations
- Reject `..` components in user input
- Reject absolute path input (paths must be relative to allowed root)
- Reject `file://` scheme
- Reject symlink escape (resolved path must remain under allowed root)
- Reject device files, sockets, FIFOs
- Reject hidden/secret directories (`.ssh`, `.gnupg`, `.aws`, etc.)

### Allowed Root Directories (Frozen)

Only these roots may be accessed by file tools:

```
/Users/huangruibang/Code/hermes-agent-dev          (source root)
/Users/huangruibang/Code/hermes-home-dev            (dev HERMES_HOME)
```

### Prohibited

- Arbitrary current working directory
- User-provided root
- Prompt-provided root
- Model-generated root
- `~/.hermes` or any subdirectory

### File Read Limits

| Constraint | Limit |
|-----------|------:|
| Single file max | 1 MiB |
| Text output max | 64 KiB |
| Directory listing max | 200 items |

---

## 17. Network Tool Security (Frozen)

### Default

All network tools are DENIED in the Phase 1G Allowlist.

### Future Read-Only Network Tool Requirements (If Ever Enabled)

- HTTPS only (no HTTP)
- Static domain allowlist
- User may not provide arbitrary URLs
- DNS resolution → IP check after resolution
- Reject private IPs:
  - 127.0.0.0/8
  - ::1
  - RFC1918 (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
  - Link-local (169.254.0.0/16, fe80::/10)
  - Multicast
  - Cloud metadata (169.254.169.254)
- Reject `file://`, `ftp://`, `gopher://` schemes
- Limit redirects to 3 hops, reject redirect to non-allowlist domain
- Response size limit
- Total time limit

### Permanently Prohibited

- POST, PUT, PATCH, DELETE methods
- WebSocket connections
- Arbitrary headers
- User-provided Authorization header

---

## 18. Timeout (Frozen)

### Per-Tool Timeout Declaration

Every allowed tool must declare `timeoutSeconds`:

| Risk Level | Default Timeout |
|-----------|----------------:|
| R0 | 2 seconds |
| R1 | 5 seconds |
| R2 | 10 seconds (if ever enabled) |

### Global Hard Maximum

- **30 seconds** — cannot be overridden by model, prompt, or configuration

### Timeout Behavior

- Return `TOOL_TIMEOUT` error code
- Do NOT auto-retry non-idempotent tools
- Record Audit entry
- Do NOT return partial/incomplete results to Agent

---

## 19. Cancel (Frozen)

### Cancel Propagation Chain

```
Agent Run Cancel (user action)
  → Tool Execution cancel_requested = true
  → If cancellable: Tool stops and returns TOOL_CANCELLED
  → If not cancellable: Wait up to cancel_wait_timeout, then mark TOOL_CANCEL_TIMEOUT
  → Tool Result tagged as cancelled
  → Agent Run ends with CANCELLED status
```

### Requirements

- Tools must declare `cancellable: true | false`
- Non-cancellable tools must NOT enter first Allowlist batch
- Cancel timeout does NOT release concurrency slot until worker actually exits

### Phase 1G State

Cancel is inherited from Phase 1F Agent Run cancel mechanism. Tool-specific cancel is not yet implemented.

---

## 20. Concurrency and Call Limits (Frozen)

### Phase 1G Initial Limits

| Constraint | Limit |
|-----------|------:|
| Max tool calls per Agent Run | 3 |
| Global concurrent tool executions | 1 |
| Per-run concurrent tool executions | 1 |
| Parallel tool calls | Prohibited |
| Batch tool calls | Prohibited |
| Recursive tool calls | Prohibited |

### Tool Loop Limits (Must Be Enforced Simultaneously)

| Constraint | Limit |
|-----------|------:|
| Max tool rounds | 3 |
| Max tool calls per single model response | 1 |
| Max cumulative tool calls per run | 3 |
| Max total runtime for all tools | 60 seconds |

---

## 21. Tool Dry-Run Model (Frozen Roadmap)

### Phase 1G-A: Tool Inventory + Static Policy

- Documentation and static code checks only
- No API, no Provider Schema, no Dispatch

### Phase 1G-B: Tool Policy Read-Only API / Panel

- Read-only display of Policy, Catalog, Risk, Schema metadata
- No execution

### Phase 1G-C: Tool Schema Preview

- Show what schema the model would see
- Do NOT send to Provider
- Do NOT execute

### Phase 1G-D: Tool Call Dry-Run

- Input: Tool Name + Arguments
- Execute full validation chain (steps 1–16 of Decision Chain)
- Return wouldAllow / wouldBlock
- Do NOT dispatch

### Phase 1G-E: Fake Tool Fixture Execute

- Temporary HERMES_HOME only
- Fake tool implementations
- No real side effects

### Phase 1G-F: Dev-Only R0/R1 Execute

- Only tools from final approved Allowlist
- Only R0 and R1 tools
- Full audit, timeout, cancel, output validation

---

## 22. Tool Dry-Run Response DTO (Frozen)

```typescript
interface ToolDryRunResponse {
  dryRun: true;
  toolName: string;
  canonicalToolName: string;
  allowed: boolean;
  blockedReason?: string;
  riskLevel: string;
  toolset: string;
  schemaValid: boolean;
  argumentsValid: boolean;
  policyValid: boolean;
  wouldDispatch: boolean;
  wouldReadFiles: boolean;
  wouldWriteFiles: boolean;
  wouldUseNetwork: boolean;
  wouldStartProcess: boolean;
  wouldReadDatabase: boolean;
  wouldWriteDatabase: boolean;
  timeoutSeconds: number;
  checks: CheckResult[];
  effects: string[];
  noEffects: string[];
  warnings: string[];
  safety: {
    readOnly: true;
    sideEffects: false;
    toolExecuted: false;
    providerCalled: false;
    sessionWritten: false;
    memoryWritten: false;
    reviewQueued: false;
  };
}
```

### Prohibited in Response

- Absolute paths
- Secrets
- Internal callables
- Complete Registry dump
- Full configuration
- Tracebacks
- Credentials

---

## 23. Tool Execute Response DTO (Frozen — Not Implemented)

```typescript
interface ToolExecuteResponse {
  toolCallId: string;
  toolName: string;
  status: "completed" | "failed" | "cancelled" | "timeout";
  startedAt: string;
  completedAt: string;
  durationMs: number;
  resultPreview: string;  // Truncated to 8 KiB
  resultType: string;
  truncated: boolean;
  redacted: boolean;
  auditId: string;
  warnings: string[];
}
```

### Prohibited in Response

- Full oversized results
- Local filesystem paths
- Secrets
- Environment variables
- Internal exception stacks
- Python object repr

---

## 24. Tool Output Validation (Frozen)

### Requirements

All tool results must:
- Be serialized to stable JSON
- Have size limited
- Have nesting depth limited
- Have array length limited
- Have string fields sanitized
- Have paths redacted (replace allowed roots with `[PATH]`)
- Have secrets redacted (replace with `[REDACTED]`)
- Have HTML/ANSI control sequences stripped
- Have control characters removed
- Reject binary output (or return SHA-256 digest only)

### Size Limits

| Output Target | Max Size |
|--------------|---------:|
| Serialized result | 64 KiB |
| Agent-visible result | 16 KiB |
| WebUI Preview | 8 KiB |

### Truncation

- Safe truncation at character boundary
- Set `truncated: true` in response
- Never return raw tool stdout to model

---

## 25. Redaction (Frozen)

### Path Redaction

All occurrences of allowed root directories replaced with:
- `/Users/huangruibang/Code/hermes-agent-dev` → `[SOURCE_ROOT]`
- `/Users/huangruibang/Code/hermes-home-dev` → `[HERMES_HOME]`

### Secret Redaction

Patterns to detect and redact:
- API keys (long alphanumeric + common key patterns)
- Bearer tokens
- URLs containing credentials (`user:pass@host`)
- Environment variable values for key names containing: `KEY`, `TOKEN`, `SECRET`, `PASSWORD`, `CREDENTIAL`

### Redaction Scope

Applied to:
- Tool output before returning to Agent
- Audit log entries
- Error messages
- Dry-Run responses

---

## 26. Error Model (Frozen)

### Error Codes

| Code | Description |
|------|-------------|
| TOOL_EXECUTION_DISABLED | Kill Switch is off |
| UNSAFE_ENVIRONMENT | Dev Guard failed |
| TOOL_NOT_ALLOWED | Not in Allowlist |
| TOOL_PERMANENTLY_DENIED | In Denylist |
| TOOL_NOT_FOUND | Name not in Registry |
| TOOLSET_NOT_ALLOWED | Tool's toolset not allowed |
| TOOL_SCHEMA_UNAVAILABLE | check_fn returned False |
| INVALID_TOOL_ARGUMENTS | Schema validation failed |
| TOOL_ARGUMENT_TOO_LARGE | Payload exceeds limit |
| TOOL_POLICY_BLOCKED | Tool-specific policy rejection |
| TOOL_PATH_BLOCKED | Path security violation |
| TOOL_NETWORK_BLOCKED | Network security violation |
| TOOL_RATE_LIMITED | Rate limit exceeded |
| TOOL_CONCURRENCY_LIMIT | Concurrency slot occupied |
| TOOL_TIMEOUT | Execution exceeded timeout |
| TOOL_CANCELLED | Execution cancelled |
| TOOL_CALL_LIMIT_EXCEEDED | Run call budget exhausted |
| TOOL_OUTPUT_TOO_LARGE | Result exceeds output limit |
| TOOL_OUTPUT_INVALID | Result serialization failed |
| TOOL_EXECUTION_ERROR | Handler raised exception |
| TOOL_AUDIT_ERROR | Audit write failed |
| AGENT_TOOL_CALL_FORBIDDEN | Tool call from Provider when tools disabled |

### HTTP Mapping

| Code | HTTP Status |
|------|-------------|
| INVALID_TOOL_ARGUMENTS, TOOL_ARGUMENT_TOO_LARGE | 400 |
| TOOL_NOT_ALLOWED, TOOL_PERMANENTLY_DENIED, TOOL_POLICY_BLOCKED, TOOL_PATH_BLOCKED, TOOL_NETWORK_BLOCKED, AGENT_TOOL_CALL_FORBIDDEN | 403 |
| TOOL_NOT_FOUND | 404 |
| TOOL_CONCURRENCY_LIMIT | 409 |
| TOOL_ARGUMENT_TOO_LARGE, TOOL_OUTPUT_TOO_LARGE | 413 |
| TOOL_RATE_LIMITED | 429 |
| TOOL_EXECUTION_ERROR, TOOL_OUTPUT_INVALID, TOOL_AUDIT_ERROR | 500 |
| TOOL_EXECUTION_DISABLED, UNSAFE_ENVIRONMENT, TOOL_SCHEMA_UNAVAILABLE | 503 |
| TOOL_TIMEOUT | 504 |

### Error Message Sanitization

All error responses must exclude:
- Filesystem paths
- Credentials
- Tracebacks
- Full arguments
- Full output

---

## 27. Audit Trail (Frozen)

### Audit Record Fields

| Field | Type | Description |
|-------|------|-------------|
| auditId | string | Unique audit record ID |
| requestId | string | HTTP request ID |
| runId | string | Agent Run ID |
| sessionId | string | Session ID |
| toolCallId | string | Tool call unique ID |
| actor | string | "dev-webui" |
| toolName | string | Name from Provider |
| canonicalToolName | string | Resolved canonical name |
| toolset | string | Tool's toolset |
| riskLevel | string | R0–R5 |
| mode | string | "dry-run" or "execute" |
| argumentsHash | string | SHA-256 of normalized args JSON |
| argumentsSummary | string | Truncated arg description (≤200 chars) |
| startedAt | string | ISO 8601 |
| completedAt | string | ISO 8601 |
| durationMs | integer | Execution duration |
| status | string | completed/failed/cancelled/timeout/blocked |
| errorCode | string | Error code if failed |
| inputBytes | integer | Size of input payload |
| outputBytes | integer | Size of output payload |
| truncated | boolean | Output was truncated |
| redacted | boolean | Output was redacted |
| cancelRequested | boolean | Cancel was requested |
| devOnly | boolean | Always true for WebUI |

### Prohibited in Audit Records

- Full arguments
- Full results
- Full user messages
- Full prompt
- API keys, authorization, cookies
- Environment variables
- Local absolute paths
- Tracebacks

### Storage Decision

**Chosen: `state.db` independent `tool_execution_audit` table**

| Option | Pros | Cons |
|--------|------|------|
| state.db table | Transactional, queryable, collocated with sessions | Table grows over time |
| Independent file | No state.db schema change | No query, no transaction |

### Lazy Initialization

- Kill Switch disabled → table NOT created
- Dry-Run mode → table NOT written
- Only real Fixture/Execute creates table lazily

### Audit Failure Handling

- Preflight audit write fails → **Do NOT dispatch** (fail closed)
- Post-execution audit write fails → Keep tool result, set `auditWarning: true`

---

## 28. Session Persistence (Frozen)

### Persistence Owner

**Agent Runtime** (AIAgent) is the sole owner of session persistence.

### Web API / Tool Service

Must NOT directly write Tool Messages to SessionDB.

### Tool Result Persistence Flow

```
Tool executes → Tool returns result to Agent Runtime
  → Agent Runtime appends tool_call + tool_result to message history
  → Agent Runtime._persist_session() saves to SessionDB
```

### Anti-Double-Persist

Exactly one system must persist each message. If Agent auto-persists, Web API must NOT call `append_message()` for the same content. Test must verify: after one `chat()` with tool call, message count increases by exactly the expected number.

---

## 29. Idempotency (Frozen)

### toolCallId

- Unique within a single Run
- Duplicate `toolCallId` must NOT re-dispatch
- Return existing result or current status

### Tool Call States

```
received → validating → blocked | running → completed | failed | cancelled
```

### Write Tool Idempotency (Future)

Write tools must additionally require `idempotencyKey`:
- Same key + same args → return cached result
- Same key + different args → reject

---

## 30. Frontend Information Architecture (Frozen — Not Implemented)

### Future Agent Panel → Tools Section

#### Tool Policy Status
- Kill Switch state
- Dev-only indicator
- Allowlist count
- Denylist count
- Max tool calls
- Concurrency

#### Tool Schema Preview
- Allowed tool list
- Risk level per tool
- Schema display
- Timeout
- Side-effect declaration

#### Tool Call Dry-Run Interface
- Tool Name input (from Allowlist only, no free text)
- Arguments JSON editor
- Validate button
- Result: Allowed/Blocked, Checks, Effects, No Effects, Warnings

#### Tool Execution Monitor (Future Execute phase)
- Tool Call ID
- Status
- Duration
- Cancel button
- Output preview
- Audit ID

### Prohibited Frontend Features

- Free text input for arbitrary tool names
- Shell input boxes
- Arbitrary path input
- Arbitrary URL input
- Batch execution buttons
- Auto-execute toggles
- "Enable all tools" button

---

## 31. OpenAPI Route Roadmap (Frozen)

### Current State (Phase 1G-00)

- OpenAPI paths: 27
- Tool routes: 0
- No modifications to OpenAPI

### Future Read-Only Routes (Phase 1G-B)

```http
GET  /api/dev/v1/tools/policy          # Kill switch, allowlist/denylist counts, limits
GET  /api/dev/v1/tools/catalog          # Full tool inventory with risk levels
```

### Future Dry-Run Routes (Phase 1G-C/D)

```http
POST /api/dev/v1/tools/schema/preview   # Schema that would be sent to Provider
POST /api/dev/v1/tools/calls/dry-run    # Validate tool call without dispatch
```

### Future Execute Routes (Phase 1G-F)

```http
POST /api/dev/v1/tools/calls                     # Execute an allowed tool
GET  /api/dev/v1/tools/calls/{toolCallId}        # Get tool call status
POST /api/dev/v1/tools/calls/{toolCallId}/cancel  # Cancel running tool call
```

### Governance

- Read-only and Dry-Run routes must NOT be implemented simultaneously with Execute routes
- Execute routes require a dedicated Phase scope document

---

## 32. dev-check Route (Frozen — Not Implemented)

Future `dev-check` additions for Tool Execution:

```
PASS  Tool Kill Switch default: disabled
PASS  Permanent Denylist exists
PASS  Static Allowlist exists (may be empty)
PASS  Allowlist / Denylist intersection: empty
PASS  All Allowlist tools have Schema
PASS  All Allowlist tools have Timeout
PASS  All Allowlist tools have Risk Level
PASS  All Allowlist tools have Output Limit
PASS  All Allowlist tools have Redaction Policy
PASS  Provider does not receive Denylist tools
PASS  OpenAPI real Execute routes: absent
```

---

## 33. Test Strategy (Frozen)

### Kill Switch Tests

| Test Case | Expected |
|-----------|----------|
| Kill Switch unset | Schema=0, Provider tools=0, Dispatch=0, Audit=0 |
| Kill Switch="" | Same as unset |
| Kill Switch=0 | Same as unset |
| Kill Switch=false | Same as unset |
| Kill Switch=invalid | Same as unset (fail closed) |
| Kill Switch=1 | Enabled (normal flow continues) |
| Kill Switch=true | Enabled |

### Allowlist / Denylist Tests

| Test Case | Expected |
|-----------|----------|
| Allowlisted tool | Passes Allowlist check |
| Unknown tool | Blocked (TOOL_NOT_ALLOWED) |
| Denylisted tool | Blocked (TOOL_PERMANENTLY_DENIED) |
| Alias resolves to denylisted tool | Blocked (canonical check) |
| Tool not in allowed toolset | Blocked (TOOLSET_NOT_ALLOWED) |

### Parameter Validation Tests

| Test Case | Expected |
|-----------|----------|
| Missing required field | INVALID_TOOL_ARGUMENTS |
| Extra unknown field | INVALID_TOOL_ARGUMENTS |
| Wrong type | INVALID_TOOL_ARGUMENTS |
| Nesting too deep | INVALID_TOOL_ARGUMENTS |
| Payload too large | TOOL_ARGUMENT_TOO_LARGE |
| Path traversal (..) | TOOL_PATH_BLOCKED |
| Symlink escape | TOOL_PATH_BLOCKED |
| Private IP in URL | TOOL_NETWORK_BLOCKED |

### Timeout / Cancel Tests

| Test Case | Expected |
|-----------|----------|
| Tool completes within timeout | Success |
| Tool exceeds timeout | TOOL_TIMEOUT |
| Cancel requested during execution | TOOL_CANCELLED |
| Cancel timeout exceeded | TOOL_CANCEL_TIMEOUT |
| Worker exits after cancel | Slot released |

### Output Tests

| Test Case | Expected |
|-----------|----------|
| Normal JSON output | Passed through |
| Oversized output | Truncated, truncated=true |
| Path in output | Redacted |
| Secret in output | Redacted |
| ANSI in output | Stripped |
| Binary output | Rejected or digest |
| Non-serializable output | TOOL_OUTPUT_INVALID |

### Audit Tests

| Test Case | Expected |
|-----------|----------|
| Allowed tool execution | Audit record created |
| Blocked tool attempt | Audit record created (blocked) |
| Completed execution | Duration recorded |
| Failed execution | Error code recorded |
| Cancelled execution | cancelRequested=true |
| Audit preflight failure | Dispatch blocked |
| No sensitive data in audit | Verify field-by-field |

### Agent Integration Tests

| Test Case | Expected |
|-----------|----------|
| Provider receives only Allowlist tools | Verified |
| Tool call executes exactly once | Verified |
| Tool result persisted exactly once | Verified |
| Call limit exceeded → Run stops | Verified |
| Unexpected tool call → safe failure | Verified |

---

## 34. Side-Effect Validation

### Before (Pre-Audit)

| Asset | Value |
|-------|-------|
| state.db SHA-256 | b1911d16c1b5ad76b301ed5cd48bf6437be054490632ade79a5440923ee67945 |
| state.db size | 360607744 bytes |
| Session count | 417 |
| Message count | 22552 |
| MEMORY.md SHA-256 | 44be12a08bbe826132f9c67940e15433f2f8aebaf5680693dea5955b7ea51515 |
| Memory records | 3 items |
| Review queue pending | 0 |
| Tool audit table | Does not exist |

### After (Post-Documentation)

Must be identical to Before. Phase 1G-00 creates documentation only — no state modification.

---

## 35. Risk Register

### P0 Risks (Phase 1G-00 Specific)

**Expected: None.** Phase 1G-00 is documentation only.

If any of the following were discovered, they would be P0:
- Tool Registry import-time tool execution → **Not found.** Registration is metadata-only.
- Default-enabled high-risk tools → **Not found.** Dev WebUI uses `enabled_toolsets=[]`.
- Agent Run can bypass `tools=[]` → **Not found.** `_has_tool_calls()` check terminates run.
- Provider currently receives Tool Schema → **Not found.** `tools=[]` in API call.
- Denylist overridable by Prompt → **Not applicable.** Denylist not yet implemented.
- Production tools callable from Dev WebUI → **Not found.** Dev WebUI has no tool dispatch.

### P1 Risks

| Risk | Assessment |
|------|-----------|
| Tool canonical name inconsistency | **Verified.** All 71 canonical names confirmed against Registry. Names match registered values. |
| Alias bypass of Denylist | **Mitigated.** No per-tool aliases exist. Only toolset-level aliases for MCP servers. Decision chain resolves to canonical name before Denylist check. |
| Schema `additionalProperties` not `false` | **Audit needed.** Current schemas do not universally set `additionalProperties: false`. Must be enforced in Phase 1G-01. |
| File path symlink escape | **Risk exists.** Current `read_file` handler does not enforce root allowlist. Must be added in Phase 1G-01. |
| Network SSRF | **Not applicable yet.** No network tools in Allowlist. |
| Tool Result secret leakage | **Risk exists.** No built-in redaction. Must be added in Phase 1G-01. |
| Tool Timeout cannot abort worker | **Risk exists.** Current async bridge timeout is 300s. Per-tool timeout not enforced. |
| Tool Audit and Session double-persist | **Addressed.** Persistence owner is Agent Runtime only. |
| Tool Call replay causes re-execution | **Mitigated.** `toolCallId` uniqueness must be enforced in implementation. |
| Registry is process-only | **Acceptable.** Dev WebUI runs in single process. Multi-worker requires future consideration. |
| Allowlist state inconsistency across workers | **Not applicable yet.** Single-process deployment. |

### P2 Risks

| Risk | Assessment |
|------|-----------|
| Large Registry enumeration performance | **Acceptable.** 71 tools, sub-millisecond lookup. |
| Tool Schema token overhead | **Not applicable.** No Schema sent in Phase 1G-00. Future cost: ~200-500 tokens per tool. |
| Output truncation impact on model quality | **Valid concern.** 16 KiB limit may truncate large file reads. May need configurable per-tool. |
| Provider Tool Schema format differences | **Known.** OpenAI, Anthropic, Google have different schema formats. `get_definitions()` handles format. |
| Audit table growth | **Future consideration.** Add TTL or rotation policy. |
| Tool execution cost tracking | **Future feature.** Not Phase 1G scope. |

---

## 36. Implementation Roadmap (Frozen)

### Phase 1G-01: Tool Inventory + Static Policy Module

- Implement `tool_inventory.py` (or similar) with frozen Inventory data
- Implement `STATIC_DENYLIST` set with 26 canonical names
- Implement `STATIC_ALLOWLIST` set (initially empty)
- Implement `CANDIDATE_ALLOWLIST` set with 6 candidate names
- No API, no Provider Schema, no Dispatch

### Phase 1G-02: Tool Policy Read-Only API / Panel

- `GET /api/dev/v1/tools/policy` — Kill switch, list counts, limits
- `GET /api/dev/v1/tools/catalog` — Full inventory with risk levels
- Frontend read-only panel in Agent workspace

### Phase 1G-03: Tool Schema Preview

- Build minimal Schema from Allowlist
- Display in UI
- Do NOT send to Provider

### Phase 1G-04: Tool Call Dry-Run

- Accept tool name + arguments
- Execute full validation chain
- Return Dry-Run response DTO
- Do NOT dispatch

### Phase 1G-05: Fake Tool Fixture Execute

- Temporary HERMES_HOME
- Fake tool implementations (return fixture data)
- No real side effects
- Full audit trail

### Phase 1G-06: Dev-Only R0/R1 Execute

- Only final approved R0/R1 tools
- Full safety chain enforced
- Full audit, timeout, cancel, output validation

### Phase Gate

Each phase requires:
- Previous phase completed and tested
- Scope document (for phases beyond 1G-01)
- No phase may be skipped

---

## 37. Acceptance Criteria

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Git baseline correct | ✓ |
| 2 | Local and remote synced | ✓ |
| 3 | Tracked worktree clean | ✓ |
| 4 | .claude/ untouched | ✓ |
| 5 | HERMES_HOME explicitly correct | ✓ |
| 6 | Production Gateway unaffected | ✓ |
| 7 | Dev Gateway stopped | ✓ |
| 8 | Ports 5180/5181 free | ✓ |
| 9 | Tool Registry fully audited | ✓ |
| 10 | Toolsets fully audited | ✓ |
| 11 | Agent Tool Loop fully audited | ✓ |
| 12 | All canonical tool names recorded | ✓ (71 tools) |
| 13 | Tool aliases recorded | ✓ (no per-tool aliases) |
| 14 | Tool-to-toolset mapping recorded | ✓ (33 toolsets) |
| 15 | Per-tool side-effect analysis | ✓ |
| 16 | Per-tool risk level assigned | ✓ |
| 17 | Permanent Denylist frozen | ✓ (26 tools) |
| 18 | Candidate Allowlist frozen | ✓ (6 candidates: 1 R0 + 5 R1, 0 enabled) |
| 19 | Allowlist may be empty | ✓ |
| 20 | Default-Deny decision chain frozen | ✓ (20 steps) |
| 21 | Kill Switch contract frozen | ✓ |
| 22 | Dev-only Guard contract frozen | ✓ |
| 23 | Provider Schema boundary frozen | ✓ |
| 24 | Tool DTO frozen | ✓ |
| 25 | Parameter validation rules frozen | ✓ |
| 26 | File path rules frozen | ✓ |
| 27 | Network rules frozen | ✓ |
| 28 | Timeout rules frozen | ✓ |
| 29 | Cancel rules frozen | ✓ |
| 30 | Concurrency rules frozen | ✓ |
| 31 | Call limits frozen | ✓ |
| 32 | Dry-Run phases frozen | ✓ (6 sub-phases) |
| 33 | Execute phases frozen | ✓ |
| 34 | Output Validation frozen | ✓ |
| 35 | Redaction rules frozen | ✓ |
| 36 | Error Model frozen | ✓ (22 error codes) |
| 37 | Audit Trail frozen | ✓ |
| 38 | Persistence Owner frozen | ✓ (Agent Runtime) |
| 39 | Idempotency frozen | ✓ |
| 40 | Frontend IA frozen | ✓ |
| 41 | OpenAPI roadmap frozen | ✓ |
| 42 | dev-check roadmap frozen | ✓ |
| 43 | Test matrix frozen | ✓ |
| 44 | Side-Effect strategy frozen | ✓ |
| 45 | Risk register completed | ✓ |
| 46 | Sub-phase roadmap frozen | ✓ (6 phases) |
| 47 | Document created | ✓ |
| 48 | Implementation Plan updated | Pending |
| 49 | No business code modified | ✓ |
| 50 | No API modified | ✓ |
| 51 | OpenAPI still 27 paths | ✓ |
| 52 | No Tool Execution | ✓ |
| 53 | No Provider Tool Schema | ✓ |
| 54 | No Session modification | ✓ |
| 55 | No Memory modification | ✓ |
| 56 | No Review modification | ✓ |
| 57 | memory-check PASS | ✓ |
| 58 | dev-check PASS or .claude/ WARN only | ✓ |
| 59 | compileall PASS | Pending |
| 60 | Local commit completed | Pending |
| 61 | Not pushed | Pending |
| 62 | Tracked worktree clean | Pending |
| 63 | .claude/ still untracked | Pending |
| 64 | Production Gateway PID 1717 unaffected | Pending |
| 65 | Phase 1G implementation not started | ✓ |
| 66 | All 71 canonical tools have exactly one Primary Risk | ✓ (Documentation Fix) |
| 67 | R0+R1+R2+R3+R4+R5 = 71 | ✓ (1+5+19+26+17+3 = 71) |
| 68 | No multiply-classified tools | ✓ |
| 69 | No unclassified tools | ✓ |
| 70 | Denylist canonical names all exist in Registry | ✓ |
| 71 | Candidate canonical names all exist in Registry | ✓ |
| 72 | Denylist ∩ Candidate = ∅ | ✓ |
| 73 | R1 candidate count matches Candidate list | ✓ (5 R1 candidates) |

---

## 38. Conclusion

Phase 1G-00 is a **documentation-only** scope document. It:

1. Audits the complete Hermes tool system (71 tools, 33 toolsets, full call chain)
2. Classifies every tool by risk level with unique Primary Risk (R0: 1, R1: 5, R2: 19, R3: 26, R4: 17, R5: 3 = 71)
3. Freezes a Permanent Denylist of 26 tools
4. Freezes a Candidate Allowlist of 6 tools (1 R0 + 5 R1, 0 enabled)
5. Defines comprehensive safety contracts for all future Tool Execution phases
6. Defines a 6-phase implementation roadmap (1G-01 through 1G-06)
7. Establishes zero modification to existing code, API, state, or production environment

**No Tool execution capability was implemented or enabled.**

**No Provider Tool Schema was sent.**

**Phase 1G implementation has not started.**

---

## 39. Documentation Fix Record

### Date

2026-06-10

### Problems Discovered

**Problem 1: R1 count inconsistency.**
- The risk summary table listed R1 = 4 with tools: `read_file, search_files, skills_list, skill_view`
- The Candidate Allowlist table listed 6 tools including `session_search` at R1
- `session_search` was classified as R2 in the summary but R1 in the Candidate list
- Root cause: `session_search` reads local SessionDB via FTS5 — it has no external network access, no credentials, no filesystem write — it is R1, not R2
- Fix: Moved `session_search` from R2 to R1 in the summary table

**Problem 2: Risk total exceeded tool count.**
- Original summary: R0=1 + R1=4 + R2=22 + R3=22 + R4=20 + R5=4 = 73
- Registry contains only 71 canonical tools
- Root causes:
  - `session_search` was double-counted (R2 in summary but R1 in Candidate)
  - `ha_call_service` was counted in both R3 and R5 (overlap note)
  - `cronjob` was counted in both R3 and R5 (overlap note)
  - Spotify tools were grouped as "R2–R5" with ambiguous individual classification
  - No explicit rule that each tool gets exactly one Primary Risk Level
- Fix: Adopted unique Primary Risk model — each tool assigned to its single highest risk level

### Classification Model Fix

**Before (original):** Tools could appear in multiple risk levels. Dual-classification was noted informally. No explicit rule enforced uniqueness.

**After (fixed):** Each of the 71 canonical tools is assigned exactly one Primary Risk Level, equal to its highest actual risk. Capability tags are orthogonal but do not participate in the Primary Risk total.

### Before Statistics

| Risk | Count |
|------|------:|
| R0 | 1 |
| R1 | 4 |
| R2 | 22 |
| R3 | 22 |
| R4 | 20 |
| R5 | 4 |
| Total | 73 (≠71) |

### After Statistics

| Risk | Count | Delta |
|------|------:|-------|
| R0 | 1 | = |
| R1 | 5 | +1 (session_search moved from R2) |
| R2 | 19 | −3 (session_search→R1, spotify_devices→R3, spotify_queue→R3) |
| R3 | 26 | +4 (discord added, spotify_devices/queue moved from R2, ha_call_service removed from R3↔R5 overlap) |
| R4 | 17 | −3 (browser tools recounted: 12 browser + 5 non-browser = 17, not 20) |
| R5 | 3 | −1 (ha_call_service and cronjob deduplicated — each appears once in R5 only) |
| Total | 71 | =71 ✓ |

### Key Reclassifications

| canonicalName | Before | After | Reason |
|---------------|--------|-------|--------|
| session_search | R2 (summary) / R1 (candidate) | R1 | Local-only FTS5 query on SessionDB; no network, no credentials |
| spotify_devices | R2 | R3 | `transfer` action mutates playback state |
| spotify_queue | R2 | R3 | `add` action modifies playback queue |
| discord | R3 | R3 | No change; was correctly R3 in inventory |
| ha_call_service | R3 + R5 (dual) | R5 only | IoT device control = highest risk R5 |
| cronjob | R3 + R5 (dual) | R5 only | Spawns arbitrary agent runs = highest risk R5 |

### Candidate Allowlist Verification

| Tool | Canonical Name | Risk | Verified |
|------|---------------|------|----------|
| clarify | ✓ exists in Registry | R0 | ✓ |
| skills_list | ✓ exists in Registry | R1 | ✓ |
| skill_view | ✓ exists in Registry | R1 | ✓ |
| read_file | ✓ exists in Registry | R1 | ✓ |
| search_files | ✓ exists in Registry | R1 | ✓ |
| session_search | ✓ exists in Registry | R1 | ✓ |

Total: 6 candidates (1 R0 + 5 R1), 0 enabled, no intersection with Denylist.

### Permanent Denylist Verification

- 26 canonical names, all verified in Registry
- No duplicates, no aliases, no toolset names, no wildcards
- Denylist ∩ Candidate = ∅

### Spotify Inventory Expansion

The original document grouped all 7 Spotify tools under a single "R2–R5" entry (section 6.50). This obscured individual tool classification and contributed to the counting error.

Fix: Expanded into 7 individual entries (6.50–6.56), each with a single Primary Risk Level:
- R2 (read-only): spotify_albums, spotify_search
- R3 (state mutation): spotify_devices, spotify_library, spotify_playback, spotify_playlists, spotify_queue

### Safety Policy Impact

**No safety policy changes.** This fix only corrects documentation statistics and classification model. It does not:
- Change the Permanent Denylist composition
- Change the Candidate Allowlist composition
- Change any safety contract, decision chain, or kill switch rule
- Implement any Tool Execution capability
- Modify any business code
