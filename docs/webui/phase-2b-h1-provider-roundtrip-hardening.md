# Phase 2B-H1 — Provider Round-trip Hardening

## Document Information

| Field | Value |
|-------|-------|
| Phase | 2B-H1 |
| Title | Provider Round-trip Hardening |
| Status | Closed |
| Date | 2026-06-14 |
| Hardening ID | `HARDENING-2B-H1-001` |
| Provider Boundary Audit ID | `PROVIDER-BOUNDARY-AUDIT-2B-H1-001` |
| Provider Flake Closure ID | `PROVIDER-FLAKE-CLOSURE-2B-H1-001` |
| Input HEAD | `a3cd3b762e947ba5b93d676557c47ac9487a0649` |
| Branch | `dev-huangruibang` |
| Predecessor | Phase 2B (Provider Schema / API Controlled Integration) |

---

## 1. Purpose

Phase 2B-H1 is the hardening pass that follows Phase 2B. It is **not** Phase 2C.
It does not implement a real-vendor Provider, does not add a Tool write route,
and does not perform a production rollout. Its scope is to close the Phase 2B
P2 backlog with deterministic, agent-independent evidence and to harden the
Provider round-trip boundary:

```
1. real-vendor provider adapter not wired in 2B
2. one transient flake observed in test_audit_jsonl_no_secret_or_repr[audit_events_read-R1]
   under high parallelism
3. frontend visual polish (optional, non-blocking)
```

---

## 2. P2 List (carried from Phase 2B)

| ID | Item | Phase 2B-H1 disposition |
|----|------|--------------------------|
| P2-1 | Real-vendor provider adapter not wired | Accepted: the blocked framework exists; the concrete vendor call is deferred to a separately-authorized future phase. Real mode is blocked by default and stays blocked. |
| P2-2 | Transient flake under high parallelism | Closed as **non-reproduced** with deterministic repeated-run evidence (30/30 + 10/10). The latent provider-audit secret-pattern gap surfaced alongside it was fixed. |
| P2-3 | Frontend visual polish | Non-blocking, accepted as future work. |

---

## 3. 8-Lens Hardening Model

A deterministic 8-lens review was applied. Each lens was verified by an
independent adversarial agent **and** by a reproducible test class in
`tests/test_dev_web_phase_2b_hardening_boundaries.py`.

### 8-Lens Summary

| Lens | Name | Status | Findings | Fixes |
|------|------|--------|----------|-------|
| 1 | Provider Schema Boundary | PASS | Schema is a pure `STATIC_ALLOWLIST` projection; injection of write/recursive tools is dropped. | — |
| 2 | Provider Request / Mode Boundary | PASS | disabled inert; fake offline; real blocked unless all conditions hold; no API key in envelope. | — |
| 3 | Fake Provider Determinism | PASS | Deterministic (sha256-derived IDs), fully offline, no network imports. | — |
| 4 | Real Provider Blocked Boundary | PASS | Real blocked by default and blocked even when eligible (`blocked_real_provider_not_wired_in_phase_2b`). | — |
| 5 | Provider Tool-call Controlled Chain Preservation | PASS | Unknown/write-like/provider-recursive/malformed/secret calls blocked; valid calls run the full chain. | — |
| 6 | Provider Audit Redaction / Secret-Repr Boundary | **PASS (after fix)** | PEM private-key value pattern never matched any standard header (bare/RSA only, and the schema copy matched none); suffixed secret field names (`privateKeyPem`, `credentials`, `xApiKey`) escaped. | PEM pattern widened to catch every variant; field-stem substring list broadened. |
| 7 | Transient Flake Reproduction / Stability Boundary | PASS | 30/30 + 10/10 repeated runs; flake not reproduced; no leak path exists in the audit writers. | — |
| 8 | Frontend Contract / Smoke User Flow Boundary | PASS | Frontend mirrors the allowlist; no API-key input; fake round-trip reachable end-to-end; smoke all profiles PASS. | — |

**0 P0. 0 P1.**

---

## 4. Per-Lens Evidence

### Lens 1 — Provider Schema Boundary

- `build_provider_tool_schema` intersects any caller-supplied
  `allowed_tool_ids` with `STATIC_ALLOWLIST`; unknown ids are dropped.
- `validate_provider_schema_bundle` checks every tool is in the allowlist and
  has `readOnly=True`, `providerRequired=False`, `writeRequired=False`,
  `externalSideEffects=False`.
- Test: `TestLens1ProviderSchemaBoundary` (5 tests). Result: PASS.

### Lens 2 — Provider Request / Mode Boundary

- `_evaluate_real_mode_eligibility` requires ALL of: enablement env, mode env,
  API key present, dev home, production gate.
- `disabled` sends no schema; `fake` sends schema + offline API; `real` blocked
  unless eligible. `allowedToolIds` is bounded by `STATIC_ALLOWLIST`.
- Test: `TestLens2ProviderRequestModeBoundary` (5 tests). Result: PASS.

### Lens 3 — Fake Provider Determinism

- `FakeProviderAdapter` derives IDs via sha256 of the message; same message →
  same tool choice and same response id. No `httpx`/`requests`/`urllib`/`aiohttp`
  imports. `external_network_called` is always False.
- Test: `TestLens3FakeProviderDeterminism` (7 tests). Result: PASS.

### Lens 4 — Real Provider Blocked Boundary

- Without enablement / mode / key / dev home / gate, real mode returns a
  specific `blocked_provider_*` reason with `external_network_called=False`.
- Even when eligibility is forced True, the vendor call is not wired in Phase 2B
  (`blocked_real_provider_not_wired_in_phase_2b`).
- Test: `TestLens4RealProviderBlockedBoundary` (6 tests). Result: PASS.

### Lens 5 — Provider Tool-call Controlled Chain Preservation

- `validate_provider_tool_call` blocks unknown / write-like / provider-recursive
  / malformed / secret-bearing / oversized calls.
- A valid fake round-trip writes both the dry-run audit line and the
  post-execution audit line, proving the full controlled chain ran.
- Test: `TestLens5ProviderToolCallControlledChain` (6 tests). Result: PASS.

### Lens 6 — Provider Audit Redaction / Secret-Repr Boundary (fix applied)

The adversarial review surfaced that the provider audit secret-pattern set was
narrower than the boundary doc claims:

- The PEM private-key value pattern `-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----`
  matched only bare/RSA (and the copy in `dev_web_provider_schema.py` matched
  **no** standard header at all, due to a stray literal space before `KEY`).
  EC, OPENSSH, DSA, and ENCRYPTED PEM private keys passed through untouched.
- `_is_forbidden_field` required an exact normalized stem match (plus a
  token/secret/password/auth substring fallback), so suffixed names like
  `privateKeyPem`, `credentials`, and `xApiKey` escaped.

Because `userMessagePreview` (200 chars of user-typed text) flows into the
provider request audit payload, a user-typed PEM private key could previously
land verbatim in the dev-only provider audit file.

**Fix (HARDENING-2B-H1-001), in scope (all four provider modules are on the
allowed-modify list):**

- The PEM value pattern is widened to `-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----`
  across `dev_web_provider_audit.py`, `dev_web_provider_schema.py`,
  `dev_web_provider_request.py`, and `dev_web_provider_roundtrip.py`. It now
  matches every standard PEM private-key variant (bare, RSA, EC, OPENSSH, DSA,
  ENCRYPTED, …) with zero false positives on benign audit strings.
- The audit `_is_forbidden_field` substring fallback is broadened to also match
  `apikey`, `privatekey`, and `credential`, closing the named-field gap
  (`privateKeyPem`, `credentials`, `xApiKey`, `apikeyV2`).
- Callables / objects / classes continue to render as the fixed opaque
  `<non_json_value>` placeholder — never the repr, never the type name, never
  `object at 0x…`.

Test: `TestLens6ProviderAuditRedactionBoundary` (parametrized). Result: PASS.

### Lens 7 — Transient Flake Reproduction / Stability Boundary

- The Phase 2B transient flake `test_audit_jsonl_no_secret_or_repr
  [audit_events_read-R1]` was **not reproduced** in 30 deterministic reruns
  (10× isolated variant, 10× full hardening file, 10× high-parallelism batch at
  the wrapper's `-j 28` file parallelism) plus 10× repeated Phase 2B
  audit/hardening checks.
- No leak path exists in the audit writers: all serialize via bare
  `json.dumps` (no `default=` handler), all event fields are JSON-native, the
  audit path is resolved purely functionally from the per-test `hermes_home`,
  and the test helper writes the dry-run line directly (bypassing the dry-run
  writer's defense-in-depth `str()` fallback, which is itself not reachable for
  the current JSON-native event shape).
- Closure decision: **closed as non-reproduced** under
  `PROVIDER-FLAKE-CLOSURE-2B-H1-001`.
- Test: `TestLens7TransientFlakeStabilityBoundary` (15 tests, 5× each of three
  repeated scenarios). Result: PASS.

### Lens 8 — Frontend Contract / Smoke User Flow Boundary

- Frontend `SELECTABLE_TOOL_IDS` mirrors `STATIC_ALLOWLIST` exactly.
- `ProviderRoundtripPanel.vue` has no password/API-key input control and no
  key v-model binding.
- The API client attaches no Authorization/Bearer/x-api-key header.
- Smoke `phase2b_provider_fake_roundtrip` profile PASS (API round-trip,
  tool-write disabled, real blocked, audit queryable, UI panel visible).
- Test: `TestLens8FrontendContractBoundary` (2 tests) + live smoke. Result: PASS.

---

## 5. Findings & Fixes

| Severity | Finding | Fix | Location |
|----------|---------|-----|----------|
| P1 | PEM private-key value pattern matched only bare/RSA (schema copy matched none) | Widened to `-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----` | `dev_web_provider_{audit,schema,request,roundtrip}.py` |
| P1 | `_is_forbidden_field` missed suffixed secret field names | Broadened substring stems (`apikey`, `privatekey`, `credential`) | `dev_web_provider_audit.py` |
| INFO | Provider-recursive guard at `roundtrip.py:220` is dead code (allowlist gate fires first) | No change — provider-recursive calls are still blocked as `blocked_not_allowlisted`; documented as residual. | `dev_web_provider_roundtrip.py` |
| INFO | `redactionApplied=true` is set before sanitize (means "redaction routine ran", not "secret removed") | No change — by design; the widened patterns make the routine effective. | `dev_web_provider_audit.py` |

No P0. No P1 remains open.

---

## 6. Final Status

All 8 lenses PASS. **0 P0. 0 P1.** The Phase 2B provider round-trip is hardened:
fake remains deterministic and offline; real remains blocked by default; the
provider audit boundary no longer leaks any standard PEM private-key variant or
suffixed secret field name; the transient flake is closed as non-reproduced
with deterministic evidence.

---

## 7. Residual Risks

| ID | Item | Owner / phase |
|----|------|---------------|
| P2 | Real-vendor provider network call not wired | Separately-authorized future phase |
| P2 | Frontend visual polish | Optional future work |
| P2 | Provider streaming / long multi-turn memory | Future phase |
| P2 | Advanced audit storage / indexing / rotation race hardening | Phase 2D |
| P2 | The Phase 2A dry-run audit sanitizer still uses a `str(value)` defense-in-depth fallback for unknown types (not reachable for current JSON-native event shapes; the Phase 2B provider sanitizer is already hardened to `<non_json_value>`) | Phase 2D (audit hardening) |
| P2 | Future Production Gateway PID drift on host reboot | Smoke harness fails closed; a future authorized refresh phase updates the constant |

---

## 8. Conclusion

Phase 2B-H1 Provider Round-trip Hardening is **complete**. The provider
round-trip has been hardened through `HARDENING-2B-H1-001`; the provider
boundary audit is recorded under `PROVIDER-BOUNDARY-AUDIT-2B-H1-001`; the
transient flake is closed under `PROVIDER-FLAKE-CLOSURE-2B-H1-001`. Phase 2C
was **not** started.

## Phase 2C Update — Controlled Tool Write Execution

Phase 2C is now complete and pushed. It reuses the same "no new route"
discipline established by Phase 2B: the write preview and write execute paths
branch on `mode` inside the existing `/tools/dry-run` and `/tools/execute`
routes. The provider round-trip gains a preview-only write mode
(`providerWriteMode = "preview_only"` or write tool ids in `allowedToolIds`)
that generates a write preview but **never auto-executes**
(`blocked_write_provider_auto_execute_denied`); real provider write execution
remains blocked. The provider security boundary is unchanged —
`externalNetworkCalled` stays false for all write paths. See
[phase-2c-controlled-tool-write-execution](phase-2c-controlled-tool-write-execution.md).
