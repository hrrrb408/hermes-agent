# PLUG-MANIFEST-3D-H1-001 — Descriptor Manifest Consistency

**Lens 1.** The static descriptor manifest is deterministic, stable, and the
single source of truth.

## Scope

- `get_static_manifest()` returns exactly 12 entries.
- The frozen pluginId list is stable and unique, in order visible → disabled →
  blocked (3 / 4 / 5).
- `CREATED_AT` / `UPDATED_AT` / `MANIFEST_VERSION` are pinned constants (no
  wall-clock sampling).
- The read model (`list_descriptor_details`, `get_descriptor_detail`,
  `build_registry_summary`, `get_plugin_descriptor_status_block`) is value-free
  and carries `redactionApplied = True`.
- Any drift in a pinned invariant (devOnly, productionAllowed,
  disabledByDefault, duplicate pluginId, missing required field, forbidden field)
  flips validation to invalid and the summary status to `validation_failed`.

## Evidence

`tests/test_dev_web_phase_3d_h1_descriptor_manifest_consistency.py` (24 tests).

## Result

PASS. The manifest is deterministic; drift is detectable and fail-closed.
