# Phase 2C-H1 — File-backed Confirmation Token TTL

## Token model

A confirmation token is `"<tokenId>.<secret>"`:

- `tokenId` is public (`cft_<hex>`); the store file is named after it.
- `secret` is a random URL-safe string handed only to the client.
- The store records `tokenHash = sha256(secret + payloadDigest + scope +
  createdAt)` — it **never stores the plain secret**. Verification recomputes
  the hash from the submitted secret, proving the caller knows it without the
  server persisting it.

Store path: `$HERMES_HOME/gateway/dev/tool-confirmation-tokens/<tokenId>.json`.
Never the repo tree, `~/.hermes`, production state dir, `state.db`, or `.claude/`.

## Record fields

`tokenId`, `tokenHash`, `scope`, `payloadDigest`, `argumentDigest`, `toolId`,
`operation`, `createdAt`, `expiresAt`, `usedAt`, `status`, `metadata`. The
plain secret, raw arguments, file content, API keys, and the full raw provider
request are **never** written.

## Scopes

| Scope | Use | Default TTL |
|-------|-----|-------------|
| `write_execute` | execute a controlled write | 10 min |
| `rollback_execute` | execute a controlled rollback | 10 min |
| `provider_write_preview_confirm` | confirm a provider write preview | 5 min |

Max TTL cap: **30 min**. Tokens are scope-isolated: a write token cannot
verify for rollback and vice-versa; a provider preview token cannot execute a
write or rollback.

## Lifecycle + blocked reasons

- `blocked_confirmation_token_not_found` — token id not in the store.
- `blocked_confirmation_token_invalid` — malformed token or wrong secret.
- `blocked_confirmation_token_expired` — `now > expiresAt`.
- `blocked_confirmation_token_already_used` — `status == used`.
- `blocked_confirmation_token_scope_mismatch` — wrong scope.
- `blocked_confirmation_token_digest_mismatch` — wrong argument digest.

## Single-use persistence

`mark_confirmation_token_used` rewrites the file with `status=used` +
`usedAt`. The used flag survives process restarts, so the same token can never
execute twice. The write-level wrappers map the granular store reasons
(`blocked_write_confirmation_already_used`, `blocked_write_confirmation_scope_mismatch`).

## Cleanup

`cleanup_expired_confirmation_tokens` deletes only expired token files. It
never follows symlinks, never deletes non-token files (validated by the
`cft_<hex>` filename convention), and never touches production paths.

## Audit

Token lifecycle events: `confirmation_token_created`, `confirmation_token_verified`,
`confirmation_token_expired`, `confirmation_token_used`,
`confirmation_token_replay_blocked` (written to `tool-write-audit.jsonl`). The
audit view never includes the secret or the full tokenHash (only a short
prefix in the redacted view).
