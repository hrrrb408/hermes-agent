# Phase 3B Provider UI (Implementation)

| Field | Value |
|-------|-------|
| Phase | 3B |
| Status | Implemented |
| Component | `apps/hermes-dev-webui/src/components/workspace/ProviderBoundaryStatus.vue` |

The existing provider panel gains a **real-provider boundary status** section
that renders the value-free metadata from `GET /api/dev/v1/status`
`data.providerBoundary`.

## What it shows

- boundary label: `disabled` / `fake (offline)` / `real — blocked` / `real — gated on`
- API enabled: no / yes (redacted)
- API key: `env_present` / `env_missing` (value-free)
- base URL: allowlisted host, or `blocked` (never a secret-bearing URL)
- model (safe string), adapter name + implemented flag
- budget / rate-limit caps (safe)
- real reachable (yes/no) + the current gating reason code
- permanently-blocked operations: provider write / auto-write / autonomous
  write / production rollout — each rendered as `blocked` (never `ALLOWED`)
- the read-only tool allowlist (clarify + the five read-only tools)

## What it never shows

An API-key input control, an API-key value, an Authorization / Bearer header, a
raw token, a full tokenHash, raw arguments, a callable repr, or a production
path.

## Store + types

- `toolProvider` store: `boundary`, `boundaryLabel`, `loadBoundary()`.
- `types/api/toolProvider.ts`: `ProviderBoundaryStatus`.
- `api/toolProvider.ts`: `fetchProviderBoundary()` (reads `/status`, returns
  `null` on error).
