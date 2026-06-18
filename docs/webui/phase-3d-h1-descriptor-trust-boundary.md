# PLUG-TRUST-BOUNDARY-3D-H1-001 — Trust Boundary / No Self-upgrade / Disabled-by-default

**Lens 5.** The trust taxonomy is frozen; self-upgrade is rejected; every
descriptor stays disabled-by-default.

## Scope

- Trust levels: `trusted_builtin_code`, `trusted_static_descriptor`,
  `dev_reviewed_descriptor`, `experimental_disabled_descriptor`,
  `external_forbidden`, `unknown_forbidden`, `production_forbidden`. Visible trust
  levels (`trusted_builtin_code`, `trusted_static_descriptor`) are disjoint from
  forbidden trust levels.
- A forbidden trust level must be blocked; `experimental_disabled_descriptor`
  must be disabled / blocked / planned; `visible` requires a verified trust level.
- Trust self-upgrade is rejected: a descriptor bound to a forbidden capability
  may not carry a verified trust level.
- First-version invariants: every descriptor has `devOnly = True`,
  `productionAllowed = False`, `disabledByDefault = True`. Mutating any of these
  fails validation.

## Evidence

`tests/test_dev_web_phase_3d_h1_descriptor_trust_boundary.py` (25 tests).

## Result

PASS. The trust taxonomy is frozen, self-upgrade is rejected, and every
descriptor remains dev-only / disabled-by-default.
