# Phase 3B Read-only Provider Threat Model

## Document Information

| Field | Value |
|-------|-------|
| Phase | 3B Planning |
| Title | Read-only Real Provider Threat Model (Optional) |
| Status | Recorded |
| Date | 2026-06-16 |
| Branch | `dev-huangruibang` |
| Planning ID | `PHASE-3B-PLANNING-001` |
| Threat-Model ID | `PHASE-3B-THREAT-MODEL-001` |

> Companion to [phase-3b-planning.md](phase-3b-planning.md) and
> [phase-3b-security-risk-register.md](phase-3b-security-risk-register.md). This
> is an optional threat model for the future Phase 3B read-only real-provider
> path. It is analysis only — **no real call is made in this planning phase.**

---

## 1. Scope

The threat model covers the **single** new trust edge introduced by Phase 3B: the
outbound HTTPS round-trip from the dev WebUI backend to a real provider endpoint,
and the inbound provider response that flows back through the controlled chain.
Everything else (read-only tool execution, fake provider, sandbox write, rollback,
audit) is already modeled by Phase 2B-H1 / Phase 3A-H1 and is unchanged.

---

## 2. Trust Boundaries

| Boundary | Trusted side | Untrusted side |
|----------|--------------|----------------|
| TB-1 Operator → Dev WebUI | Operator (env-set key, explicit enablement) | WebUI treats all UI input as untrusted |
| TB-2 Dev WebUI → Provider | WebUI backend | The provider response (prompt-injection / hallucinated tool calls) |
| TB-3 Provider → Controlled chain | (validated tool calls only) | Raw provider output before validation |
| TB-4 Dev WebUI → `~/.hermes` | n/a | **Hard boundary — never crossed** |
| TB-5 Dev WebUI → Production Gateway | n/a | **Hard boundary — never crossed** |

The provider is **untrusted input**. Every value it returns is validated before
it can influence execution — exactly the Phase 2B contract, extended to the real
path.

---

## 3. Assets

| Asset | Protection |
|-------|------------|
| Provider API key | env-only; never persisted / logged / UI; sanitizer redacts |
| Operator messages | sanitized; bounded; no secret passthrough |
| Audit integrity | append-only / atomic; dev-home confined; redacted |
| Cost / budget | bounded caps; fail-closed counters |
| Dev sandbox | no provider write; provider can only request read-only tools |
| Production instance / gateway | hard boundary; never accessed / signaled |

---

## 4. Adversaries & Attacks

### ATK-01 — Prompt injection (provider → tool call)

- **Vector:** A provider response embeds instructions trying to make the system
  call a write / shell / arbitrary-URL tool.
- **Defense:** Every provider tool call is validated against the read-only
  `STATIC_ALLOWLIST`. Write / shell / db / external-http calls are blocked with a
  precise reason. Provider-requested URL fetch is blocked.
- **Residual:** none — the allowlist is the single source of truth.

### ATK-02 — Secret exfiltration (provider → response)

- **Vector:** A provider response tries to echo a secret back, or the request
  audit leaks a key.
- **Defense:** The key never enters the request envelope. The response is
  normalized to a bounded `contentSummary`. The sanitizer re-redacts every audit
  event (`sk-…`, `Bearer …`, Authorization, PEM, forbidden stems). Secret-detected
  → blocked.
- **Residual:** a novel secret shape not matched by the patterns — mitigated by
  the `<non_json_value>` collapse for non-JSON values and the no-leak test
  (R3B-P1-06).

### ATK-03 — SSRF / arbitrary URL fetch

- **Vector:** A provider / tool requests an arbitrary URL (internal service
  probing).
- **Defense:** Base-URL allowlist; `https://` only; off-allowlist redirects
  blocked; provider / tool URL fetch blocked (`blocked_provider_external_url_not_allowed`).
- **Residual:** none for the allowlisted-host model.

### ATK-04 — Cost / availability attack

- **Vector:** A runaway loop, retry storm, or oversize response runs up cost or
  exhausts memory.
- **Defense:** Hard retry cap; bounded timeouts; max response size; per-minute /
  daily / token / budget caps; fail-closed counters; single round-trip (no
  autonomous loop).
- **Residual:** budget caps are conservative estimates; the daily cap is the hard
  backstop.

### ATK-05 — Boundary / route drift

- **Vector:** A change quietly adds a route, a Provider route, or crosses to
  production.
- **Defense:** Route-governance contract test pins 34 / 34 / 5 / 0 / 1 / 1;
  `enforce_dev_environment()` allowlist; boundary searches; production-safety
  checks pin PID `28428`.
- **Residual:** none while the gates are enforced.

### ATK-06 — Audit tampering / loss

- **Vector:** A failure is silently swallowed, or an audit record is dropped.
- **Defense:** Every round-trip emits exactly one terminal event; oversized
  events are truncated, never dropped; write failure never enables execution.
- **Residual:** none within the dev-home-confined store.

---

## 5. STRIDE Summary

| Category | Highest-risk example | Primary control |
|----------|----------------------|-----------------|
| Spoofing | Forged provider response driving a tool call | Allowlist validation (TB-2/3) |
| Tampering | Provider write / state mutation | Read-only allowlist; no write path |
| Repudiation | Round-trip without an audit event | Terminal-event coverage invariant |
| Information disclosure | API-key / secret leak | env-only key; sanitizer; no-leak test |
| Denial of service | Retry storm / oversize response | Timeouts; caps; size limit |
| Elevation of privilege | Arbitrary URL fetch / shell | Allowlist; boundary searches |

---

## 6. Assumptions

- The operator explicitly enables the real path and sets the key in their own env.
- The allowlisted provider endpoint is operated by a vendor the operator trusts.
- The dev `HERMES_HOME` is isolated from `~/.hermes`.
- The Production Gateway is never touched by the WebUI.

---

## 7. Cross-References

- [Phase 3B planning](phase-3b-planning.md)
- [Phase 3B security risk register](phase-3b-security-risk-register.md)
- [Phase 3B redaction & no-leak policy](phase-3b-provider-redaction-and-no-leak-policy.md)
- [Phase 3B network boundary](phase-3b-network-boundary.md)
- [Phase 2B provider security boundary](phase-2b-provider-security-boundary.md)
- [Phase 3A security boundary](phase-3a-security-boundary.md)
