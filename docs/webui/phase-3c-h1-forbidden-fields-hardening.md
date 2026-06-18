# Phase 3C-H1 — Forbidden Fields Hardening

| Field | Value |
|-------|-------|
| Lens | 2 — Schema Forbidden Fields / Validation Fail-closed |
| Hardening ID | `CAP-FORBIDDEN-FIELDS-3C-H1-001` |
| Status | PASS (one real defect fixed) |

## Scope

Every forbidden field — top-level, case/alias variant, AND nested inside an
allowed field's value — must be rejected fail-closed, and the read model must
never expose one. An invalid manifest yields `status = validation_failed` and
blocked details.

## Evidence / the real defect

The forbidden-field scanner was **shallow**. A forbidden field nested inside
an allowed field's value passed validation and leaked through the read model:

```python
{"metadataSchema": {"shellCommand": "rm -rf", "secret": "leak", "Authorization": "Bearer x"}}
# before: valid=True, detail exposed "shellCommand" / "secret" / "Authorization"
```

Alias variants (`authorization`, `Bearer`, `api_key`, `shell_command`, …) were
already rejected via the unknown-field whitelist and dropped from the read
model by the `DETAIL_FIELDS` allowlist.

## Commands

```bash
./scripts/run_tests.sh tests/test_dev_web_phase_3c_h1_forbidden_fields.py
```

## Fixes (minimal, defense-in-depth)

1. `dev_web_capability_registry_schema.py` — `is_forbidden_field_present` now
   scans **recursively** (top-level keys + any nested dict / list / tuple), so
   a nested forbidden field is detected and the entry blocked fail-closed.
2. `dev_web_capability_registry.py` — `_validate_entry` requires scalar-string
   fields to be string scalars; a nested structure (forbidden or not) is
   rejected, so no content smuggles past the scalar read model.

The static manifest is unaffected (no nested structures). All 160 Phase 3C
backend tests still pass.

## Residual risk

None (P0 = 0, P1 = 0). The recursive scan + scalar guard + `DETAIL_FIELDS`
allowlist form three independent layers.
