# Phase 2C-H1 — Security Boundary

## Invariants preserved from Phase 2C

Every Phase 1G/2A/2B/2C safety invariant holds:

- `STATIC_ALLOWLIST` stays frozen at six read-only tools.
- Writes happen only inside the dev sandbox root.
- No shell command execution, no database mutation, no external service write,
  no production rollout, no `~/.hermes` access, no production `state.db` access.
- No raw token / full tokenHash / raw arguments / secrets / callable repr
  exposed in responses or audit.

## New hardening (Phase 2C-H1)

### Confirmation tokens

- The plain token secret is **never stored**; the store keeps only a hash.
- The full tokenHash is **never exposed** to the client or audit (only a short
  prefix in the redacted audit view).
- Tokens are **scope-isolated**: `write_execute` ≠ `rollback_execute` ≠
  `provider_write_preview_confirm`. A provider preview token cannot execute a
  write or rollback.
- TTL enforced (default 10/10/5 min; cap 30 min); expired tokens blocked.
- Single-use persisted across process restarts; replay blocked.

### Rollback execution

- Loads only system-generated stored manifests (no user-authored manifests).
- `rollbackId` validated; no path traversal in the store.
- Rollback target must resolve inside the sandbox; symlink escape and
  outside-sandbox targets blocked.
- Current-hash verification at preview AND execution time (fail-closed on
  concurrent change).
- Already-executed manifests refuse re-execution.
- `beforeContent` (needed for restore) is stored internally only, never exposed
  via API or audit.

## Store locations (dev HERMES_HOME only)

- `$HERMES_HOME/gateway/dev/tool-confirmation-tokens/<tokenId>.json`
- `$HERMES_HOME/gateway/dev/tool-write-rollback-manifests/<rollbackId>.json`
- `$HERMES_HOME/gateway/dev/audit/tool-write-audit.jsonl`

None of these are committed (verified by the commit guard; they live under
`HERMES_HOME`, outside the repo). Cleanup is bounded, symlink-safe, and
production-safe.

## Source inspection

`tests/test_dev_web_phase_2c_h1_write_hardening.py` verifies the new modules
introduce no `subprocess`/`sqlite3`/`requests`/`httpx`/`urllib` imports and no
production IO. Route governance stays 34/34/5/0/1/1.
