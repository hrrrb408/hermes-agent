# Phase 3B Provider Redaction & No-Leak Policy

## Document Information

| Field | Value |
|-------|-------|
| Phase | 3B Planning |
| Title | Real Provider Redaction & No-Leak Policy (Optional) |
| Status | Frozen |
| Date | 2026-06-16 |
| Branch | `dev-huangruibang` |
| Planning ID | `PHASE-3B-PLANNING-001` |
| Policy ID | `PHASE-3B-NO-LEAK-POLICY-001` |

> Companion to [phase-3b-api-key-and-secret-strategy.md](phase-3b-api-key-and-secret-strategy.md)
> and [phase-3b-provider-audit-model.md](phase-3b-provider-audit-model.md). This
> optional policy consolidates every no-leak invariant the future Phase 3B
> implementation must satisfy. It is analysis only — no key is read here.

---

## 1. Principle

The real-provider path must inherit the Phase 2B-H1 / Phase 2E-H1 no-leak closure
**unchanged** and extend it to the new surfaces (request preview, response
summary, cost badge, blocked-reason panels). Nothing secret may ever reach an
audit record, a log line, a UI element, a doc, or a committed file.

---

## 2. What Must Never Leak (forbidden values)

| Value | Why |
|-------|-----|
| API-key value | account compromise / unauthorized spend |
| Authorization / API-key header | same |
| Raw bearer token | replay |
| Full `tokenHash` | replayable metadata |
| Raw confirmation token | replay |
| Raw tool arguments containing a secret | leak |
| Callable / function / bound-method repr | internal exposure |
| Production path (`~/.hermes`, production `state.db`) | production access |
| Raw provider request body with a secret | leak |
| Raw provider response body | leak / oversize |
| Full secret-bearing URL (query/path) | leak |
| Partial key prefix (`sk-…****`) | still a leak |

---

## 3. Redaction Mechanisms (reused + extended)

The Phase 2B-H1 sanitizer is the single redaction engine. It runs:

- on every persisted document (workflow state, cost counters);
- on every audit event (`build_provider_audit_event` re-redacts the whole event);
- on every API response and UI-bound payload.

Patterns (frozen, widened in Phase 2B-H1):

- value patterns: `sk-…`, `Bearer …`, `Authorization: …`,
  `-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----` → `[REDACTED]`;
- forbidden field stems: `token`, `secret`, `password`, `auth`, `api_key`,
  `authorization`, `apikey`, `privatekey`, `credential` → value `[REDACTED]`;
- non-JSON-native values → `<non_json_value>` (never repr / type name);
- nesting depth capped at 8.

---

## 4. Surface-by-Surface No-Leak Rules

| Surface | Rule |
|---------|------|
| Provider request envelope | never carries `apiKey` / Authorization / raw secret / token / production path |
| Provider response envelope | bounded `contentSummary`; no raw body / header / secret |
| Provider audit record | `safeMetadata` carries only value-free markers; sanitizer re-redacts |
| Server log | only `apiKeySourceDetail` = `env_present` / `env_missing`; never the value; no stack trace to UI |
| Cost / budget badge | safe metadata only (caps, remaining, model name); no spend-leaking precision |
| Blocked-reason panel | `blocked_provider_*` reason + short label; no raw body / stack / secret |
| Docs / examples | placeholders only (`OPENAI_API_KEY=<set in your env>`, `Bearer <REDACTED>`) |

---

## 5. Active Block on Secret Detection

If the sanitizer detects a secret in the request, response, or arguments, the
round-trip is **blocked** with `blocked_provider_secret_detected` — the secret is
never persisted, never returned, and never reaches the UI beyond the redacted
reason.

---

## 6. Verification (for a future Phase 3B implementation)

1. A parametrized no-leak test sweeps the real-provider surface (request / response
   / audit / UI / blocked panels) for every forbidden value class.
2. The sanitizer patterns are asserted to catch every standard PEM variant and
   every forbidden stem (inheriting the Phase 2B-H1 Lens 6 test set).
3. A route-governance + no-leak test runs in the gate before every push.
4. Boundary searches sweep the diff for `sk-…` / `api_key` / `Bearer` / PEM /
   `Authorization` / callable repr / production path, allowing them only inside
   safety statements, negations, risk descriptions, and blocked reasons.

---

## 7. Cross-References

- [Phase 3B planning](phase-3b-planning.md)
- [Phase 3B API-key & secret strategy](phase-3b-api-key-and-secret-strategy.md)
- [Phase 3B audit model](phase-3b-provider-audit-model.md)
- [Phase 3B request / response schema](phase-3b-provider-request-response-schema.md)
- [Phase 3B read-only provider threat model](phase-3b-readonly-provider-threat-model.md)
- [Phase 3B security risk register](phase-3b-security-risk-register.md)
- [Phase 2B-H1 provider round-trip hardening](phase-2b-h1-provider-roundtrip-hardening.md)
