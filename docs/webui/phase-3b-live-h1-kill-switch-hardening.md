# Phase 3B-Live-Enablement H1 — Kill Switch / Disable / Re-enable Hardening

| Field | Value |
|-------|-------|
| Lens | 5 — Kill Switch / Disable / Re-enable Boundary |
| Hardening ID | `LIVE-KILL-3B-H1-001` |
| Status | PASS |

## Scope

The live kill switch: inactive by default, 14 frozen triggers, unknown-reason
normalization, blocks before the secret read and before any network call, and
clearing it is **not** itself an approval.

## Evidence

- Test file: `tests/test_dev_web_phase_3b_live_h1_kill_switch_hardening.py`
- Implementation: `hermes_cli/dev_web_provider_live_kill_switch.py`

## Findings & Fixes

- Inactive by default; exactly 14 frozen triggers present.
- Trigger arms the switch with the correct `triggeredBy` / `triggeredAt`.
- Unknown reason normalized to `manual_operator_trigger`.
- State projection is value-free.
- Clearing disarms the switch and grants **no** approval (`list_approvals` empty).
- Corrupt store fail-opens to inactive (still gated by the other layers).
- Production home is refused (trigger returns `False`).

No implementation change was required.

## Residual risk

None. The kill switch is dev-only and re-enable requires a fresh approval.
