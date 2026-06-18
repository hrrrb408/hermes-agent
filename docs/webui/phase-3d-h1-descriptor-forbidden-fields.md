# PLUG-FORBIDDEN-FIELDS-3D-H1-001 — Descriptor Forbidden Fields / Nested Alias Fail-closed

**Lens 2.** No descriptor may carry a forbidden field at any depth.

## Scope

- Every canonical forbidden field (`pythonImportPath`, `callable`, `shellCommand`,
  `externalUrl`, `downloadUrl`, `pluginPackage`, `dynamicModule`, `evalCode`,
  `execCode`, `sqlStatement`, `productionPath`, `apiKey`, `Authorization`,
  `secret`, `localPath`, `remoteUrl`, `installCommand`, `postInstallHook`,
  `preExecutionHook`, `arbitraryArgs`) is rejected.
- Every alias / casing / snake_case variant (`authorization`, `AUTHORIZATION`,
  `bearer`, `api_key`, `secretValue`, `token`, `accessToken`, `callable_repr`,
  `shell_command`, `sql`, `production_path`, `dynamic_import`, `importPath`,
  `modulePath`, …) is rejected.
- Nested escapes inside `metadataSchema`, list values, `owner`, and deeply nested
  structures are caught by the recursive `_scan_for_forbidden`.
- An invalid descriptor is fail-closed: not exposed as enabled, blocked in the
  read model, summary status `validation_failed`, no permission grant, no
  execution path.

## Evidence

`tests/test_dev_web_phase_3d_h1_descriptor_forbidden_fields.py` (41 tests).

## Result

PASS. The denylist is the union of canonical + alias variants; the recursive scan
defeats nesting; invalid descriptors never reach the read model.
