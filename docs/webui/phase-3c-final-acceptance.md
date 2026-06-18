# Phase 3C — Final Acceptance

| Field | Value |
|-------|-------|
| Phase | 3C (Closeout) |
| Title | Static Capability Registry — Final Acceptance |
| Status | Accepted (dev-only milestone) |
| Date | 2026-06-18 |
| Acceptance ID | `PHASE-3C-ACCEPTANCE-001` |

## 1. Acceptance scope

Final acceptance of the Phase 3C static dev-only Capability Registry as a
**dev-only descriptive milestone**: the registry + its read-only `/status`
block + its read-only Dev WebUI panel + its `capability_registry_*` audit +
its smoke/hardening coverage. Acceptance is for the dev branch only; it is not
a production acceptance.

## 2. Accepted capabilities

- Static Capability Registry (descriptive only).
- Static, deterministic manifest (`phase3c-static-v1`, 46 capabilities).
- Schema validation (frozen taxonomies + required/allowed/forbidden fields).
- Forbidden-field rejection (top-level, alias, and **nested**).
- Read-only `/status` block (`data.capabilityRegistry`).
- Read-only Dev WebUI panel (summary / table / detail drawer / badges).
- Permission / trust / status badges (non-color, accessible).
- `capability_registry_*` audit (10 event types, redacted, no-leak).
- Smoke profiles (Profile P + Profile Q, in `all`).
- Phase 3C-H1 hardening (12 / 12 lenses PASS; recursive forbidden scan +
  scalar-string type guard).

## 3. Rejected / not-accepted capabilities

- Plugin runtime.
- Dynamic loading.
- Remote registry.
- Marketplace.
- External plugin fetch.
- Provider-generated plugin.
- Shell command execution.
- Database mutation execution.
- External HTTP execution.
- Production operation.
- Provider write.
- Autonomous write.
- New HTTP route.
- Production rollout.

## 4. Test evidence

- Phase 3C backend tests: **160 PASS**.
- Phase 3C-H1 backend tests: **8 files PASS**.
- Frontend tests: **1147 PASS**.
- Smoke / E2E: **all PASS**, including `phase3c_capability_registry_static`
  (Profile P) and `phase3c_h1_capability_registry_hardening` (Profile Q).
- Hardening audit script: **PASS** (Overall, exit 0).

## 5. Security evidence

- No-leak closure: the `/status` block, every detail, and every audit event
  carry no API key / Authorization / Bearer / secret / callable repr / shell
  command / SQL statement / production path / plugin path / dynamic import path
  / external URL.
- Forbidden-field boundary enforced by three layers: recursive scan, scalar-
  string type guard, and the `DETAIL_FIELDS` read-model allowlist.
- No dynamic loading (AST-import + AST-call scanned across all registry modules).
- Audit failure never enables the registry; production home refused.

## 6. Production safety evidence

- Production Gateway PID 28428 (count 1), not stopped / restarted / replaced /
  signaled.
- Dev services bind to `127.0.0.1` only; 5180 / 5181 free before and after.
- No `~/.hermes` access; no production `state.db` access.

## 7. Route governance evidence

OpenAPI paths **34** · runtime routes **34** · Tool GET **5** · Tool write HTTP
route **0** · Tool dry-run **1** · Tool execution **1**. No new HTTP route, no
Provider route, no Tool write route.

## 8. Risk state

P0 open = **0**. P1 open = **0**. P2 deferred = frontend TS manifest mirror
generator (drift bounded by the H1 consistency test). See
[risk closure](phase-3c-risk-closure.md).

## 9. Known limitations

See [known limitations / deferred work](phase-3c-known-limitations-and-deferred-work.md).
These are intentional deferrals, not unfinished defects.

## 10. Final acceptance statement

**Phase 3C is accepted as a static dev-only Capability Registry milestone.**
The registry is static, dev-only, read-only, and descriptive only. It does not
grant permissions, does not execute tools / providers / workflows, does not
create approvals / confirmations / dry-runs, and does not bypass Tool policy,
the Provider live gate, Workflow approval, dry-run, confirmation, or audit.
Phase 3D was not started.

## 11. Cross-references

- [Closeout](phase-3c-closeout.md)
- [Final security boundary](phase-3c-security-boundary-final.md)
- [Risk closure](phase-3c-risk-closure.md)
- [Test gate summary](phase-3c-test-gate-summary.md)
