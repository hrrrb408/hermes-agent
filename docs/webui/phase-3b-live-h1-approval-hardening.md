# Phase 3B-Live-Enablement H1 — Live Approval / TTL / Single-use Hardening

| Field | Value |
|-------|-------|
| Lens | 1 — Live Approval / TTL / Single-use Boundary |
| Hardening ID | `LIVE-APPROVAL-3B-H1-001` |
| Status | PASS |

## Scope

The live human-approval model: scope `provider_live_enablement`, 5-minute TTL,
single-use, in-scope match (provider / model / host / tool-allowlist subset),
and the dev-only value-free store.

## Evidence

- Test file: `tests/test_dev_web_phase_3b_live_h1_approval_hardening.py`
- Implementation: `hermes_cli/dev_web_provider_live_approval.py`

## Findings & Fixes

- TTL boundary verified: valid at exactly `now + TTL`, expired one second after.
- Single-use verified: a used approval is blocked; `mark_approval_used` is idempotent.
- Scope / mode tampering → `blocked_live_provider_approval_scope_invalid`.
- Mismatch (provider / model / host / out-of-allowlist tool) → `blocked_live_provider_approval_mismatch`.
- Approval + persisted store are value-free (no key / header / token / secret / production path).
- Production home and corrupt store → fail closed (no usable approval).

No implementation change was required.

## Residual risk

None. The approval layer remains value-free, single-use, 5-minute, and dev-only.
