# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Environment Safety

**Highest priority. Every other section is subordinate to these rules.**

| Item | Path / Value |
|------|-------------|
| Source root | `/Users/huangruibang/Code/hermes-agent-dev` |
| Development HERMES_HOME | `/Users/huangruibang/Code/hermes-home-dev` |
| Production HERMES_HOME | `/Users/huangruibang/.hermes` |
| Development branch | `dev-huangruibang` |

### Hard Rules

1. **Never read from or write to `/Users/huangruibang/.hermes`.** This is the production instance. All development must use `/Users/huangruibang/Code/hermes-home-dev`.
2. **Never run `setup-hermes.sh`.** The development environment is already configured.
3. **Never modify or reinstall the global `hermes` command.** The production CLI must remain untouched.
4. **Never stop, restart, replace, signal, or reconfigure the production Gateway.**
5. **Never start the production Gateway or production Dashboard.**
6. **Never commit WeChat sessions, caches, logs, PID files, API keys, tokens, or secrets.** Verify `.gitignore` coverage before staging.
7. **Never enable automatic memory writing, automatic memory updating, or automatic category creation.**
8. **Development services must bind to `127.0.0.1` only.** Never expose dev services on `0.0.0.0`.
9. **Do not commit or push unless explicitly requested by the user.**
10. **Before and after changes, verify the Git branch and working tree.** Confirm you are on `dev-huangruibang` and the tree is clean (or has only expected changes).
11. **Use `/Users/huangruibang/Code/hermes-home-dev` for all development runtime data** — sessions, memories, logs, cron state, plugin data.

### Dev WebUI Environment Guard

The Dev WebUI backend must use a **precise allowlist**, not a deny-list:

```python
import os
from pathlib import Path

ALLOWED_SOURCE_ROOT = Path("/Users/huangruibang/Code/hermes-agent-dev").resolve()
ALLOWED_HERMES_HOME = Path("/Users/huangruibang/Code/hermes-home-dev").resolve()
ALLOWED_BIND_HOST = "127.0.0.1"

def enforce_dev_environment():
    # Source root derived from module location, NOT from cwd
    source_root = Path(__file__).resolve().parents[1]
    hermes_home = Path(os.environ.get("HERMES_HOME", "")).resolve()
    if source_root != ALLOWED_SOURCE_ROOT:
        raise RuntimeError(f"Source root must be {ALLOWED_SOURCE_ROOT}, got {source_root}")
    if hermes_home != ALLOWED_HERMES_HOME:
        raise RuntimeError(f"HERMES_HOME must be {ALLOWED_HERMES_HOME}, got {hermes_home}")
    # cwd is supplementary diagnostic info only, never the sole basis for source root
```

Any mismatch → **fail closed** (refuse to start, refuse all API requests).

### Dev WebUI P0 Access Control

**WebUI may write to:**
- `/Users/huangruibang/Code/hermes-home-dev` session data (create/update/delete conversations)
- Dev WebUI's own non-sensitive UI state

**WebUI P0 must remain read-only for:**
- Formal hierarchical Memory (MEMORY.md, memory/indexes/, memory/records/, memory/events.jsonl, memory/snapshots/, memory/reviews/)
- Review Queue
- Gateway state
- Workspace source files
- Hermes configuration
- Environment variables
- WeChat sessions and cache

**WebUI P0 absolutely prohibits:**
- `memory-add`, `memory-update`, `memory-archive`
- Review approve or reject
- Gateway start, stop, restart, or replace
- File creation, modification, move, or delete (including via Agent tools)
- `git commit`, `git push`, `git reset`, `git clean`
- Configuration or environment variable modification
- Automatic memory writing, updating, or category creation
- Executing any tool with side effects without explicit user approval
- Terminal write commands, `write_file`, `patch`, `execute_code`, `delegate_task`, `browser_*`, `computer_use`, `send_message`

## Project Overview

Hermes Agent is a self-improving AI agent with tool-calling, multi-platform messaging, skill creation, and cron scheduling. Python 3.11–3.13 backend with TypeScript frontend workspaces (TUI, desktop, web dashboard).

## Build & Install

> **WARNING:** Never run `./setup-hermes.sh` in this development environment.
> The venv and dependencies are already configured. Do not recreate or overwrite `.venv`.

```bash
# Activate the existing virtual environment
source .venv/bin/activate

# Install/editable install if dependencies changed
uv pip install -e ".[all,dev]"
```

**Frontend packages:** Do NOT blindly run `npm install` at the repo root. Before any frontend work:
1. Check `package.json`, `package-lock.json` (or `pnpm-lock.yaml` / `yarn.lock`), and workspace config.
2. Identify which package manager the project actually uses.
3. Only then run the appropriate install command (`npm install`, `pnpm install`, etc.) in the correct workspace directory.

## Testing

```bash
# ALWAYS use the wrapper — it enforces hermetic CI parity (clean env, TZ=UTC, no leaked credentials)
scripts/run_tests.sh                                    # full suite
scripts/run_tests.sh tests/gateway/                     # one directory
scripts/run_tests.sh tests/agent/test_foo.py::test_x   # single test
scripts/run_tests.sh -- -v --tb=long                    # passthrough pytest flags
scripts/run_tests.sh --no-isolate tests/foo/            # skip subprocess isolation (debugging only)
```

**Never call `pytest` directly** if you can use the wrapper. Direct pytest with developer API keys set diverges from CI. If you must (e.g. IDE integration), activate the venv first and use `python -m pytest tests/ -q`.

Every test runs in a fresh subprocess (via `tests/_isolate_plugin.py`) — module-level state cannot leak between tests.

## Linting & Type Checking

```bash
ruff check .                   # lint (only PLW1514 is enabled — encoding safety)
ruff check --fix .             # auto-fix
ty check                       # type checking (experimental, warn-only)
```

## Dev Verification Commands

```bash
./scripts/run-dev-hermes.sh dev-check           # development environment health check
./scripts/run-dev-hermes.sh memory-check        # verify dev memory store integrity
./scripts/run-dev-hermes.sh dev-info            # show dev environment info (paths, branch, config)
./scripts/run-dev-hermes.sh gateway-dev status   # show development gateway status (read-only)
```

> **Unless explicitly requested,** do NOT run `gateway-dev run`, `gateway-dev stop`, or any production Gateway commands.

## Architecture

### Core Loop

```
User message → AIAgent._run_agent_loop()
  ├── Build system prompt (agent/prompt_builder.py)
  ├── Call LLM (OpenAI-compatible API)
  ├── If tool_calls → execute via registry dispatch → loop back
  ├── If text response → persist session to SQLite → return
  └── Context compression if approaching token limit
```

### Key Files & Dependency Chain

```
tools/registry.py          (no deps — imported by all tool files)
       ↑
tools/*.py                  (each calls registry.register() at import time)
       ↑
model_tools.py              (imports registry + triggers tool discovery)
       ↑
run_agent.py, cli.py        (AIAgent class, HermesCLI class)
```

### Package Layout

| Path | Role |
|------|------|
| `run_agent.py` | `AIAgent` class — core conversation loop, tool dispatch, session persistence (~12k LOC) |
| `cli.py` | `HermesCLI` — interactive prompt_toolkit CLI (~11k LOC) |
| `model_tools.py` | Tool orchestration, `discover_builtin_tools()`, `handle_function_call()` |
| `toolsets.py` | Toolset definitions (`TOOLSETS` dict, `_HERMES_CORE_TOOLS`) |
| `hermes_state.py` | `SessionDB` — SQLite session store with FTS5 search |
| `hermes_constants.py` | `get_hermes_home()`, `display_hermes_home()` — profile-aware paths |
| `agent/` | Internals: prompt builder, context compressor, provider adapters, memory |
| `tools/` | Self-registering tools; auto-discovered from `tools/*.py` |
| `tools/environments/` | Terminal backends (local, docker, ssh, modal, daytona, singularity) |
| `gateway/` | Messaging gateway — `run.py` + `session.py` + `platforms/` adapters |
| `hermes_cli/` | CLI subcommands, setup wizard, plugins loader, skin engine, slash command registry |
| `plugins/` | Plugin system (memory providers, model providers, observability, etc.) |
| `skills/` | Bundled skills (shipped with every install) |
| `optional-skills/` | Official optional skills (discoverable, not active by default) |
| `cron/` | Scheduler — `jobs.py` + `scheduler.py` |
| `acp_adapter/` | ACP server (VS Code / Zed / JetBrains integration) |
| `ui-tui/` | Ink (React) terminal UI — `hermes --tui` |
| `tui_gateway/` | Python JSON-RPC backend for the TUI |
| `web/` | React web dashboard |

### Config Loaders (three paths)

| Loader | Used by | Location |
|--------|---------|----------|
| `load_cli_config()` | CLI mode | `cli.py` |
| `load_config()` | `hermes tools`, `hermes setup`, most subcommands | `hermes_cli/config.py` |
| Direct YAML load | Gateway runtime | `gateway/run.py` + `gateway/config.py` |

If a new config key shows in CLI but not gateway (or vice versa), check `DEFAULT_CONFIG` coverage.

## Adding a New Tool

1. Create `tools/your_tool.py` with a `registry.register(...)` call — auto-discovered, no manual import list.
2. **Add the tool name to a toolset in `toolsets.py`** — this is required; without it the tool registers but is never exposed to the agent.
3. All handlers return JSON strings.

For local-only or custom tools, prefer the plugin route: `~/.hermes/plugins/<name>/plugin.yaml` + `register_tool()` via `ctx`.

## Adding a Skill

Most capabilities should be **skills**, not tools. See `CONTRIBUTING.md` for the "Skill vs Tool" decision framework.

- Bundled → `skills/<category>/<name>/SKILL.md`
- Optional → `optional-skills/<category>/<name>/SKILL.md`
- SKILL.md frontmatter: `name`, `description` (≤60 chars), `version`, `author`, `platforms`, `metadata.hermes.*`
- Tests → `tests/skills/test_<skill>_skill.py`

## Hermes Dev WebUI

Current development goal: building a modern AI workbench WebUI for the Hermes development instance.

### Technology Decision (Confirmed)

- **Independent Vue 3 application** at `apps/hermes-dev-webui/`
- **Does NOT modify existing `web/` React Dashboard**
- Backend: `hermes_cli/dev_web_server.py`, `dev_web_api.py`, `dev_web_schemas.py`
- Frontend: Vue 3 + TypeScript + Vite + Vue Router + Pinia + Tailwind CSS
- Product form: three-column AI workbench (session sidebar | chat area | workspace panel)

### Built-in Theme System (Frozen)

The Dev WebUI ships with **five built-in themes**. Aurora and Terminal are NOT included.

#### Theme IDs and Default

| Theme | ID | Category | Color Scheme |
|-------|----|----------|-------------|
| Obsidian | `obsidian` | Modern | Dark |
| Paper | `paper` | Modern | Light |
| 宋韵 Song | `song` | Eastern | Light |
| 墨境 Ink | `ink` | Eastern | Dark |
| 夜樱 Sakura Night | `sakura-night` | Eastern | Dark |

- Default theme: `obsidian`
- `ThemeId` must be a strict union type — no arbitrary strings

#### Theme Grouping (for Theme Picker)

- **Modern:** Obsidian, Paper
- **Eastern (东方):** 宋韵 Song, 墨境 Ink, 夜樱 Sakura Night

#### Theme Positioning

**Obsidian** (default)
- Dark. Linear-style modern professional developer tool aesthetic.
- Neutral-cool background, low-saturation blue-purple accent.
- Medium-high density, medium border-radius, thin borders, weak shadows.
- User messages: light bubbles. Assistant messages: natural document layout.

**Paper**
- Light. Clean document-reading aesthetic.
- Neutral warm-white background, gray-blue accent.
- Medium density, small border-radius, minimal shadows.
- Assistant replies use document-style layout.

**宋韵 Song**
- Light. Song dynasty literati, Song edition books, and Xuan paper aesthetic.
- Xuan paper warm-white, ink black, dai-blue (黛青), vermilion (朱砂), Ru ware celadon (汝窑青).
- Comfortable density, small border-radius, almost no shadows.
- Active session may use a thin vermilion bookmark line.
- Messages use scroll-and-document layout.
- No direct decoration: no dragons, palaces, or auspicious clouds.

**墨境 Ink**
- Dark. Chinese ink-wash night aesthetic.
- Ink black, deep dai, moon-white, celadon green, trace vermilion.
- Medium-high density, small-medium border-radius, weak borders, no heavy shadows.
- Assistant replies use minimal document layout.
- No large-area ink-wash background images.

**夜樱 Sakura Night**
- Dark. Restrained Japanese night aesthetic.
- Deep night blue, indigo, moon-white, gray-pink, cherry blossom pink.
- Medium density, larger border-radius, soft shadows.
- Light card and bubble style.
- No animated cherry blossom backgrounds, anime characters, or large-area pink.

#### Theme Difference Requirements

Themes must differ beyond background and accent colors. Every theme must control:

- `colorScheme` (light/dark)
- Font stack
- Page and panel backgrounds
- Text hierarchy
- Accent colors and semantic state colors
- Borders
- Border-radius
- Shadows
- UI density
- `messageStyle` (bubble, document, scroll, minimal)
- `panelStyle`
- `toolCardStyle`
- `motion` (animation intensity)
- Focus ring
- Scrollbar
- Selection color

**Recommended `ThemeDefinition` fields:**

```typescript
interface ThemeDefinition {
  id: ThemeId;
  name: string;
  localizedName: string;
  description: string;
  category: "modern" | "eastern";
  colorScheme: "light" | "dark";
  previewColors: { bg: string; fg: string; accent: string; };
  density: "compact" | "comfortable" | "loose";
  radius: "none" | "small" | "medium" | "large";
  panelStyle: string;
  messageStyle: "bubble" | "document" | "scroll" | "minimal";
  toolCardStyle: string;
  motion: "none" | "reduced" | "normal" | "expressive";
  fontStyle: string;
}
```

#### Theme Technical Rules

- The same Vue components must adapt to all five themes.
- Root element uses: `data-theme`, `data-density`, `data-message-style`, `data-panel-style`, `data-tool-card-style`, `data-motion`.
- All components use semantic CSS Variables.
- Font stack: system font fallback only. No remote fonts, no committed font files.

**Prohibited:**
- Large amounts of fixed Tailwind color scales in components.
- Scattered hex colors in component code.
- Duplicating entire Vue components per theme.
- Large-area background images for theming.
- Remote fonts or committed font files.
- Unlicensed artwork as backgrounds.

#### Theme File Structure

```
apps/hermes-dev-webui/src/themes/
├── types.ts
├── registry.ts
├── theme-manager.ts
└── styles/
    ├── base.css
    ├── obsidian.css
    ├── paper.css
    ├── song.css
    ├── ink.css
    └── sakura-night.css

apps/hermes-dev-webui/src/stores/theme.ts

apps/hermes-dev-webui/src/components/theme/
├── ThemeSwitcher.vue
├── ThemePicker.vue
└── ThemePreviewCard.vue
```

#### Theme Test Requirements

Phase 0 must cover:
- Default theme is Obsidian
- All five themes are registered
- All five Theme IDs are valid
- Invalid ID falls back to Obsidian
- `setTheme` correctly updates root element attributes
- `localStorage` correctly saves and restores theme
- Theme Picker groups by Modern, Eastern
- All five themes define all required CSS Variables
- Theme switch does not reload the page
- `prefers-reduced-motion` is respected
- Light themes correctly set `color-scheme: light`
- Dark themes correctly set `color-scheme: dark`

### P0 Tool Execution Policy

**Phase 0 is a pure frontend mock workbench — it does NOT call the real Agent and does NOT execute any Agent tools.**

Before entering the real conversation integration phase, the following audit is mandatory:

1. Audit `tools/registry.py` — verify every tool's actual registered name (the string passed to `registry.register()`).
2. Audit `toolsets.py` — verify which toolset each tool belongs to.
3. Audit each candidate tool handler — confirm its actual input parameters, output format, and whether it has side effects.
4. Only after confirming the real registered name, input/output schema, and absence of side effects may a tool be added to the `dev-webui-safe` toolset.

**Tools that remain disabled by default until individually audited:**
- `clarify`, `todo`, `memory`, `web_search`, `web_extract`, `vision_analyze`, `read_file`, `search_files`, `skills_list`, `skill_view`, `session_search` — these names are NOT verified against the real registry. Do NOT assume they are safe by name alone.

**Tools that are permanently prohibited in WebUI P0:**
- `terminal`, `process` — shell/system execution
- `write_file`, `patch` — file modification
- `execute_code` — code execution sandbox
- `delegate_task` — subagent spawning
- `browser_*` — browser automation
- `computer_use` — desktop control
- `send_message` — cross-platform messaging
- `cronjob` — cron job management
- `skill_manage` — skill mutation
- `image_generate` — image generation

**Do NOT guess tool safety from names.** Every tool must be individually audited against the real code. The `dev-webui-safe` toolset in `toolsets.py` may only be created after the full audit is complete.

### P0 Context Panel Scope

The Context panel is restricted to displaying:

- Hit Memory categories and Memory IDs
- Memory summaries and scores
- Skipped items (archived entries)
- Truncation status
- Runtime Memory injection status
- Current user message

**P0 Context panel must NOT expose:**
- Full system prompt text
- SOUL.md, CLAUDE.md, or AGENTS.md full content
- API keys, secrets, or tokens
- Full skill instruction text
- Internal model routing parameters

### SSE Constraints

`run_conversation()` / `chat()` are **synchronous blocking calls** — they must run in a thread pool. The following rules are mandatory for any WebUI SSE implementation:

1. **Thread pool execution:** `run_conversation()` and `chat()` must be dispatched via `asyncio.get_running_loop().run_in_executor(None, ...)`. Never call them directly from a FastAPI coroutine.
2. **Bridge pattern:** Synchronous callbacks (e.g. `stream_delta_callback`) must write to `asyncio.Queue` via `loop.call_soon_threadsafe(queue.put_nowait, event)`. The SSE response async-iterates from that queue.
3. **Single streaming entry:** `stream_delta_callback` (AIAgent constructor param) and `stream_callback` (chat/run_conversation param) are **different mechanisms** that may fire overlapping text. Only one must be registered per consumer — never both simultaneously for the same SSE stream.
4. **Choose one:** Before integration, decide which callback mechanism to use and document the choice. Do not wire both.
5. **Done event:** The `done` SSE event must be emitted exactly once, triggered by the background `Future` completing (not by a text delta of `None`). The Future's result or exception determines whether `done` or `error` is sent.
6. **Error propagation:** If the background thread raises an exception, it must be caught and converted to an `error` SSE event with the exception message. Never silently swallow background errors.
7. **Client disconnect:** When the client disconnects (SSE connection closes), the server must call `AIAgent.interrupt()` to stop the running generation. Use FastAPI's `Request.is_disconnected()` in the SSE loop or lifecycle hooks.
8. **Single-generation constraint:** At most one generation task may run per session at any time. A second request to the same session must be rejected (HTTP 409) or queued — never start concurrent generations for the same session.

### Session Persistence Constraints

Before implementing Web API message persistence, the following must be verified through source code audit and confirmed with tests:

1. **Does `AIAgent.chat()` / `run_conversation()` auto-persist?** — Verify whether user messages and assistant replies are automatically saved to SessionDB inside `_persist_session()`. If yes, the Web API must NOT duplicate persistence.
2. **How is `session_id` passed or bound?** — Verify whether `session_id` is a constructor parameter, a method parameter, or auto-generated. Document how WebUI associates a conversation with an existing session.
3. **How is `source="dev-webui"` set?** — Verify the `source` field in `SessionDB.create_session()`. Determine whether it's set via AIAgent constructor, config, or at the SessionDB call site.
4. **Single responsibility:** Web API and Agent Runtime must not both persist messages. Exactly one must own persistence for each message. If Agent auto-persists, Web API must not call `append_message()` for the same content.
5. **No double-persist:** Every user message and every assistant message must be saved exactly once. A test must verify this invariant: after a single `chat()` call, the message count in SessionDB increases by exactly the expected number (not doubled).

### Memory Architecture

The Memory system has two distinct modules with separate responsibilities:

| Module | Path | Responsibility |
|--------|------|---------------|
| Memory Writer | `agent/runtime_memory_writer.py` | Decision evaluation — determines whether to WRITE, UPDATE, REVIEW, or SKIP a memory candidate based on conversation content |
| Review Queue | `agent/memory_review_queue.py` | Storage and state management — persists review items, tracks status (PENDING → APPROVED/REJECTED/FAILED) |

**Do NOT confuse the two:**
- `memory_review_queue.py` manages the queue lifecycle; it does NOT evaluate whether a memory is worth writing.
- `runtime_memory_writer.py` makes the decision; it does NOT manage queue persistence.
- Never substitute one for the other.

Runtime memory data is stored under `$HERMES_HOME/memory/` (NOT `memories/`):
- `memory/indexes/` — category index files
- `memory/records/` — individual memory records
- `memory/events.jsonl` — append-only event log
- `memory/snapshots/` — periodic snapshots
- `memory/reviews/` — review queue items

### Phase 0 Scope (0A → 0B → 0C → 0D)

Phase 0 implements the **frontend mock workbench only**. No real Agent integration.

**Phase 0A — Theme System & Project Scaffold:**
- `apps/hermes-dev-webui/` Vue 3 + TypeScript + Vite project scaffold
- `ThemeDefinition` type and `ThemeId` strict union
- Theme Registry (`themes/registry.ts`)
- Theme Store (`stores/theme.ts`) with localStorage persistence
- Five theme base CSS token files
- `base.css` with all semantic CSS Variables
- Theme Picker component (grouped: Modern, Eastern)
- Theme Preview Card component
- Theme Switcher component
- Theme unit tests (12 cases per test requirements above)

**Phase 0B — Layout & Theme Integration:**
- Three-column responsive layout (session sidebar | chat area | workspace panel)
- Top status bar (connection status, model info, environment indicator)
- All five themes adapted to the main layout
- Root element data attributes wired to theme system

**Phase 0C — Mock Content Components:**
- Mock session list (sidebar with fake conversation entries)
- Mock user and assistant messages (static chat bubbles)
- Mock streaming text (simulated SSE with typewriter effect)
- Mock tool call cards (collapsible cards showing tool name, input, output)
- Mock Memory panel (displaying mock memory hits and categories)
- Mock Context panel (displaying mock context injection info)
- Verify all five themes render correctly across different content components

**Phase 0D — Quality & Verification:**
- Responsive breakpoints and mobile adaptation
- Accessibility (keyboard nav, screen reader, focus management)
- Motion and animation polish (respects `prefers-reduced-motion`)
- `vue-tsc` type checking
- ESLint pass
- Vitest unit tests for all stores and components
- Production build (`vite build`)
- Browser visual verification of all five themes

**Phase 0 overall does NOT include:**
- Real Agent conversation API (no `AIAgent.chat()` calls)
- No modification to `toolsets.py` (no `dev-webui-safe` toolset yet)
- No SessionDB integration (no real session persistence)
- No real SSE implementation (no FastAPI backend)
- No real tool execution
- No backend Python files (`dev_web_server.py`, `dev_web_api.py`, etc.)

## Critical Policies

### Paths: Never hardcode `~/.hermes`

Always use `get_hermes_home()` for code paths and `display_hermes_home()` for user-facing messages. Profiles create isolated `HERMES_HOME` directories — hardcoded paths break them.

### Prompt caching must not break mid-conversation

Do not alter past context, change toolsets, or rebuild system prompts mid-conversation. Slash commands that mutate state default to deferred invalidation (next session) with an opt-in `--now` flag.

### Dependency pinning

All PyPI dependencies need upper bounds: `>=floor,<next_major` for post-1.0, `<0.(minor+2)` for pre-1.0. No bare `>=X.Y.Z`. Git URLs pinned to commit SHA. GitHub Actions pinned to SHA with version comment.

### Cross-platform code

- Never `os.kill(pid, 0)` for liveness — use `psutil.pid_exists(pid)`
- `shutil.which()` before shelling out — don't assume POSIX tools exist
- `termios`/`fcntl` are Unix-only — guard with `ImportError` + `NotImplementedError`
- File encoding: always explicit `encoding="utf-8"` (Windows defaults to cp1252)
- Use `pathlib.Path`, not string concatenation with `/`

### Tests

- Never write to `~/.hermes/` — the `_isolate_hermes_home` autouse fixture redirects to temp
- Don't write change-detector tests (snapshot assertions on model catalogs, config versions, enumeration counts) — test behavior/invariants instead
- Integration tests: `@pytest.mark.integration` (excluded from default run)

### Slash commands

Defined in `COMMAND_REGISTRY` (`hermes_cli/commands.py`) as `CommandDef` objects. Adding an alias only requires updating the `aliases` tuple — dispatch, help, autocomplete, Telegram menu, and Slack mapping all update automatically.

### Plugins must not modify core files

Plugins extend via hooks (`ctx.register_tool`, `ctx.register_cli_command`, lifecycle hooks). If a capability is missing, expand the generic plugin surface — never hardcode plugin-specific logic into core.

## Entry Points

```bash
hermes              # CLI conversation (hermes_cli.main:main)
hermes gateway      # Messaging gateway
hermes setup        # Setup wizard
hermes-acp          # ACP adapter (acp_adapter.entry:main)
```

## Commit Conventions

Conventional Commits: `type(scope): description` (fix, feat, docs, test, refactor, chore). Scopes: cli, gateway, tools, skills, agent, install, security, etc.
