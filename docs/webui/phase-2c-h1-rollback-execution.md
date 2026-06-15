# Phase 2C-H1 — Rollback Execution

## Overview

Phase 2C generated rollback manifests at write time but did not execute them.
Phase 2C-H1 adds the `dev_sandbox_rollback_execute` tool and a full controlled
rollback chain. The write chain now **persists** each manifest to the rollback
store; rollback execution loads a manifest by id and undoes the write.

## Manifest store

`$HERMES_HOME/gateway/dev/tool-write-rollback-manifests/<rollbackId>.json`.

- `rollbackId` is validated (`wrbk_<hex>`, no slash / dot-dot / NUL) and used
  only as a filename — no path traversal.
- The record carries the public manifest fields plus an internal `beforeContent`
  (only when the target previously existed) so `restore_previous_content` can
  restore it. `beforeContent` is never returned by the public list/load safe
  view and never written to audit.
- Symlinked manifest files are refused.

## Execution chain

`dispatch_rollback_tool(rollback_id, context, hermes_home)` runs:

1. write-enablement gate
2. load + validate manifest (tamper check)
3. already-executed check
4. re-derive rollback plan (sandbox target validation + current-hash check)
5. argument-digest verification
6. rollback-scoped confirmation token verification (`scope=rollback_execute`)
7. mark token used (single-use)
8. pre-execution audit
9. re-verify current hash at execution time (fail-closed on concurrent change)
10. execute: `delete_created_file` (unlink a regular in-sandbox file) or
    `restore_previous_content` (atomic write of `beforeContent`, verify final
    hash == `beforeHash`)
11. mark manifest executed (persistent single-use rollback)
12. post-execution audit

## Restore modes

- `delete_created_file` — only deletes a file the original write created; only
  inside the sandbox; refuses if current hash ≠ `afterHash`, target escapes the
  sandbox, or target is a symlink.
- `restore_previous_content` — writes the previous content back; only inside
  the sandbox; refuses on current-hash mismatch, `beforeHash` mismatch, escape,
  or symlink.

## Blocked reasons

`blocked_rollback_manifest_not_found`, `blocked_rollback_already_executed`,
`blocked_rollback_current_hash_mismatch`, `blocked_rollback_manifest_tampered`,
`blocked_rollback_target_escape`, `blocked_rollback_symlink_escape`,
`blocked_rollback_confirmation_required`, `blocked_rollback_digest_mismatch`,
`blocked_rollback_write_not_enabled`, `blocked_rollback_forbidden_target`.

## API (no new route)

- `POST /tools/dry-run` `mode=rollback_preview` `{rollbackId}` → preview +
  rollback-scoped token (optionally `includeManifestList` for a UI list).
- `POST /tools/execute` `mode=rollback` `{rollbackId, confirmationToken,
  argumentDigest}` → execution result.

## Audit

`rollback_preview_generated`, `rollback_execution_blocked`,
`rollback_pre_execution_audit`, `rollback_handler_called`,
`rollback_post_execution_audit`, `rollback_manifest_marked_executed` (written
to `tool-write-audit.jsonl`, queryable via `auditKind=write`). No token secret,
no `beforeContent`, no callable repr.
