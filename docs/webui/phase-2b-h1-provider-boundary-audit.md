# Phase 2B-H1 — Provider Boundary Audit

| Field | Value |
|-------|-------|
| Audit ID | `PROVIDER-BOUNDARY-AUDIT-2B-H1-001` |
| Hardening ID | `HARDENING-2B-H1-001` |
| Date | 2026-06-14 |
| Status | Closed — all 8 boundaries hold |

This document records the eight provider round-trip boundaries audited in
Phase 2B-H1. Each boundary is enforced in code, pinned by a deterministic
test, and verified by an independent adversarial review.

---

## 1. Provider Schema Boundary

**Contract.** The provider schema is a pure projection of `STATIC_ALLOWLIST`
(`clarify` + the five read-only tools). It can never advertise a write tool, a
provider-recursive tool, a secret, a callable repr, or a filesystem/shell/
database parameter. Every tool carries `readOnly=True`, `providerRequired=False`,
`writeRequired=False`, `externalSideEffects=False`.

**Enforcement.** `build_provider_tool_schema` intersects caller-supplied ids
with `STATIC_ALLOWLIST`; `validate_provider_schema_bundle` re-checks every tool.

**Evidence.** `TestLens1ProviderSchemaBoundary` (5 tests PASS). Adversarial
review: PASS (no refutation).

---

## 2. Provider Request Boundary

**Contract.** `disabled` sends nothing. `fake` sends the schema and invokes the
offline fake adapter. `real` is blocked unless ALL hold: enablement env,
mode=real, API key present, dev home, production gate, explicit request flag.
The request never carries an API key.

**Enforcement.** `build_provider_request` mode gating; `_evaluate_real_mode_eligibility`;
`allowedToolIds` always intersected with `STATIC_ALLOWLIST`.

**Evidence.** `TestLens2ProviderRequestModeBoundary` (5 tests PASS). Adversarial
review: PASS.

---

## 3. Fake Provider Boundary

**Contract.** `FakeProviderAdapter` is deterministic and fully offline. No env
key read, no API key required, no network call. Same message → same tool choice
and same response id.

**Enforcement.** sha256-derived IDs; keyword routing gated by `allowed_tool_ids`;
no network imports.

**Evidence.** `TestLens3FakeProviderDeterminism` (7 tests PASS). Adversarial
review: PASS.

---

## 4. Real Provider Blocked Boundary

**Contract.** `RealProviderAdapter` never calls a real network in Phase 2B.
Without full enablement the request is blocked with a specific reason and
`externalNetworkCalled=false`. Even when eligible, the vendor call is not wired
(`blocked_real_provider_not_wired_in_phase_2b`).

**Enforcement.** `_evaluate_real_mode_eligibility` (request) +
defense-in-depth re-check (adapter) + unconditional not-wired block.

**Evidence.** `TestLens4RealProviderBlockedBoundary` (6 tests PASS). Adversarial
review: PASS.

---

## 5. Tool-call Controlled Chain Boundary

**Contract.** Every provider-requested tool call flows through the EXISTING
controlled chain: dry-run → digest → dry-run audit → confirmation token →
pre-execution audit → handler lookup → dispatch → handler call → post-execution
audit. Unknown / write-like / provider-recursive / malformed / oversized /
secret-bearing calls are blocked and never reach execution.

**Enforcement.** `validate_provider_tool_call` + `parse_provider_tool_calls` +
`execute_provider_tool_call_via_controlled_chain`.

**Evidence.** `TestLens5ProviderToolCallControlledChain` (6 tests PASS); a valid
fake round-trip writes both `tool-dry-run-audit.jsonl` and
`tool-post-execution-audit.jsonl`. Adversarial review: PASS.

---

## 6. Provider Audit Redaction Boundary

**Contract.** Every provider audit event is defensively re-redacted. Secrets
(`sk-…`, `Bearer …`, `Authorization: …`, every PEM private-key variant) become
`[REDACTED]`; forbidden field-name stems (incl. `apikey`, `privatekey`,
`credential`) are dropped; non-JSON-native values render as the fixed
`<non_json_value>` placeholder (never repr/type-name). `redactionApplied` is
always true. The audit path is rejected if missing `HERMES_HOME`, equal to
`~/.hermes`, outside the dev home, or ending in `state.db`.

**Enforcement.** `_sanitize` + `_is_secret_string` + `_is_forbidden_field` +
`_resolve_audit_path`, in `dev_web_provider_audit.py`.

**Evidence.** `TestLens6ProviderAuditRedactionBoundary` (parametrized PASS,
incl. all 6 PEM variants, suffixed secret fields, opaque callable placeholder,
EC-PEM-in-user-message redaction). Adversarial review: WARN → **fixed → PASS**.

---

## 7. Frontend Provider Contract Boundary

**Contract.** The frontend mirrors the backend boundary: mode selector
(disabled/fake/real), message input, allowed-tools selector bounded by the
read-only allowlist, schema preview, run-fake-round-trip button, tool
calls/results/final-answer panels, provider audit IDs, safety badges. The UI
**never** accepts an API key; real mode surfaces a blocked message.

**Enforcement.** `SELECTABLE_TOOL_IDS` mirrors `STATIC_ALLOWLIST`; no key input
control; API client sends no Authorization header; backend `_FORBIDDEN_REQUEST_FIELDS`
rejects any key in the body.

**Evidence.** `TestLens8FrontendContractBoundary` (2 tests PASS); smoke
`phase2b_provider_fake_roundtrip` profile PASS. Adversarial review: PASS.

---

## 8. Production Isolation Boundary

**Contract.** No `~/.hermes` access, no production `state.db` access, no
production gateway stop/restart/replace/signal, no production rollout. Dev
services bind `127.0.0.1` only. The production gateway PID gate is read-only.

**Enforcement.** Allowlist path resolution; `_resolve_audit_path` containment;
read-only `pgrep` gate; smoke harness fails closed on PID drift.

**Evidence.** Production Gateway PID 1962 unchanged across every gate; count 1;
5180/5181 free throughout. `dev-check` and `memory-check` PASS.

---

## Verdict

All 8 boundaries hold. **0 P0. 0 P1.** Recorded under
`PROVIDER-BOUNDARY-AUDIT-2B-H1-001`.
