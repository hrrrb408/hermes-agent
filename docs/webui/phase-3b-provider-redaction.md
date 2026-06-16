# Phase 3B Provider Redaction (Implementation)

| Field | Value |
|-------|-------|
| Phase | 3B |
| Status | Implemented |
| Module | `hermes_cli/dev_web_provider_real_redaction.py` |

Inherits the Phase 2B-H1 sanitizer semantics and extends them to the real
surfaces (request preview, response summary, cost badge, blocked-reason panels).

## Value patterns (frozen)

`sk-…`, `Bearer …`, `Authorization: …`, and every PEM private-key variant
(`-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----`) → `[REDACTED]`.

## Field-name rule (with the token-count precision rule)

A field whose normalized name contains a secret stem
(`token`, `secret`, `password`, `auth`, `apikey`, `privatekey`, `credential`)
has its **string** value redacted to `[REDACTED]`. An **integer** value under
such a name is a token COUNT (`maxTokens`, `promptTokens`, `totalTokens`,
`tokensToday`) and is **preserved** — it is safe metadata, not a secret.

This closes the false-positive where `maxTokens` would otherwise be redacted,
while still redacting `accessToken` / `api_key` string values.

## Secret detection → block

`contains_secret()` drives the `blocked_provider_secret_detected` block: a
string matching a secret value pattern, OR a non-empty string under a
secret-bearing field name, blocks the round-trip before any persistence.

## Other rules

- nesting depth capped at 8 (deeper → None);
- non-JSON-native values (callables, objects) → `<non_json_value>` (never the
  repr / type name);
- the whole projection is re-redacted before persistence or return.
