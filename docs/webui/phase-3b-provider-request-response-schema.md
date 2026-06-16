# Phase 3B Provider Request / Response Schema

## Document Information

| Field | Value |
|-------|-------|
| Phase | 3B Planning |
| Title | Real Provider Request / Response Envelope Schema (Frozen) |
| Status | Frozen |
| Date | 2026-06-16 |
| Branch | `dev-huangruibang` |
| Planning ID | `PHASE-3B-PLANNING-001` |
| Schema ID | `PHASE-3B-PROVIDER-SCHEMA-001` |

> Companion to [phase-3b-planning.md](phase-3b-planning.md). This document freezes
> the future Phase 3B provider request / response envelope. The request envelope
> **never** carries an API key; the response envelope **never** carries a raw
> secret. These are the contracts a future implementation must implement against.

---

## 1. Design Principle

The provider request / response envelopes are the **controlled surface** the rest
of the system sees. The raw vendor wire payload is **never** exposed: it is
normalized into these envelopes with secrets redacted, sizes bounded, and tool
calls validated against the read-only allowlist. The envelopes extend the Phase
2B provider request / response shapes (which already proved the model) with the
fields a real round-trip needs.

---

## 2. Provider Request Envelope (frozen)

### Includes

| Field | Type | Notes |
|-------|------|-------|
| `providerMode` | `disabled` \| `fake` \| `real` | mirrors Phase 2B |
| `providerName` | `openai_compatible` \| `anthropic_compatible` \| `zai_compatible` \| `openrouter_compatible` | selected adapter |
| `model` | string | safe model id from config (not a secret) |
| `requestId` | string | correlation id, generated server-side |
| `conversationId` | string \| null | optional conversation binding |
| `workflowId` | string \| null | optional workflow step binding (Phase 3A) |
| `toolAllowlist` | string[] | bounded to the Phase 2A `STATIC_ALLOWLIST` |
| `messages` | object[] | sanitized message list; **no secrets** |
| `maxTokens` | integer | bounded per-request cap |
| `temperature` | number | bounded `[0, 1]` |
| `timeoutSeconds` | integer | bounded request timeout |
| `redactionPolicy` | string | the active redaction policy id |
| `auditRequired` | boolean | always `true` for the real path |

### Excludes (forbidden)

`apiKey`, an `Authorization` header, a raw secret, a raw token, a full
`tokenHash`, a production path, raw file content, a callable / function repr.

---

## 3. Provider Response Envelope (frozen)

### Includes

| Field | Type | Notes |
|-------|------|-------|
| `requestId` | string | echoes the request id |
| `responseId` | string | provider response id (or a derived id) |
| `providerName` | string | selected adapter |
| `model` | string | model used |
| `status` | `completed` \| `blocked` \| `failed` | terminal status |
| `contentSummary` | string | bounded, redacted text summary — **not** the raw body |
| `toolCalls` | object[] | validated, allowlisted tool calls only |
| `usageSummary` | object | bounded token usage (prompt / completion / total) |
| `finishReason` | string | provider finish reason |
| `blockedReason` | string \| null | a `blocked_provider_*` reason when blocked |
| `auditLinks` | string[] | audit event ids for this round-trip |
| `redactionApplied` | boolean | always `true` (redaction routine ran) |
| `externalNetworkCalled` | boolean | `true` only when a real call was actually made |
| `costEstimate` | object \| null | bounded cost estimate (cents) |

### Excludes (forbidden)

A raw secret, an API key, an `Authorization` header, a raw token, a full
`tokenHash`, a callable repr, an **unbounded** raw response body.

---

## 4. Tool-Call Sub-schema (frozen, reused from Phase 2B)

A provider tool call in the response is valid only if it passes
`validate_provider_tool_call`:

```
toolCall := {
  toolCallId: string,
  toolId: <must be in STATIC_ALLOWLIST>,
  args: object (JSON-native, sanitized, no secret / no path-injection),
  status: parsed | blocked | executed,
  blockedReason: string | null
}
```

Unknown, write-like, provider-recursive, malformed, oversized, or secret-bearing
calls are **blocked** (`blocked_provider_tool_call_not_allowed`) and never reach
the controlled execution chain. A validated call flows through the **existing**
chain unchanged (dry-run → digest → confirmation token → pre-audit → handler
lookup → dispatch → handler call → post-audit).

---

## 5. Content / Size Bounds (frozen)

| Bound | Rule |
|-------|------|
| `contentSummary` length | bounded (truncated; the raw body is never returned) |
| `toolCalls` count | bounded per round-trip |
| `messages` count / size | bounded |
| `args` nesting depth | ≤ 8 (mirrors the sanitizer) |
| response byte size | bounded (`blocked_provider_response_too_large`) |

---

## 6. Redaction Invariants (frozen)

The envelopes are produced **through** the Phase 2B-H1 sanitizer before any
persistence or return:

- `sk-…`, `Bearer …`, `Authorization: …`, and any PEM private key → `[REDACTED]`.
- Forbidden field stems (`token`, `secret`, `password`, `auth`, `api_key`,
  `authorization`, `apikey`, `privatekey`, `credential`) → `[REDACTED]`.
- Non-JSON-native values → `<non_json_value>` (never the repr / type name).
- Nesting depth capped at 8.

If the sanitizer detects a secret in the request or response, the round-trip is
blocked with `blocked_provider_secret_detected`.

Full detail: [phase-3b-provider-redaction-and-no-leak-policy.md](phase-3b-provider-redaction-and-no-leak-policy.md).

---

## 7. Determinism

- The `requestId` / `responseId` are generated server-side; they are stable for
  correlation and audit linkage.
- The envelope shape is the same across `fake` and `real` modes — only the
  adapter differs. This keeps tests deterministic: the fake adapter (offline)
  and the real adapter produce the **same envelope shape**, so contract tests
  can assert against the envelope without a real network call.

---

## 8. Acceptance (for a future Phase 3B implementation)

1. The request envelope never contains `apiKey` / Authorization / raw secret /
   raw token / full tokenHash / production path / raw file content / callable.
2. The response envelope never contains a raw secret / API key / Authorization /
   raw token / full tokenHash / callable / unbounded raw body.
3. Tool calls are validated against the read-only allowlist before execution.
4. Sizes are bounded; oversize → `blocked_provider_response_too_large`.
5. Secrets detected by the sanitizer → `blocked_provider_secret_detected`.
6. `externalNetworkCalled` is `true` only when a real call was actually made.

---

## 9. Cross-References

- [Phase 3B planning](phase-3b-planning.md)
- [Phase 3B scope freeze](phase-3b-provider-readonly-scope-freeze.md)
- [Phase 3B API-key & secret strategy](phase-3b-api-key-and-secret-strategy.md)
- [Phase 3B network boundary](phase-3b-network-boundary.md)
- [Phase 3B audit model](phase-3b-provider-audit-model.md)
- [Phase 3B redaction & no-leak policy](phase-3b-provider-redaction-and-no-leak-policy.md)
- [Phase 2B provider schema / API integration](phase-2b-provider-schema-api-integration.md)
- [Phase 2B provider audit model](phase-2b-provider-audit-model.md)
