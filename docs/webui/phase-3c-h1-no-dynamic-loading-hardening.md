# Phase 3C-H1 — No Dynamic Loading Hardening

| Field | Value |
|-------|-------|
| Lens | 8 — No Dynamic Loading / No Remote Registry / No Marketplace |
| Hardening ID | `CAP-NO-DYNAMIC-3C-H1-001` |
| Status | PASS |

## Scope

The registry is a static, descriptive, in-process manifest. There is no plugin
runtime, no dynamic loading, no remote registry / marketplace / external
plugin fetch, no provider-generated plugin, no LLM-generated tool install.

## Evidence

- AST-walk of every registry module: no import of a dynamic-load / network /
  shell library (`importlib`, `importlib_metadata`, `pkgutil`, `ctypes`,
  `subprocess`, `shlex`, `requests`, `httpx`, `urllib`, `aiohttp`, `socket`,
  `http`).
- No call to `eval` / `exec` / `__import__` / `compile` / `importlib.import_module`
  / `subprocess.*` / `os.system` / `os.popen`, and no `shell=True` keyword.
- No path-based loader reference (`SourceFileLoader`, `load_module`,
  `exec_module`, `spec_from_file_location`).
- Frozen flags: `DYNAMIC_LOADING_ALLOWED = REMOTE_REGISTRY_ALLOWED =
  MARKETPLACE_ALLOWED = PRODUCTION_ALLOWED = False`; `DEV_ONLY = True`.
- Manual one-shot live profile is listed but disabled (never executed); no
  `LIVE_PROVIDER_GATED` capability is enabled by default.
- Forbidden capabilities (dynamic plugin load, remote registry, marketplace,
  shell, database mutation, external HTTP, production operation) are described
  as `blocked`.

## Commands

```bash
./scripts/run_tests.sh tests/test_dev_web_phase_3c_h1_no_dynamic_loading.py
```

## Fixes

Test-only. No implementation change. The AST call-scan complements the Phase
3C AST import-analysis test.

## Residual risk

None.
