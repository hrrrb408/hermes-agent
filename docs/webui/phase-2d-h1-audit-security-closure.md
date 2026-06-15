# Phase 2D-H1 — Audit Security Closure

## Identification

- Security Closure ID: `AUDIT-SECURITY-CLOSURE-2D-H1-001`
- Hardening ID: `HARDENING-2D-H1-001`
- Evidence: `tests/test_dev_web_phase_2d_h1_audit_security.py`,
  `tests/test_dev_web_phase_2d_audit_security.py`,
  `tests/test_dev_web_phase_2d_audit_sanitizer.py`; live smoke
  `phase2d_audit_store_indexing`.

## 1. Sanitizer adversarial review

The unified sanitizer is the single redaction surface for every audit event.
Adversarial matrix verified (`sanitize_audit_value` / `sanitize_audit_event`):

| Input class | Outcome |
|-------------|---------|
| callable / lambda | `<non_json_value>` |
| function / module / class | `<non_json_value>` |
| object instance | `<non_json_value>` |
| bound method | `<non_json_value>` |
| bytes / bytearray | `<bytes_redacted>` |
| Exception | `<exception:ClassName>` (no message) |
| string containing `<function …>` / `<bound method …>` / `object at 0x…` | scrubbed / `[REDACTED]` |
| `sk-…` token, `Bearer …`, `Authorization: …`, `api_key=…` | `[REDACTED]` |
| PEM private key block (RSA / EC / OPENSSH / generic) | `[REDACTED]` |
| git-URL credential (`https://user:pass@host`) | `[REDACTED]` |
| bare hex digest ≥ 32 chars (full tokenHash) | `[REDACTED]` |
| short hex correlation id | preserved |
| forbidden field name (api_key, apiKey, password, secret, credential, tokenSecret, confirmationToken, rawArguments, rawArgs, arguments, fileContent, rawfileContent, fullTokenHash, tokenHash, plainToken, access_token, refresh_token, cookie, session, private_key, providerPayload, …) | value → `[REDACTED]` |
| production path (`/Users/huangruibang/.hermes`, `~/.hermes`, `state.db`) | `[REDACTED]` |

`confirmationTokenId` and `tokenId` are explicitly allowed correlation ids
(not secrets).

**str(object) / repr(object) / default=str fallback:** closed. Source grep
confirms the non-JSON-native branch returns `NON_JSON_VALUE_SENTINEL`; no
`default=str` anywhere in the sanitizer module.

## 2. No-leak checks

- **On disk:** secrets, raw arguments, callable reprs, and `object at 0x…`
  fingerprints never appear in the JSONL segments (verified across all 7 audit
  kinds, each seeded with a secret-like payload).
- **In index files:** index files contain only `seq` / `id` / `seg` / `line`
  pointers — no secrets, no raw arguments.
- **In API output:** the store-mode response carries no `sk-…`, no password,
  no `rawArguments`, no `<function`, no `object at 0x`, no production path,
  no `state.db`.
- **In cursor tokens:** the token decodes to a strict whitelist
  (`v`, `lastSequence`, `direction`, `queryHash`, `issuedAt`); no path, secret,
  or index internal.

## 3. API output checks

`GET /api/dev/v1/tools/audit-events` (store mode) was exercised across all 7
audit kinds with secret-laden payloads; the output blob is secret-free,
raw-argument-free, and callable-repr-free. A corrupt line in the store yields
HTTP 200 with `skippedMalformed >= 1` — the API never crashes.

## 4. UI output checks

Live Playwright smoke (`phase2d_audit_store_indexing`, 9 tests) confirms the
Viewer surfaces the enriched store-mode shape, store / index status,
`redactionApplied`, cursor pagination, and a corruption-safe read path — with
no raw secret / token / callable / raw-args leak and the route remaining
read-only (POST → 405).

## 5. Runtime artifact checks

- `audit-store/`, `quarantine/`, `events/`, `indexes/` are runtime artifacts
  under the dev `HERMES_HOME` — never committed.
- Legacy JSONL artifacts (`tool-dry-run-audit.jsonl`, …),
  `tool-confirmation-tokens/`, `tool-write-rollback-manifests/`,
  `confirmation-tokens.jsonl` are gitignored.
- `git diff` boundary search returns no runtime artifacts, no secrets, no
  production access.
- `.claude/` is never committed.

## 6. Production isolation

- No `~/.hermes` access performed.
- No production `state.db` access performed.
- No production rollout.
- Production Gateway PID 28428 (count 1) observed read-only throughout;
  untouched by every test, the hardening script, and the smoke harness.
- Dev services bind `127.0.0.1` only; ports 5180 / 5181 free at start and end.

## 7. Fix log

One latent inconsistency closed (security-neutral): `_minimal_safe_event`
`sequence: -1` → `0` so the fallback event actually validates and can persist a
safe breadcrumb as documented (see
[hardening doc](phase-2d-h1-audit-storage-hardening.md#fix-log-product-code)).
No boundary was loosened; no field is newly accepted.

## Final security conclusion

**PASS.** The Phase 2D durable audit store leaks nothing: no secrets, no raw
arguments, no full token hashes, no callable / function reprs, no production
paths — on disk, in the index, in the API, in the Viewer, or in cursor tokens.
The `str(object)` fallback is closed. Runtime artifacts stay uncommitted.
Production is untouched.
