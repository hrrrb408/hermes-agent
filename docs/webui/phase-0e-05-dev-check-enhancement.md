# Phase 0E-05: dev-check Enhancement

**Status:** Completed
**Date:** 2026-06-08
**Branch:** dev-huangruibang
**Base commit:** 3224a8464 (Phase 0E-04 Dev WebUI Smoke Runner)

---

## 1. Problem

`dev-check` verifies Hermes dev environment integrity but has no awareness of the Dev WebUI subsystem. It does not verify:

- Dev WebUI app directory and package.json existence
- Build artifact ignore policy (0E-01)
- Visual-review artifact ignore policy (0E-02)
- Playwright artifact ignore policy (0E-03)
- Playwright config and smoke spec existence
- Smoke runner existence and executability
- Package scripts (test:smoke, test:smoke:0e03)
- Static OpenAPI contract validity (11 paths, allowed routes, no forbidden routes)
- Dev Web API module existence

Without these checks, regressions in WebUI governance policies would go undetected.

---

## 2. Decision

Add a dedicated "Dev WebUI governance" section to `cmd_dev_check()` in `hermes_cli/main.py`. Extract two helper functions for reusability and testability:

- `_webui_check_gitignore()` — validates that paths are covered by `.gitignore`
- `_webui_check_openapi()` — validates static OpenAPI path count, allowed routes, and forbidden route absence

All checks remain fast, read-only, and require no service startup.

---

## 3. Checks Added

| Check | Label | PASS/FAIL/WARN |
|-------|-------|----------------|
| WebUI app directory | `WebUI app` | FAIL if `apps/hermes-dev-webui/` missing |
| package.json | `WebUI package` | FAIL if `apps/hermes-dev-webui/package.json` missing |
| Build artifact ignore | `Build artifacts` | FAIL if `dist/` or `*.tsbuildinfo` not ignored |
| Visual-review ignore | `Visual review` | FAIL if `visual-review/` not ignored |
| Playwright artifact ignore | `Playwright artifacts` | FAIL if `playwright-report/`, `test-results/`, `blob-report/` not ignored |
| Playwright config | `Playwright config` | FAIL if `playwright.config.ts` missing |
| Smoke spec | `Smoke spec` | FAIL if `phase-0e-03-smoke.spec.ts` missing |
| Smoke runner | `Smoke runner` | FAIL if `run-dev-webui-smoke.sh` missing or not executable |
| test:smoke script | `Smoke script` | FAIL if `test:smoke` missing from package.json |
| test:smoke:0e03 script | `Smoke 0e03 script` | WARN if `test:smoke:0e03` missing from package.json |
| OpenAPI path count | `OpenAPI paths` | FAIL if not exactly 11 |
| OpenAPI route presence | `OpenAPI routes` | FAIL if any allowed route missing |
| Forbidden routes | `Forbidden routes` | FAIL if any forbidden route appears |
| Dev Web API module | `Dev Web API module` | FAIL if `dev_web_api.py` missing |
| WebUI section marker | `WebUI section` | PASS (section ran) |

---

## 4. PASS / WARN / FAIL Semantics

### FAIL conditions

- WebUI app directory missing
- package.json missing
- Build artifacts not ignored by `.gitignore`
- Visual-review not ignored by `.gitignore`
- Playwright artifacts not ignored by `.gitignore`
- Playwright config missing
- Smoke spec missing
- Smoke runner missing or not executable
- `test:smoke` script missing
- OpenAPI YAML missing or not parseable
- OpenAPI path count ≠ 11
- Allowed route missing from OpenAPI
- Forbidden route present in OpenAPI
- Dev Web API module missing

### WARN conditions

- `test:smoke:0e03` script missing (runner may still work with `test:smoke`)

### PASS conditions

- All critical governance checks satisfied

---

## 5. No Service Startup Guarantee

`dev-check` with WebUI checks:

- Does NOT start Dev API
- Does NOT start WebUI
- Does NOT start Dev Gateway or Dashboard
- Does NOT run Playwright
- Does NOT run `pnpm build`, `pnpm test`, or `pnpm lint`
- Does NOT make network requests
- Does NOT access `~/.hermes`
- Does NOT modify any files
- Completes in under 5 seconds

---

## 6. OpenAPI Static Validation

The OpenAPI validation reads `docs/webui/openapi/dev-web-api-v1.yaml` as a static file:

- Parses YAML with `yaml.safe_load`
- Checks `paths` count = 11
- Verifies all 11 allowed business routes are present with correct methods
- Checks no forbidden route substrings appear (`/reviews`, `/agent/run`, `/tools`, `/files/upload`)
- Checks no extra HTTP methods on allowed routes (e.g., DELETE on `/sessions`)

Allowed routes:

| Path | Method |
|------|--------|
| `/status` | GET |
| `/files/status` | GET |
| `/sessions` | GET |
| `/sessions/{sessionId}` | GET |
| `/sessions/{sessionId}/messages` | GET |
| `/memory/status` | GET |
| `/memory/categories` | GET |
| `/memory/items` | GET |
| `/memory/items/{memoryId}` | GET |
| `/context/preview` | POST |
| `/agent/status` | GET |

---

## 7. Artifact Policy Validation

Build artifact, visual-review, and Playwright artifact checks use `git check-ignore -v` via the existing `_git_value` helper. This is read-only and does not modify the index.

Checked paths:

- `apps/hermes-dev-webui/dist/index.html`
- `apps/hermes-dev-webui/tsconfig.app.tsbuildinfo`
- `apps/hermes-dev-webui/visual-review/phase-0b/`
- `apps/hermes-dev-webui/playwright-report/`
- `apps/hermes-dev-webui/test-results/`
- `apps/hermes-dev-webui/blob-report/`

---

## 8. Smoke Runner Validation

Checks `scripts/run-dev-webui-smoke.sh`:

- Exists as a file
- Is executable (`os.access(path, os.X_OK)`)

Does NOT execute the script.

---

## 9. How to Run

```bash
./scripts/run-dev-hermes.sh dev-check
# or directly:
python -m hermes_cli.main dev-check
```

---

## 10. Validation Result

| Check | Result |
|-------|--------|
| compileall | PASS |
| Unit tests (17 tests) | 17/17 PASS |
| dev-check output | All WebUI checks PASS |
| memory-check | PASS |
| No service startup | Confirmed (<5s execution) |

---

## 11. Non-goals

- No runtime OpenAPI validation (no service startup)
- No Playwright execution
- No frontend build or lint
- No modification to existing checks
- No new CLI commands
- No changes to Dev Web API business functionality

---

## 12. Follow-up

- Phase 0E-06: Phase 1 Safety Boundary Draft
- Phase 0E-Release: Final verification and push
