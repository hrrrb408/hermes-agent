# Phase 2D — Audit Security Boundary

## Unified sanitizer (closes the Phase 2A gap)

`dev_web_audit_sanitizer.py` is the single redaction surface for every audit
event entering the durable store. It replaces the per-writer defensive
sanitizers and closes the Phase 2A `str(object)` defense-in-depth issue.

Non-JSON-native values **never** use `str(value)`:

- callables / functions / classes / modules → `<non_json_value>`
- `bytes` / `bytearray` → `<bytes_redacted>`
- `Exception` → `<exception:ClassName>` (never the message)
- arbitrary objects → `<non_json_value>`
- residual Python repr fingerprints (` object at 0x`, `<function`, `<bound
  method`, `<class `, `<module `) inside strings → `[REDACTED]`

## Redaction coverage

Secret values (PEM blocks — RSA / EC / OpenSSH / PGP / encrypted — `sk-...`
tokens, `Bearer ...`, `Authorization:` headers, `api_key=...`, URL-embedded
credentials, bare HEX digests ≥ 32 chars) are redacted.

Forbidden field stems are redacted regardless of value:
`api_key`, `token`, `secret`, `password`, `credential`, `cookie`,
`private_key`, `client_secret`, `access_token`, `refresh_token`, `rawArguments`,
`tokenHash`, `fullTokenHash`, `rawToken`, `confirmationToken` (the secret, not
the `confirmationTokenId` correlation id), `fileContent`, `providerPayload`, …

For OUTPUT, `strip_forbidden_keys()` drops forbidden key **names** entirely —
not even a redacted key name is surfaced.

## Store confinement

The audit store root is confined to the dev `HERMES_HOME` and is never under:

- the repository (`hermes-agent-dev`)
- `~/.hermes` (production home, exact + subtree)
- any `state.db`

## Cursor safety

Cursor tokens carry only `lastSequence`, `direction`, `queryHash`, `issuedAt`.
They never carry a path, an absolute path, an index internal, a secret, or a
full token hash.

## API output guarantees

The enhanced route never exposes: raw arguments, plain token, `tokenSecret`,
full `tokenHash`, API key, file content, callable / function repr, production
path, or the audit store's absolute path.

## Commit hygiene

No audit store files, token store files, rollback manifest files, runtime audit
JSONL files, or `.claude` files are committed. `.gitignore` asserts these
patterns as defense-in-depth.

## Production isolation

- No production rollout.
- No `~/.hermes` access.
- No production `state.db` access.
- No shell command execution, database mutation, or external service write.
- Production Gateway PID is never affected.
