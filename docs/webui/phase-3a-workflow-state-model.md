# Phase 3A — Workflow State Model

## Location

The workflow state store is **dev-only** and lives under:

```
$HERMES_HOME/gateway/dev/workflow-store/
  workflows/    wf_….json        (workflow definitions)
  executions/   wfx_….json       (execution snapshots)
  timelines/    wfx_….jsonl      (append-only timeline events)
  meta/         store metadata + advisory lock files
```

It never lives under the repository, under `~/.hermes`, or under production
state. It is gitignored and never committed.

## Confinement

`_resolve_home` rejects: an unset `HERMES_HOME`, the production home
(`/Users/huangruibang/.hermes`), and the repository source root.
`validate_workflow_store_root` rejects the production home and the repo root.

## Integrity

- **Atomic writes** — every document is written via a temp file + `os.replace`,
  so a crashed write never leaves a half-written document.
- **Corruption-safe** — a malformed JSON document is skipped (returns `None` /
  read-only), never leaked, never crashes the API.
- **Advisory file lock** — `fcntl` on Unix (ImportError-guarded no-op fallback)
  serializes concurrent timeline appends.
- **Bounded** — 256 KiB per document, 1000 timeline events per execution.

## API

```python
ensure_workflow_store(hermes_home) -> (root, error)
get_workflow_store_root(hermes_home) -> Path
validate_workflow_store_root(root) -> error | None
save_workflow_definition(definition, hermes_home) -> WorkflowStoreResult
load_workflow_definition(workflow_id, hermes_home) -> WorkflowDefinition | None
save_workflow_execution(state, hermes_home) -> WorkflowStoreResult
load_workflow_execution(execution_id, hermes_home) -> WorkflowExecutionState | None
append_workflow_timeline_event(execution_id, event, hermes_home) -> WorkflowStoreResult
list_workflow_executions(limit, hermes_home) -> list[dict]
```

`load_workflow_execution` merges the authoritative append-only timeline JSONL
over the execution snapshot, so the freshest events always win.

## Sanitization on persist

Every persisted document runs through `sanitize_workflow_value` before write.
No raw token, full token hash, raw arguments, file content, API key, callable
repr, or production path is ever persisted.
