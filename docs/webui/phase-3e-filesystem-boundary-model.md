# Phase 3E — Filesystem Boundary Model

| Field | Value |
|-------|-------|
| Phase | 3E (Planning) |
| Title | Real Plugin Runtime — Filesystem Boundary Model (Frozen, Design-only) |
| Status | Frozen (docs-only planning; Real Plugin Runtime **not started**) |
| Date | 2026-06-19 |
| Planning ID | `PHASE-3E-PLANNING-001` |
| Filesystem-Boundary ID | `PHASE-3E-FILESYSTEM-BOUNDARY-001` |

> This document designs — but does **not** implement — the filesystem boundary a
> future real plugin runtime would require. No implementation is authorized.

## 1. Position (deny-by-default)

```
No access to ~/.hermes
No access to production state.db
No access to repo secrets
No access to arbitrary local path
No access to the user plugin directory by default
No write outside an explicit dev sandbox
No read outside an explicit allowlist
No symlink traversal
No path traversal (.. smuggling)
No hidden-file read
No production path read
```

## 2. Allowed dev sandbox root

- A single explicit dev-sandbox root under the dev `HERMES_HOME` (e.g.
  `$HERMES_HOME/gateway/dev/runtime-sandbox`).
- The sandbox root is created on demand, scoped per-plugin where applicable, and
  destroyed on lifecycle end.
- Everything outside the sandbox root is unreachable by default.

## 3. Read allowlist

- An explicit, per-plugin read allowlist of paths *inside* the sandbox root.
- No read of: source repo, dotfiles, SSH keys, other projects, `/proc`, `/etc`,
  `~/.hermes`, production `state.db`.

## 4. Write allowlist

- An explicit, per-plugin write allowlist *inside* the sandbox root only.
- No write outside the sandbox root.
- No write to: any tracked source file, any config, any `state.db`, any
  `~/.hermes` path.

## 5. Denylist

```
~/.hermes (production home)
production state.db
source repo paths
dotfiles / SSH keys / credentials
system paths (/etc, /proc, /var, /usr outside sandbox)
any path resolved via symlink escape
any path after .. normalization that leaves the sandbox root
```

## 6. Symlink + path policy

- Symlinks are resolved and the **resolved** target is checked against the
  allowlist; a symlink that resolves outside the sandbox root is rejected.
- All paths are normalized (absolute, `..` collapsed, repeated `/` collapsed)
  before the boundary check.
- A path that, after normalization, is not strictly *inside* the sandbox root is
  rejected.
- TOCTOU: the resolved target is re-checked at the actual open / write call.

## 7. Audit + rollback

- Every filesystem access request is audited (`runtime_filesystem_access_*`;
  safe fields: pluginId, capabilityId, permissionClass, decision, blockedReason,
  devOnly, productionAllowed, redactionApplied). No raw path is written.
- Writes are auditable and reversible inside the sandbox; a rollback manifest is
  recorded for any write (reuses the Phase 2C-H1 rollback discipline).
- Audit failure is fail-closed.

## 8. Cross-references

- [Phase 3E planning](phase-3e-planning.md)
- [Phase 3E sandbox architecture](phase-3e-sandbox-architecture.md)
- [Phase 3E process isolation model](phase-3e-process-isolation-model.md)
- [Phase 3E network boundary model](phase-3e-network-boundary-model.md)
- [Phase 3E audit / redaction review](phase-3e-audit-redaction-review.md)
- [Phase 2C write sandbox security](phase-2c-write-sandbox-security.md)
- [Phase 2C-H1 rollback execution](phase-2c-h1-rollback-execution.md)
