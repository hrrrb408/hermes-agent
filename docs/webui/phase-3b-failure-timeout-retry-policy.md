# Phase 3B Failure / Timeout / Retry Policy

## Document Information

| Field | Value |
|-------|-------|
| Phase | 3B Planning |
| Title | Real Provider Failure / Timeout / Retry Policy (Frozen) |
| Status | Frozen |
| Date | 2026-06-16 |
| Branch | `dev-huangruibang` |
| Planning ID | `PHASE-3B-PLANNING-001` |
| Policy ID | `PHASE-3B-FAILURE-POLICY-001` |

> Companion to [phase-3b-planning.md](phase-3b-planning.md). This document freezes
> how a future Phase 3B implementation must bound, retry, classify, and recover
> from real-provider failures. **No real call is made in this planning phase.**

---

## 1. Principle

Every real-provider call is **bounded**, **classified**, and **audited**. Failures
are never silently swallowed, never retried into a storm, and never surfaced as a
raw stack trace. A failure always **safe-degrades**: no side effect, an audited
reason, and a safe UI state.

---

## 2. Timeouts (frozen)

| Timeout | Rule |
|---------|------|
| Connect timeout | bounded, derived from `HERMES_PROVIDER_TIMEOUT_SECONDS` (clamped to a safe min/max) |
| Read timeout | bounded, separate from connect timeout |
| Total request timeout | a hard ceiling per request; exceeding it fails the call |
| Invalid timeout config | blocked with `blocked_provider_timeout_invalid` before any call |

Each timeout failure is classified as a **transient** failure (retryable, see
below, subject to the retry cap) and audited as `provider_real_request_failed`.

---

## 3. Retry Policy (frozen)

| # | Rule |
|---|------|
| 1 | Max retries is capped (from `HERMES_PROVIDER_MAX_RETRIES`, clamped). |
| 2 | Retry **only** on safe-transient errors (connect timeout, read timeout, 5xx, 429 with a backoff). |
| 3 | **No retry** on authentication failure (401 / 403) — classify and fail fast. |
| 4 | **No retry** on budget exceeded — `blocked_provider_budget_exceeded`. |
| 5 | **No retry** on policy-blocked requests — surface the `blocked_provider_*` reason. |
| 6 | **No retry** on response-too-large — `blocked_provider_response_too_large`. |
| 7 | **No retry** on secret-detected — `blocked_provider_secret_detected`. |
| 8 | Retries use bounded exponential backoff with a jitter ceiling (deterministic bounds, no unbounded growth). |
| 9 | Every retry is audited; the final outcome is one terminal event. |

A retry storm is structurally impossible: the cap is hard, the backoff is bounded,
and the non-retryable classes short-circuit immediately.

---

## 4. Response-Size Limit (frozen)

- A maximum response byte size is enforced at read time.
- Oversize → the read is aborted, classified as a **non-retryable** failure, and
  audited as `provider_real_request_failed` with `blockedReason =
  blocked_provider_response_too_large`.
- No partial oversize body is persisted.

---

## 5. Malformed-Payload Fallbacks (frozen)

| Situation | Fallback |
|-----------|----------|
| Malformed JSON response | abort; classify as non-retryable `provider_real_request_failed`; never `eval` / `exec` repair |
| Tool-call schema mismatch | block the offending call (`blocked_provider_tool_call_not_allowed`); do not execute |
| Unknown tool id | block (`blocked_provider_tool_call_not_allowed`); never fall back to a write tool |
| Provider-requested URL fetch | block (`blocked_provider_external_url_not_allowed`) |
| Secret in request / response / args | block (`blocked_provider_secret_detected`) |

No fallback ever **executes** anything unvalidated, and no fallback ever
**repairs** a payload by interpreting it (no `eval` / `exec` / dynamic parse).

---

## 6. Provider-Unavailable Fallback (frozen)

- DNS failure, connection refused, TLS failure, or a 5xx storm exhausting the
  retry cap → `provider_real_request_failed`.
- The system **safe-degrades**: returns a blocked / error result, no side effect,
  audited, and a safe UI state.
- The fake adapter (offline baseline) is unaffected and remains available for
  tests / smoke / local verification.

---

## 7. Audit of Failures (frozen)

- Every failure emits exactly one terminal audit event
  (`provider_real_request_failed`, or a specific `…_blocked` variant).
- The event records `status`, `blockedReason`, `externalNetworkCalled`, the
  bounded `usageSummary` (if any), and `safeMetadata` — **never** a raw body,
  header, or stack trace.
- The internal stack trace is **not** placed in the audit record (it stays in the
  dev-only server log at debug level at most, and is never sent to the UI).

---

## 8. UI Failure Representation (frozen)

- The UI shows a **safe** blocked / error state with the `blocked_provider_*`
  reason and a short human label.
- The UI **never** shows a raw stack trace, a raw provider body, a header, or a
  secret.
- A retry (if any) is operator-initiated, not automatic in the UI.

---

## 9. Acceptance (for a future Phase 3B implementation)

1. Connect / read / total timeouts are all bounded and enforced.
2. Retries are capped; non-retryable classes short-circuit.
3. Response size is bounded; oversize → blocked.
4. Malformed / schema-mismatch / unknown-tool / secret payloads are blocked, not
   executed or repaired.
5. Every failure is audited with a terminal event and a `blockedReason`.
6. The UI shows no raw stack trace, body, header, or secret.

---

## 10. Cross-References

- [Phase 3B planning](phase-3b-planning.md)
- [Phase 3B network boundary](phase-3b-network-boundary.md)
- [Phase 3B cost / rate-limit policy](phase-3b-cost-and-rate-limit-policy.md)
- [Phase 3B audit model](phase-3b-provider-audit-model.md)
- [Phase 3B request / response schema](phase-3b-provider-request-response-schema.md)
