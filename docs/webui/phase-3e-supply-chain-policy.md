# Phase 3E — Supply-chain Policy

| Field | Value |
|-------|-------|
| Phase | 3E (Planning) |
| Title | Real Plugin Runtime — Supply-chain Policy (Frozen, Design-only) |
| Status | Frozen (docs-only planning; Real Plugin Runtime **not started**) |
| Date | 2026-06-19 |
| Planning ID | `PHASE-3E-PLANNING-001` |
| Supply-Chain ID | `PHASE-3E-SUPPLY-CHAIN-001` |

> This document designs — but does **not** implement — the supply-chain policy a
> future real plugin runtime would require. No implementation is authorized.

## 1. Position (no install by default)

```
No package install by default.
No npm / pip / cargo install by a plugin.
No remote plugin package.
No marketplace.
No remote registry.
No auto-update.
No post-install hook.
No pre-execution hook.
No provider-generated dependency.
```

## 2. Static reviewed descriptor only

- The only plugin content that exists today is **static, reviewed, tracked
  source** (Phase 3D descriptors). There is no fetched package and no
  installed dependency.
- A future runtime must start from this static, reviewed source — never from a
  fetched or installed artifact.

## 3. Pinning + integrity (if anything is ever fetched)

- If any artifact is ever considered (separate approval required):
  - **pinned version** (no `latest`, no floating ranges);
  - **hash / digest verification** (SHA-256 or stronger) at fetch;
  - **allowlist of sources** (deny-by-default);
  - **no auto-update** — every update is a reviewed, explicit change.

## 4. Review checklist (future, not executed now)

For any future plugin / package candidate:

```
source review (tracked / reviewed / reputable)
capability binding (existing Phase 3C capabilityId)
permission inheritance (most-restrictive)
forbidden-field scan (recursive + alias + nested)
no dynamic loading / no shell / no DB / no external HTTP
no post-install / pre-execution hook
no persistence surface
integrity hash verified
kill switch + audit coverage confirmed
```

## 5. Signed manifest (future option)

- A signed-manifest model is a **future** supply-chain hardening option
  (RUNTIME-P2-03). It is **not** designed out and **not** approved.
- If pursued, signing keys, verification, key rotation, and revocation must each
  be separately planned.

## 6. Quarantine model

- Any unverified / un-pinned artifact is quarantined (never executed).
- Quarantine is auditable; release from quarantine requires explicit review.

## 7. Deprecation + rollback

- A plugin / package may be **deprecated** (marked, disabled, audited).
- A **rollback** swaps a plugin out for a prior reviewed version — subject to the
  version-floor / downgrade protection (see RUNTIME-THREAT-29).
- Rollback is audited and reversible.

## 8. Cross-references

- [Phase 3E planning](phase-3e-planning.md)
- [Phase 3E sandbox architecture](phase-3e-sandbox-architecture.md)
- [Phase 3E network boundary model](phase-3e-network-boundary-model.md)
- [Phase 3E permission review](phase-3e-permission-review.md)
- [Phase 3E threat model](phase-3e-real-runtime-threat-model.md)
- [Phase 3D plugin manifest contract](phase-3d-plugin-manifest-contract.md)
- [Phase 3D plugin descriptor trust policy](phase-3d-plugin-descriptor-trust-policy.md)
