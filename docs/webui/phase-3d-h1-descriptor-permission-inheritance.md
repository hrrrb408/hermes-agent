# PLUG-PERMISSION-INHERITANCE-3D-H1-001 — Permission Inheritance / Most-restrictive Rule

**Lens 4.** A descriptor inherits the most-restrictive permission among its
bindings; escalation is rejected.

## Scope

- The frozen restrictiveness order (least → most): `READ_ONLY`, `WRITE_PREVIEW`,
  `WRITE_CONFIRM`, `ROLLBACK_CONFIRM`, `LIVE_PROVIDER_GATED`, `ADMIN_FORBIDDEN`,
  `EXTERNAL_FORBIDDEN`, `PRODUCTION_FORBIDDEN`. Rank map agrees with the order.
- `most_restrictive_permission` returns None for empty/invalid input, the single
  class for one binding, and the highest rank for many (PRODUCTION_FORBIDDEN
  dominates all).
- `inherited_permission_class` resolves a descriptor's bindings against the
  capability index and returns the most-restrictive class; unknown / empty
  bindings return None (treated as binding failure).
- Escalation is rejected fail-closed: declaring a class less restrictive than
  the inherited class (e.g. READ_ONLY when inheriting WRITE_CONFIRM or
  EXTERNAL_FORBIDDEN or PRODUCTION_FORBIDDEN) emits a "permission escalation"
  error. Terminal-forbidden classes are non-executable.

## Evidence

`tests/test_dev_web_phase_3d_h1_descriptor_permission_inheritance.py` (26 tests).

## Result

PASS. Most-restrictive inheritance is exact; escalation never weakens.
