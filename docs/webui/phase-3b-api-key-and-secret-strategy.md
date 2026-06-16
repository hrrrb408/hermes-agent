# Phase 3B API Key & Secret Strategy

## Document Information

| Field | Value |
|-------|-------|
| Phase | 3B Planning |
| Title | Real Provider API-Key & Secret Handling Strategy (Frozen) |
| Status | Frozen |
| Date | 2026-06-16 |
| Branch | `dev-huangruibang` |
| Planning ID | `PHASE-3B-PLANNING-001` |
| Strategy ID | `PHASE-3B-SECRET-STRATEGY-001` |

> Companion to [phase-3b-planning.md](phase-3b-planning.md). This document freezes
> how a future Phase 3B implementation may obtain, carry, audit, and display a
> provider API key. **No API key is read in this planning phase.** No key value
> appears in this document — every key-like reference is a placeholder.

---

## 1. Core Principle

The provider API key is a **read-only input from the environment**. It is read
exactly once, used to set a single Authorization / API-key header on the outbound
HTTPS request, and **never** persisted, logged, audited, displayed, or committed
in any form. Every other representation of the key is a **redacted metadata
marker** (`env_present` / `env_missing`).

---

## 2. Source Rules (frozen)

| # | Rule |
|---|------|
| 1 | The API key **only** comes from an environment variable. |
| 2 | The API key is **never** accepted from the UI. |
| 3 | The API key is **never** stored in the workflow store. |
| 4 | The API key is **never** stored in the audit store. |
| 5 | The API key is **never** stored in the provider request audit record. |
| 6 | The API key is **never** stored in the provider response audit record. |
| 7 | The API key is **never** stored in frontend state. |
| 8 | The API key is **never** stored in `localStorage` / `sessionStorage`. |
| 9 | Docs examples use **placeholders only** — never a real key. |
| 10 | Every key-like field is **redacted** before any persistence or display. |
| 11 | Logs may record only the key **source state** (`env_present` / `env_missing`). |
| 12 | Logs **never** record the environment-variable value. |
| 13 | The Authorization / API-key header is **never** printed. |
| 14 | A raw bearer token is **never** stored. |
| 15 | The provider adapter hands only **redacted metadata** to the audit layer. |

---

## 3. Suggested Environment-Variable Surface

These are **future-implementation suggestions only**. They are **not read** in
this planning phase. They are documented so the future Phase 3B implementation
has a frozen contract to implement against.

```
HERMES_PROVIDER_MODE=disabled|fake|real
HERMES_PROVIDER_API_ENABLED=0|1
HERMES_PROVIDER_NAME=openai_compatible|anthropic_compatible|zai_compatible|openrouter_compatible
HERMES_PROVIDER_BASE_URL=<allowlisted base URL; redacted in audit>
HERMES_PROVIDER_MODEL=<safe string>
HERMES_PROVIDER_TIMEOUT_SECONDS=<bounded number>
HERMES_PROVIDER_MAX_RETRIES=<bounded number>
HERMES_PROVIDER_DAILY_BUDGET_CENTS=<bounded number>
```

The provider API-key env vars are referenced only as future-implementation
suggestions. **They are never read here:**

```
OPENAI_API_KEY
ANTHROPIC_API_KEY
ZAI_API_KEY
OPENROUTER_API_KEY
```

---

## 4. Read Semantics (future implementation)

- The adapter reads the key once per outbound request, directly from the
  environment, into a local variable that lives only for the duration of the
  HTTP call.
- The key is attached to the outbound request as a single header
  (`Authorization: Bearer …` for OpenAI-compatible; `x-api-key: …` for
  Anthropic-compatible). The header is set by the HTTP client and **never**
  captured into any application data structure.
- After the request completes (success, failure, timeout, or exception), the key
  reference is dropped. It is never assigned to a module-global, never cached in
  a store, and never serialized.

---

## 5. Audit & Log Representation (frozen)

The audit and log layers may only ever observe a **boolean presence marker** and
a **source label** — never the value.

| Observable | Allowed? | Example |
|------------|----------|---------|
| `apiKeySource` = `env` | yes | `"apiKeySource": "env"` |
| `apiKeyPresent` = `true` / `false` | yes | `"apiKeyPresent": true` |
| `apiKeySourceDetail` = `env_present` / `env_missing` | yes | `"apiKeySourceDetail": "env_present"` |
| The key value | **no** | — |
| The env-var name with a value | **no** | — |
| The Authorization / API-key header | **no** | — |
| A masked key prefix (`sk-…****`) | **no** | (a partial key is still a leak) |
| A hash of the key | **no** | (replayable metadata; out of scope) |

The sanitizer from Phase 2B-H1 enforces this defensively: it replaces
`sk-…`, `Bearer …`, `Authorization: …`, PEM private keys, and forbidden field
stems (`token`, `secret`, `password`, `auth`, `api_key`, `authorization`,
`apikey`, `privatekey`, `credential`) with `[REDACTED]` and collapses non-JSON
values to `<non_json_value>`. Phase 3B inherits this unchanged.

---

## 6. UI Representation (frozen)

- The UI **never** renders an API-key input control. No password field, no key
  text box, no key `v-model` binding, no paste target. (Inherit the Phase 2B-H1
  Lens 8 closure.)
- The UI **may** show a safe state badge: `key: env_present` or
  `key: env_missing` (boolean + source label only).
- The UI **never** displays a key value, a key prefix, a masked key, or a key
  hash.

---

## 7. Docs Representation (frozen)

- Docs examples use placeholders only: `OPENAI_API_KEY=<set in your env>`,
  `Authorization: Bearer <REDACTED>`, `sk-<REDACTED>`.
- No real key, no partial key, no key hash, and no key prefix may appear in any
  doc or example.

---

## 8. Failure Modes

| Situation | Behaviour |
|-----------|-----------|
| Key env var absent | Request blocked with `blocked_provider_api_key_missing`; `apiKeyPresent=false`; no network call. |
| Key env var present but empty | Treated as absent → `blocked_provider_api_key_missing`. |
| Key present but mode not `real` / not enabled | Blocked with `blocked_provider_real_not_enabled` / `blocked_provider_api_disabled`. |
| Audit / log accidentally receives the key | The sanitizer redacts it to `[REDACTED]` before persistence (defense-in-depth). |
| UI accidentally receives the key | Forbidden by contract; the no-leak test must fail the build if any key value reaches the UI. |

---

## 9. Acceptance (for a future Phase 3B implementation)

1. No API-key value appears in any audit record, log line, UI element, doc, or
   committed file.
2. The key is read from the environment only, on the request path only.
3. The UI exposes no API-key input control.
4. The audit layer observes only `apiKeySource` / `apiKeyPresent` /
   `apiKeySourceDetail` (value-free markers).
5. The Phase 2B-H1 sanitizer is reused unchanged and is covered by a no-leak
   test across the real-provider surface.

---

## 10. Cross-References

- [Phase 3B planning](phase-3b-planning.md)
- [Phase 3B scope freeze](phase-3b-provider-readonly-scope-freeze.md)
- [Phase 3B network boundary](phase-3b-network-boundary.md)
- [Phase 3B redaction & no-leak policy](phase-3b-provider-redaction-and-no-leak-policy.md)
- [Phase 3B request / response schema](phase-3b-provider-request-response-schema.md)
- [Phase 2B-H1 provider round-trip hardening](phase-2b-h1-provider-roundtrip-hardening.md)
- [Phase 2B provider audit model](phase-2b-provider-audit-model.md)
