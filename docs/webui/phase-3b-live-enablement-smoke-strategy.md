# Phase 3B-Live-Enablement — Smoke Strategy

| Field | Value |
|-------|-------|
| Phase | 3B-Live-Enablement (Planning) |
| Title | Strict Manual Real Provider Enablement — Smoke Strategy |
| Status | Frozen (docs-only planning; live enablement **not started**) |
| Date | 2026-06-17 |
| Planning ID | `PHASE-3B-LIVE-ENABLEMENT-PLANNING-001` |

## 1. What is allowed to smoke in this planning phase

```
No live smoke.
No API key.
No network.
Docs-only.
```

## 2. Future implementation smoke layers

The future implementation must build smoke in layered gates. Each layer proves
one boundary before the next can run:

| Layer | Scope | Network | Key | Live |
|-------|-------|---------|-----|------|
| 0 | disabled mode blocks | none | none | no |
| 1 | fake provider stays deterministic | none | none | no |
| 2 | real-gated but approval missing → blocked | none | none | no |
| 3 | approval present but key missing → blocked | none | marker only | no |
| 4 | key-present marker only, no request | none | marker only | no |
| 5 | mock-live request through injected fake network | fake (injected) | marker | mock-live |
| 6 | single live request, only after explicit human approval | real | real (env) | live |

Layers 0–5 are deterministic and offline (injected `MockHttpClient`). Layer 6 is
the **only** real-network layer and is gated behind explicit human approval.

## 3. First real live smoke (Layer 6) — allowed shape only

The first real live smoke may contain **only**:

1. One request.
2. No tool-call execution (tool calls may be classified / blocked, not executed).
3. No write.
4. No retry.
5. At most 5 cents.
6. Non-streaming.
7. Redacted audit.
8. Immediate disable after the request (auto-trigger disable / kill-switch
   re-arm).

This layer is **opt-in** and never runs in the default `all` smoke target. It
runs only under an operator-witnessed, separately-authorized session.

## 4. What live smoke must never do

- Read a key from anywhere but the environment.
- Persist / log / commit a key.
- Follow a redirect.
- Make a second request without a fresh approval.
- Execute a write / rollback / shell / db / external tool.
- Exceed the approved budget.
- Skip the kill-switch re-arm.

## 5. Smoke ↔ gates mapping

- Route governance (34 / 34 / 5 / 0 / 1 / 1) is re-asserted before and after
  every layer.
- Production Gateway PID `28428` / count `1` is re-asserted before and after
  every layer.
- `~/.hermes` and production `state.db` must never be accessed by any layer.

## 6. Cross-references

- [Phase 3B test report](phase-3b-test-report.md)
- [Phase 3B-H1 test report](phase-3b-h1-test-report.md)
- [Phase 3B-Live-Enablement kill switch](phase-3b-live-enablement-kill-switch-and-rollback.md)
- [Phase 3B-Live-Enablement GO / NO-GO](phase-3b-live-enablement-go-no-go.md)
