# Phase 3B-H1 — provider_real_* Audit Security Hardening

- **Provider Audit Security ID:** PROVIDER-AUDIT-3B-H1-001
- **Lens:** 8 (provider_real_* Audit No-leak Boundary)
- **Status:** PASS

## Scope

The `provider_real_*` audit writers
(`hermes_cli/dev_web_provider_real_audit.py`). Phase 3B-H1 hardens the guarantee
that no secret may ever reach an audit record.

## Frozen Event Catalogue (11)

`provider_real_request_previewed`, `provider_real_request_blocked`,
`provider_real_request_started`, `provider_real_request_completed`,
`provider_real_request_failed`, `provider_real_response_redacted`,
`provider_real_tool_call_requested`, `provider_real_tool_call_blocked`,
`provider_real_tool_call_completed`, `provider_real_budget_blocked`,
`provider_real_rate_limit_blocked`.

## Verified Invariants

- **Defensive re-redaction at the WRITE boundary:** even a hand-built event with
  a secret-bearing payload is redacted before serialization; the written line
  carries `[REDACTED]` and never the raw secret.
- **Value-free safeMetadata:** `apiKeySource` (`env` only),
  `apiKeyPresent` (bool), `apiKeySourceDetail` (`env_present` / `env_missing`),
  `allowlistedBaseUrl` (host only), `modelName`, `adapterName`,
  `externalNetworkCalled`. Never the key value.
- **Non-JSON values collapse:** callables/objects in a payload become
  `<non_json_value>` — never a repr/type name.
- **Every written line carries `redactionApplied=true`.**
- **Never present in audit:** API key, Authorization header, Bearer token, raw
  prompt/response body, raw arguments, full tokenHash, plainToken, file content,
  callable repr, production path, `state.db`.
- **Write failure fails closed:** writing to `~/.hermes` is refused (returns
  `None`); a write failure never enables execution and never leaks.

## Evidence

- `tests/test_dev_web_phase_3b_h1_provider_audit_hardening.py`

## Residual Risk

- P0: none. P1: none.
