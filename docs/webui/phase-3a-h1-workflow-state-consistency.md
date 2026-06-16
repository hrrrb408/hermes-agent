# Phase 3A-H1 — Workflow State Consistency

**ID:** `WORKFLOW-STATE-3A-H1-001`
**Lens:** 2 — Workflow Store / State Persistence Boundary

## Scope

The dev-only, file-backed workflow store and its state-persistence contract:
confinement, atomic writes, append-only timeline, corruption safety, document
bounds, and no-leak on disk.

## Evidence (code)

- `hermes_cli/dev_web_workflow_store.py`
  - `_resolve_home` / `validate_workflow_store_root` — reject production
    `~/.hermes` and the repo source root.
  - `_atomic_write` — temp file + `os.replace`; a crashed write never leaves a
    half-written document.
  - `_FileLock` — `fcntl` advisory lock (ImportError-guarded fallback) so
    concurrent timeline appends do not interleave.
  - `_read_text_safe` — refuses symlinks; returns `None` on any error.
  - `_parse_document` — corrupt JSON → `None`; non-object JSON → `None`.
  - `_serialize` — rejects documents > 256 KiB.
  - `_MAX_TIMELINE_EVENTS` (1000), `_MAX_LIST_LIMIT` (100).

## Commands

```bash
./scripts/run_tests.sh \
  tests/test_dev_web_phase_3a_h1_workflow_store_hardening.py -- -q
```

## Findings

The store already satisfies every boundary. The hardening tests pin it:

- Store root is under `$HERMES_HOME/gateway/dev/workflow-store` with four
  subdirs (`workflows`, `executions`, `timelines`, `meta`); not under the repo,
  not under `~/.hermes`, not production.
- A symlinked document is refused; corrupt definition/execution JSON and
  corrupt JSONL lines return `None` / are skipped (never raised).
- Definition overwrite is atomic; the timeline is append-only and merges over
  the snapshot on load.
- `list_workflow_executions` is bounded to `_MAX_LIST_LIMIT`, clamps 0/negative
  limits, and skips corrupt entries.
- Invalid workflow ids are rejected on save (`ERROR_CORRUPT_DOCUMENT`); an
  oversized document is rejected (`ERROR_WRITE_FAILED`).
- No persisted document carries `rawArguments` / `fullTokenHash` / `tokenSecret`
  / `plainToken` / `apiKey` / `fileContent` / `absolutePath` / a callable repr /
  a production path / `state.db`.

## Fixes

None required — no implementation defect found.

## Status

PASS.

## Residual risk

None (P0 = 0, P1 = 0). The advisory lock is best-effort on non-Unix platforms
(fallback to atomic-replace-only), which is acceptable because dev WebUI runs
on a single operator workstation bound to `127.0.0.1`.
