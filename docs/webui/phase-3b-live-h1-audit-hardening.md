# Phase 3B-Live-Enablement H1 — provider_live_* Audit / Redaction Hardening

| Field | Value |
|-------|-------|
| Lens | 7 — provider_live_* Audit / Redaction / Fail-closed Boundary |
| Hardening ID | `LIVE-AUDIT-3B-H1-001` |
| Status | PASS |

## Scope

The 18 frozen `provider_live_*` audit event types, their value-free schema,
defensive re-redaction before the persisted JSONL, and fail-closed writes.

## Evidence

- Test file: `tests/test_dev_web_phase_3b_live_h1_audit_hardening.py`
- Implementation: `hermes_cli/dev_web_provider_live_audit.py`

## Findings & Fixes

- All 18 event types build value-free with `redactionApplied=true`.
- Injected `apiKey` / `Authorization` (`Bearer …`) in `safeMetadata` are
  defensively redacted to `[REDACTED]` before the persisted JSONL; no
  `sk-…` / `Bearer …` survives.
- Secret-state projection carries `keyValue="never"`.
- Write against the production home fails closed (returns `None`).
- Typed writers return a non-`None` eventId under the dev home.
- Store lives under the dev `HERMES_HOME` only.

No implementation change was required.

## Residual risk

None. Audit is redacted, dual-written, and fail-closed.
