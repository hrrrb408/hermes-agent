# Phase 3B-H1 — Provider Boundary UI Security Hardening

- **Provider UI Security ID:** PROVIDER-UI-3B-H1-001
- **Lens:** 9 (Frontend Provider Boundary UI No-leak Boundary)
- **Status:** PASS

## Scope

The frontend provider surface: `ProviderBoundaryStatus.vue`,
`ProviderRoundtripPanel.vue`, the `toolProvider` store, and the boundary result
projection. Phase 3B-H1 hardens the no-leak + read-only-allowlist invariants.

## Verified Invariants

- **No API-key input:** no `input[type="password"]`, no `api-key`/`bearer`/
  `authorization` input anywhere on the provider surface, in any state
  (disabled / fake / real-blocked / real-gated).
- **No secret value rendered:** no `sk-`, no `Bearer `, no `Authorization`,
  no `apiKeyValue`, no `accessToken`/`refresh_token`/`client_secret`, no
  `fullTokenHash`/`plainToken`, no masked key fragment, no callable repr,
  no production path.
- **Boundary label state machine:** disabled / fake / real_blocked /
  real_gated, gated ONLY when `realReachable=true`.
- **Permanently-blocked operations** (Provider write, Provider auto-write,
  Autonomous write, Production rollout) render as `blocked`, NEVER `ALLOWED`,
  in every state.
- **Read-only allowlist:** the boundary renders exactly the six read-only tools;
  the selectable constant is pinned to the backend `STATIC_ALLOWLIST`.
- **Blocked write-tool result:** a provider round-trip result surfacing a write
  tool is marked `blocked`, `executed=false`, never executed.
- **Unknown provider mode rejected at the schema layer** (HTTP 400), no leak.

## Evidence

- `apps/hermes-dev-webui/src/tests/phase3b-h1-provider-boundary.spec.ts`
- `apps/hermes-dev-webui/src/tests/phase3b-h1-provider-no-leak.spec.ts`
- `apps/hermes-dev-webui/src/tests/phase3b-h1-provider-blocked-reasons.spec.ts`
- `apps/hermes-dev-webui/src/tests/phase3b-h1-provider-readonly-tools.spec.ts`
- `apps/hermes-dev-webui/src/tests/phase3b-h1-provider-status-ui.spec.ts`
- `apps/hermes-dev-webui/tests/smoke/phase-3b-h1-provider-boundary-hardening-smoke.spec.ts`

## Residual Risk

- P0: none. P1: none.
