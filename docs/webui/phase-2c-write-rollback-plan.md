# Phase 2C — Write Rollback Plan

## Status

Phase 2C generates a rollback **manifest** and **preview** for every
non-readback write. Automatic rollback **execution** is deferred to Phase
2C-H1 / Phase 2D (a P2 item). The manifest carries enough metadata to drive a
future automatic restore.

## Manifest fields

| Field | Meaning |
|-------|---------|
| `rollbackId` | opaque id (`wrbk_<hex>`) |
| `operation` | `create_or_replace` / `append` / `patch` |
| `targetRelativePath` | sandbox-relative target |
| `beforeExists` | whether the target existed before the write |
| `beforeHash` / `afterHash` | SHA-256 of before/after content |
| `beforeSizeBytes` / `afterSizeBytes` | sizes |
| `restoreMode` | `delete_created_file` \| `restore_previous_content` \| `none` |
| `restorePreview` | bounded, redacted textual description of the restore |
| `createdAt` | ISO-8601 timestamp |

The manifest deliberately does **not** embed the full prior content (which
could be large or secret-bearing). A future automatic executor would restore
from `beforeHash` + a content backup taken at write time.

## Restore modes

- `delete_created_file` — the target did not exist before; rollback deletes it.
- `restore_previous_content` — the target existed; rollback restores the
  previous content (identified by `beforeHash`).
- `none` — the readback tool performs no write; no rollback is required.

## Validation + audit redaction

`validate_rollback_manifest` checks required fields, restore-mode validity,
and secret-free content. `redact_rollback_manifest_for_audit` re-sanitizes the
manifest (strips secret value patterns, sets `redactionApplied=true`) before it
is persisted to the write audit JSONL.

The manifest is also surfaced in the execute result (`rollbackId`,
`rollbackAvailable`) and recorded by a `write_rollback_manifest_built` audit
event.
