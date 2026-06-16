# Phase 3B-H1 — Provider Network Isolation / Mock-only Hardening

- **Provider Network Isolation ID:** PROVIDER-NETWORK-3B-H1-001
- **Lens:** 3 (Network Isolation / Mock-only Boundary)
- **Status:** PASS

## Scope

The OpenAI-compatible adapter
(`hermes_cli/dev_web_provider_openai_compatible.py`) is the only concrete real
round-trip. Phase 3B-H1 hardens the guarantee that **no real network call ever
happens in tests, smoke, or default operation.**

## Verified Invariants

- **Injectable HTTP client:** the HTTP client is a `ProviderHttpClient` Protocol,
  injected by the caller. `MockHttpClient` is the only client any test/smoke path
  wires. There is NO default real-network client wired into the live request path.
- **Header-value isolation:** `MockHttpClient` records header KEYS only
  (including `Authorization`), never the value. It records the request body
  LENGTH, never the content.
- **Endpoint allowlist:** the URL is always `{allowlisted_base_url}/v1/chat/completions`.
- **Transport simulation via mock:** transport failure →
  `blocked_provider_network_unavailable`; a safe-transient storm is retried up to
  the cap then fails closed (attempts == max_retries + 1).
- **Response-size guard:** a body over `MAX_RESPONSE_BYTES` (64 KiB) blocks with
  `blocked_provider_response_too_large` (non-retryable).
- **Success path never returns the raw body:** only the bounded content + parsed
  tool calls + bounded usage leave the adapter; the raw JSON body object is never
  carried on the normalized result.
- **No real network dependency** is introduced for the real provider live call
  (no `requests` / `httpx` / `urllib` / `aiohttp` / `curl` live path in tests).

## Evidence

- `tests/test_dev_web_phase_3b_h1_provider_network_hardening.py`
- `phase3b_h1_provider_boundary_hardening` smoke profile (real path blocked,
  `externalNetworkCalled=false`).

## Residual Risk

- P0: none. P1: none. The concrete production HTTP client remains deferred.
