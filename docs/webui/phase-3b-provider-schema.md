# Phase 3B Provider Request / Response Schema (Implementation)

| Field | Value |
|-------|-------|
| Phase | 3B |
| Status | Implemented |
| Module | `hermes_cli/dev_web_provider_real_schema.py`, `hermes_cli/dev_web_provider_openai_compatible_schema.py` |

The controlled envelopes the rest of the system sees. The raw vendor wire
payload is **never** exposed: it is normalized with secrets redacted, sizes
bounded, and tool calls validated against the read-only allowlist.

## Request envelope (`ProviderRealRequest`)

Includes: `providerMode`, `providerName`, `model`, `requestId`,
`conversationId`, `workflowId`, `toolAllowlist`, `messages`, `maxTokens`,
`temperature`, `timeoutSeconds`, `redactionPolicy`, `auditRequired`.

Excludes (forbidden): `apiKey`, an Authorization header, a raw secret / token,
a full tokenHash, a production path, raw file content, a callable repr.

Bounds: message length ≤ 4000 chars; `maxTokens` ≤ 4096; `temperature` ∈ [0,1].

## Response envelope (`ProviderRealResponse`)

Includes: `requestId`, `responseId`, `providerName`, `model`, `status`
(completed | blocked | failed), `contentSummary` (bounded ≤ 1000 chars),
`toolCalls` (validated, allowlisted), `usageSummary` (prompt/completion/total
token counts), `finishReason`, `blockedReason`, `auditLinks`,
`redactionApplied`, `externalNetworkCalled`, `costEstimate`.

Excludes (forbidden): a raw secret, an API key, an Authorization header, a raw
token, a full tokenHash, a callable repr, an unbounded raw response body.

`externalNetworkCalled` is `true` only when a real call was actually made.

## OpenAI wire mapping

`OpenAIChatRequest.from_real_request()` builds the chat-completions payload
(model, messages, max_tokens, temperature, tools from the read-only allowlist,
tool_choice). `parse_openai_chat_response()` normalizes content + tool calls +
bounded usage, parsing the string tool-call arguments defensively (never
`eval`/`exec`); malformed arguments → empty dict; a missing `choices` array →
empty content.
