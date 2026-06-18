# PLUG-CAPABILITY-BINDING-3D-H1-001 — Capability Binding Integrity / Phase 3C Drift

**Lens 3.** Every descriptor binds only to existing Phase 3C capabilityIds.

## Scope

- The Phase 3C capability index (`build_capability_index`) contains every
  capabilityId; every descriptor binding resolves to it.
- A descriptor can never introduce a new capabilityId, bind to a missing /
  malformed one, or bind an invented id — all rejected by `check_descriptor_policy`.
- A descriptor binding a forbidden (terminal) capability can never be marked
  visible; it inherits the terminal permission and must be blocked.
- Phase 3C drift boundary: if a bound capabilityId disappears from the index
  (simulated drift), descriptor validation fails closed. A stricter Phase 3C
  permission is inherited; a less-restrictive declared class is escalation.

## Evidence

`tests/test_dev_web_phase_3d_h1_descriptor_capability_binding.py` (19 tests).

## Result

PASS. Bindings are exhaustive against Phase 3C; drift and forbidden-binding
attempts are rejected.
