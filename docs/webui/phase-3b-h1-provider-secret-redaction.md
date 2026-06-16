# Phase 3B-H1 — Provider Secret / Authorization Redaction Hardening

- **Provider Secret Redaction ID:** PROVIDER-SECRET-3B-H1-001
- **Lens:** 2 (API Key / Secret / Authorization Redaction Boundary)
- **Status:** PASS

## Scope

The redaction engine (`hermes_cli/dev_web_provider_real_redaction.py`) is the
single authority over what may leave the provider surface. Phase 3B-H1 hardens
its verification with adversarial, exhaustive assertions.

## Verified Invariants

- **Secret value patterns:** `sk-…` (8+ trailing chars), `Bearer …`,
  `Authorization: …`, and every PEM private-key variant (bare / RSA / EC /
  OPENSSH / DSA / ENCRYPTED) are flagged. Short `sk-abc` is NOT flagged
  (avoids over-redacting the literal token stem).
- **Field-name redaction:** a STRING value under a secret-bearing field name
  (`api_key`, `apikey`, `accessToken`, `refresh_token`, `client_secret`,
  `password`, `secret`, `credential`, `authToken`, `privateKey`, `tokenHash`,
  `plainToken` …) is redacted to `[REDACTED]`. An empty string is safe (preserved).
- **Token-count precision:** INTEGER / bool / None values under a
  secret-bearing name (`maxTokens`, `promptTokens`, `completionTokens`,
  `totalTokens`, `tokensToday`) are COUNTS and are PRESERVED, never redacted.
- **Non-JSON values:** callables, objects, lambdas, sets collapse to
  `<non_json_value>` — NEVER the repr / type name / `<function …>` /
  `<bound method …>` / `object at 0x…`.
- **Depth bound:** nesting capped at 8; deeper leaves are dropped.
- **Blocking:** a detected secret in request/response/arguments drives
  `blocked_provider_secret_detected` — the secret is never persisted, never
  returned, never reaches the UI beyond the redacted reason.
- **No full tokenHash / raw token leak** in any projection.

## Evidence

- `tests/test_dev_web_phase_3b_h1_provider_redaction_hardening.py`
- The written audit file (`provider-roundtrip-audit.jsonl`) never carries a raw
  secret — verified by the audit no-leak hardening test.

## Residual Risk

- P0: none. P1: none.
