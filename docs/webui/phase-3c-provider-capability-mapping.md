# Phase 3C — Provider Capability Mapping

| Field | Value |
|-------|-------|
| Phase | 3C (Planning) |
| Title | Provider Capability Mapping (Phase 3B Boundary → Capabilities) |
| Status | Frozen (docs-only planning; Capability Registry **not started**) |
| Date | 2026-06-17 |
| Planning ID | `PHASE-3C-PLANNING-001` |
| Mapping ID | `PHASE-3C-PROVIDER-MAP-001` |

> This document maps the **existing** Phase 3B / 3B-H1 / 3B-Live-Enablement
> provider surface to capability records. The registry describes these; it does
> **not** change any provider gate. The live manual one-shot execution remains
> **NO-GO until separately authorized**.

## 1. Provider capability classification

| Capability | capabilityId | permissionClass | trustLevel | status |
|------------|--------------|-----------------|------------|--------|
| Fake provider round-trip | `provider.fake_roundtrip` | `READ_ONLY` | `BUILTIN_VERIFIED` | `enabled` |
| Real provider boundary status | `provider.real_boundary_status` | `READ_ONLY` | `BUILTIN_VERIFIED` | `enabled` |
| Real provider request preview | `provider.real_request_preview` | `READ_ONLY` | `BUILTIN_VERIFIED` | `enabled` (default disabled) |
| Real gated round-trip | `provider.real_gated_roundtrip` | `LIVE_PROVIDER_GATED` | `BUILTIN_VERIFIED` | `disabled` (default) |
| Live manual one-shot | `provider.live_manual_one_shot` | `LIVE_PROVIDER_GATED` | `BUILTIN_VERIFIED` | `disabled` (default) |
| Provider tool-call classification | `provider.tool_call_classification` | `READ_ONLY` | `BUILTIN_VERIFIED` | `enabled` |

## 2. Forbidden provider capabilities

| Capability | capabilityId | permissionClass | trustLevel | status | blockedReason |
|------------|--------------|-----------------|------------|--------|---------------|
| Provider tool execution (first live path) | `provider.tool_execution` | `ADMIN_FORBIDDEN` | `EXTERNAL_FORBIDDEN` | `blocked` | `blocked_provider_tool_execution_forbidden` |
| Provider write | `provider.write` | `ADMIN_FORBIDDEN` | `EXTERNAL_FORBIDDEN` | `blocked` | `blocked_provider_write_forbidden` |
| Provider auto-write | `provider.auto_write` | `ADMIN_FORBIDDEN` | `EXTERNAL_FORBIDDEN` | `blocked` | `blocked_provider_auto_write_forbidden` |
| Provider autonomous action | `provider.autonomous_action` | `ADMIN_FORBIDDEN` | `EXTERNAL_FORBIDDEN` | `blocked` | `blocked_provider_autonomous_action_forbidden` |

## 3. Invariants preserved

- The fake round-trip stays an offline, deterministic mock. The registry does
  not change it.
- Real provider capabilities stay **disabled by default**. The registry does not
  enable them.
- `LIVE_PROVIDER_GATED` capabilities still require the full Phase 3B-Live-Enablement
  live gate: a fresh, single-use, in-scope, unexpired human approval; the env-only
  value-free secret read; the single-host HTTPS allowlist; the frozen caps; the
  14-trigger kill switch; and the redacted dual-write `provider_live_*` audit.
- Provider tool execution is **blocked** in the first live path; provider tool
  calls are classified / blocked, not executed.

## 4. Manual one-shot live execution — explicit deferral

> **Manual one-shot live execution is not part of Phase 3C.**

Phase 3C may **register** `provider.live_manual_one_shot` as a
`LIVE_PROVIDER_GATED` capability (so it is visible as gated and auditable), but
it **may not execute** it. Executing it remains a separately-authorized step
governed by [phase-3b-live-enablement-go-no-go.md](phase-3b-live-enablement-go-no-go.md).

## 5. Non-negotiable statement

The Capability Registry **does not relax** the provider boundary. No real
provider is enabled, no real API key is read, and no real network call is made
by registering or viewing these capabilities.

## 6. Cross-references

- [Phase 3C planning](phase-3c-planning.md)
- [Phase 3B security boundary](phase-3b-security-boundary.md)
- [Phase 3B-Live-Enablement GO / NO-GO](phase-3b-live-enablement-go-no-go.md)
- [Phase 3B-Live-Enablement scope freeze](phase-3b-live-enablement-scope-freeze.md)
