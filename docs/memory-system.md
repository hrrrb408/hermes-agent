# Hermes Memory System

## Design Goals

Hermes uses a layered memory system so long-term memory does not depend on a
single ever-growing `MEMORY.md` file.

The current goals are:

- Avoid unbounded growth in `MEMORY.md`.
- Avoid overwriting older memory when a memory item is updated.
- Keep `MEMORY.md` as the root router only.
- Store category-level indexes in separate index files.
- Store full memory content in record files.
- Record category and memory changes in append-only `events.jsonl`.
- Create snapshots before modifying root, index, or record files.
- Load relevant memory context for a query through `memory-context`.

This implementation is file-based and intentionally simple. It does not use
LLM summarization, embeddings, or a vector database.

## Directory Structure

The development memory home currently uses this shape:

```text
HERMES_HOME/
├── MEMORY.md
├── memory/
│   ├── indexes/
│   │   ├── user.md
│   │   ├── hermes.md
│   │   ├── projects.md
│   │   ├── learning.md
│   │   ├── dev-env.md
│   │   ├── preferences.md
│   │   └── travel.md
│   ├── records/
│   │   └── ...
│   ├── events.jsonl
│   └── snapshots/
```

`MEMORY.md` is the Root Router. It stores root category entries only.

`memory/indexes/*.md` are Category Index files. Each category has one index
file with memory item metadata.

`memory/records/**/*.md` are Memory Records. They store the detailed memory
body.

`memory/events.jsonl` is the Event Log. It records category and memory item
changes as append-only JSON lines.

`memory/snapshots/` stores snapshots created before root, index, or record
files are modified.

## Root Router Format

Root categories are stored in `MEMORY.md` as Markdown sections:

```md
## hermes

- index: memory://indexes/hermes.md
- scope: project
- priority: P0
- status: active
- keywords: Hermes, dev-check, gateway, memory, cli
- description: Hermes 项目当前进度、开发约束、设计决策、功能规划等。
```

Root categories are dynamic data. The fixed bootstrap categories are used only
when a new `MEMORY.md` is first created. Once `MEMORY.md` exists, the categories
come from `MEMORY.md`; Python code should parse, validate, display, and maintain
those categories rather than enforcing a fixed runtime list.

## Category Index Format

Category indexes live under `memory/indexes/*.md`. A memory item is declared as
a Markdown section:

```md
## MEM-HERMES-001 Hermes 当前开发状态

- type: project_status
- importance: P0
- ttl: project
- status: active
- tags: hermes, status, branch, dev-check
- storage: memory://records/projects/hermes/current-status.md
- created_at: 2026-06-05
- updated_at: 2026-06-05
- summary: Hermes 当前在 dev-huangruibang 分支，已完成 dev-info 和 dev-check，工作区干净，未污染全局环境。
```

The item fields are:

- `memory_id`: parsed from the section heading, for example `MEM-HERMES-001`.
- `title`: parsed from the rest of the section heading.
- `type`: memory type, such as `project_status` or `architecture_decision`.
- `importance`: `P0`, `P1`, `P2`, or `P3`.
- `ttl`: `permanent`, `project`, `session`, or `temporary`.
- `status`: `active`, `archived`, `deprecated`, `superseded`, or `conflict`.
- `tags`: comma-separated search and routing tags.
- `storage`: a `memory://records/...` URI pointing to the detailed record.
- `created_at`: creation date.
- `updated_at`: last update date.
- `summary`: compact human-readable summary.

## Memory Record Format

Detailed records live under `memory/records/**/*.md`:

```md
# MEM-HERMES-002 Hermes 分层记忆路由系统设计

## Summary

...

## Details

...

## Metadata

- category: hermes
- type: architecture_decision
- importance: P0
- ttl: permanent
- status: active
- tags: hermes, memory, architecture
- created_at: 2026-06-05
- updated_at: 2026-06-05
```

The index remains the authoritative routing layer. The record keeps the full
context that can be shown by `memory-show` or loaded by `memory-context`.

## CLI Commands

### Root / Category

```bash
./scripts/run-dev-hermes.sh memory-root
./scripts/run-dev-hermes.sh memory-root --all
./scripts/run-dev-hermes.sh memory-category-list
./scripts/run-dev-hermes.sh memory-category-list --all
./scripts/run-dev-hermes.sh memory-category-show hermes
./scripts/run-dev-hermes.sh memory-category-add travel ...
./scripts/run-dev-hermes.sh memory-category-update travel ...
./scripts/run-dev-hermes.sh memory-category-archive travel
```

### Memory Read

```bash
./scripts/run-dev-hermes.sh memory-index hermes
./scripts/run-dev-hermes.sh memory-list
./scripts/run-dev-hermes.sh memory-list --all
./scripts/run-dev-hermes.sh memory-show MEM-HERMES-001
./scripts/run-dev-hermes.sh memory-search "分层记忆"
```

### Memory Write

```bash
./scripts/run-dev-hermes.sh memory-add ...
./scripts/run-dev-hermes.sh memory-update MEM-HERMES-003 ...
./scripts/run-dev-hermes.sh memory-archive MEM-HERMES-003
```

### Memory Context

```bash
./scripts/run-dev-hermes.sh memory-context "Hermes 记忆系统现在做到哪了"
./scripts/run-dev-hermes.sh memory-context "分层记忆路由系统" --show-scores
./scripts/run-dev-hermes.sh memory-context "安全写入 memory-add memory-update memory-archive" --include-archived
```

### Checks

```bash
./scripts/run-dev-hermes.sh memory-check
./scripts/run-dev-hermes.sh dev-check
./scripts/run-dev-hermes.sh dev-info
```

## Current Milestones

```text
112157b44  feat: add hierarchical memory router
404d17a9b  feat: add dynamic memory categories
9e09cd10c  feat: add memory write commands
ee877bde0  feat: add memory context loader
```

The current memory system supports layered routing, dynamic root categories,
safe memory creation, memory updates, memory archival, keyword search, query
context loading, `memory-check`, and `dev-check` regression validation.

## Roadmap

The next steps should stay incremental:

1. Current stage: document the memory system and expose status through
   `dev-info`.
2. Next stage: integrate Memory Context Loader into Agent Runtime.
3. Then: generate candidate memories, without automatic writes.
4. Then: add human confirmation before writing memory.
5. Finally: close the long-term memory loop for WeChat usage.

Automatic memory writes are high risk. The safer route is candidate generation
first, followed by explicit human confirmation before anything is written.

WeChat integration, including `gateway-dev run`, should go through Agent
Runtime memory injection. The WeChat/Gateway layer should not call or modify
`memory_router` directly.
