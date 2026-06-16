# Phase 3B-Live-Enablement — Secret Read Policy

| Field | Value |
|-------|-------|
| Phase | 3B-Live-Enablement (Planning) |
| Title | Strict Manual Real Provider Enablement — Secret Read Policy |
| Status | Frozen (docs-only planning; live enablement **not started**) |
| Date | 2026-06-17 |
| Planning ID | `PHASE-3B-LIVE-ENABLEMENT-PLANNING-001` |

## 1. Principle

A real API key, when live enablement is authorized in a future phase, may be read
**only** from the environment. Its value never persists, never traverses a store,
never appears in audit / logs / exceptions / responses / UI / tests.

> **This planning phase does not read any real API key.** This policy describes
> the constraints the future implementation must satisfy.

## 2. API-key source — allow / forbid

| Source | Allowed |
|--------|---------|
| Environment variable (`OPENAI_API_KEY`) | **yes (future)** |
| UI input control | **no** |
| File read | **no** |
| Workflow store | **no** |
| Audit store | **no** |
| Docs / git-tracked files | **no** |
| Frontend (localStorage / sessionStorage / Pinia) | **no** |
| Backend runtime store (beyond the live process local) | **no** |

## 3. Lifecycle in the live process (future)

1. Read the env var once into a local.
2. Attach it to a single outbound `Authorization` header on the single approved
   request.
3. Drop the local and the header immediately after the call returns or fails.
4. Never copy the value into any other structure.

## 4. Where the value must never appear

```
audit events
logs
exceptions / tracebacks
HTTP responses
UI rendering
test snapshots
git commits
```

## 5. Allowed secret-state audit fields

Secret-state audit may record **only**:

```
keySource = environment
keyState = env_present | env_missing
keyFingerprint = disabled
keyValue = never
authorizationHeader = never
```

`keyValue` and `authorizationHeader` are **never** recorded; their presence is a
no-leak violation and a P0 stop condition.

## 6. API-key environment variable

The API-key environment variable for the first live test is:

```
OPENAI_API_KEY
```

This planning document **names** the variable but **does not read its value** and
does not check whether it is set.

## 7. Blocked reasons (secret layer)

```
blocked_live_secret_state_checked   (audited; no value)
blocked_provider_secret_detected    (reuse — secret detected in prompt/response/args)
```

A detected secret in the request preview, response, or tool args fails closed
and fires the kill switch.

## 8. Reuse of Phase 2B-H1 / Phase 3B redaction

The future implementation reuses the Phase 2B-H1 / Phase 3B redaction + secret
detection patterns. Token COUNTS (`maxTokens`, `promptTokens`, `totalTokens`)
remain safe and preserved; token VALUES and any key-bearing string are redacted.

## 9. Cross-references

- [Phase 3B redaction](phase-3b-provider-redaction.md)
- [Phase 3B-H1 secret redaction](phase-3b-h1-provider-secret-redaction.md)
- [Phase 3B-Live-Enablement audit policy](phase-3b-live-enablement-audit-policy.md)
