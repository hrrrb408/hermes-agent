# Phase 3C — No Dynamic Loading Policy

| Field | Value |
|-------|-------|
| Phase | 3C (Planning) |
| Title | No Dynamic Loading Policy (Frozen Prohibition) |
| Status | Frozen (docs-only planning; Capability Registry **not started**) |
| Date | 2026-06-17 |
| Planning ID | `PHASE-3C-PLANNING-001` |
| Policy ID | `PHASE-3C-NO-DYNAMIC-LOADING-001` |

> Phase 3C is a **Capability Registry**, not a **Plugin Runtime.** This document
> freezes the prohibition on dynamic loading. A future Plugin Runtime, if ever
> needed, must be planned as a separate phase (Phase 3D / 3E) and separately
> authorized.

## 1. Frozen prohibition

The Phase 3C first version **forbids** all of the following. Any one of them is
a P0 stop condition (see [phase-3c-security-risk-register.md](phase-3c-security-risk-register.md),
`CAP-P0-01` / `CAP-P0-02`):

1. Python `importlib` dynamic import.
2. Path-based loading of a Python file.
3. Loading a user's local plugin directory.
4. npm package dynamic loading.
5. Browser-side remote JS plugin loading.
6. Plugin marketplace.
7. Remote registry.
8. Remote manifest fetch.
9. Arbitrary-URL fetch for capability / plugin discovery.
10. Shell-command plugin.
11. Database plugin.
12. External-HTTP plugin.
13. Provider-generated plugin.
14. An LLM-generated tool installed as a plugin.
15. A self-modifying capability (a capability that rewrites the registry).
16. Auto-enable of a capability.
17. Production plugin.

## 2. Why

Dynamic loading converts a **descriptive** registry into an **arbitrary code
execution** surface. The entire Phase 3C premise is that capabilities are
declared, audited, and blocked — never loaded and invoked from an untrusted or
external source. Permitting any item in §1 would:

- break the static / tracked / reviewable invariant,
- introduce an untrusted-code execution path,
- bypass the existing tool policy / approval / route / live-gate boundaries,
- create a new secret-leak and supply-chain vector.

## 3. What the registry may do instead

- Declare capabilities statically in a tracked manifest
  ([phase-3c-static-manifest-schema.md](phase-3c-static-manifest-schema.md)).
- Classify, validate, expose (read-only), and audit them.
- **Reference** an existing built-in capability by a stable id (`toolBinding` /
  `providerBinding` / `workflowBinding`) without holding a code pointer.
- Block capabilities with a precise `blockedReason`.

## 4. What must hold at runtime (future)

- No `importlib` / `__import__` / `importlib.util.spec_from_file_location` call
  path may exist in the registry module.
- No `subprocess` / `os.system` / `eval` / `exec` path.
- No `requests` / `httpx` / `urllib` / `aiohttp` fetch for capability discovery.
- No filesystem walk of a user plugin directory.
- No remote registry / marketplace URL configured or fetched.
- The audit event `capability_registry_no_dynamic_loading_checked` must confirm
  these invariants at load time.

## 5. Future Plugin Runtime (deferred)

A Plugin Runtime is **out of scope** for Phase 3C. If one is ever required, it
must:

- be a separate, explicitly named future phase (e.g. Phase 3D / 3E),
- carry its own scope freeze, threat model, and GO / NO-GO,
- never be reachable from the Phase 3C registry by default,
- re-affirm every existing boundary (no production, no `~/.hermes`, no
  production `state.db`, no new route, no auto-enable, no trust auto-upgrade).

## 6. Cross-references

- [Phase 3C planning](phase-3c-planning.md)
- [Phase 3C scope freeze](phase-3c-capability-registry-scope-freeze.md)
- [Phase 3C static manifest schema](phase-3c-static-manifest-schema.md)
- [Phase 3C risk register](phase-3c-security-risk-register.md)
