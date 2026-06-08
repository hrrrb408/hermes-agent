# Phase 0E-01: Build Artifact Policy

**Status:** Completed
**Date:** 2026-06-08
**Branch:** dev-huangruibang
**Base commit:** 17c13843a (Phase 0E-00 governance scope)

---

## 1. Problem

Dev WebUI build artifacts (`dist/` and `*.tsbuildinfo`) were tracked by Git. Every `pnpm build` produced hash-renamed files and updated build metadata, causing tracked file modifications. Stage closure workflows required `git restore` to undo these changes, introducing unnecessary friction.

---

## 2. Audit Result

### 2.1 Git Tracking

5 files were tracked before this task:

```
apps/hermes-dev-webui/dist/assets/index-AxamzU0w.js
apps/hermes-dev-webui/dist/assets/index-CCl_6OPG.css
apps/hermes-dev-webui/dist/index.html
apps/hermes-dev-webui/tsconfig.app.tsbuildinfo
apps/hermes-dev-webui/tsconfig.node.tsbuildinfo
```

Note: `tsconfig.node.tsbuildinfo` was discovered during execution — it was also tracked and modified by `vue-tsc -b`, bringing the total from 4 (estimated in 0E-00) to 5.

### 2.2 Build Dependency Audit

| Source | Searched | References Found | Deployment Dependency |
|--------|----------|-----------------|---------------------|
| `scripts/` | All `.py`, `.sh` files | None | No |
| `gateway/` | All Python files | None | No |
| `hermes_cli/` | All Python files | None | No |
| `docs/` | Phase 0E docs | Descriptive only (problem statement) | No |
| `package.json` | Build scripts | Standard Vite build only | No |
| `vite.config.*` | Build config | Standard output to `dist/` | No |

**Conclusion:** No deployment process, script, or CI pipeline depends on committed `dist/`. The Dev WebUI uses `pnpm dev` (Vite dev server) in development. Build output is only used for build verification (`pnpm build`), not served statically.

---

## 3. Decision

**Dev WebUI build artifacts must not be tracked by Git.**

Reasons:
1. `pnpm build` generates hash-renamed files (`index-*.js`, `index-*.css`) that change every build
2. `tsbuildinfo` files are TypeScript incremental build caches, not source code
3. `dist/` is build output, not source code
4. Repeated `git restore` at stage closure is unnecessary friction
5. No deployment or CI dependency on committed build artifacts
6. The root `.gitignore` already follows this pattern for `apps/desktop/dist/` and `hermes_cli/web_dist/`

---

## 4. .gitignore Rules Added

```gitignore
# Hermes Dev WebUI build artifacts
/apps/hermes-dev-webui/dist/
/apps/hermes-dev-webui/*.tsbuildinfo
/apps/hermes-dev-webui/tsconfig*.tsbuildinfo
```

Design choices:
- Leading `/` anchors to repo root — avoids accidentally ignoring `dist/` in other projects
- Covers `dist/` directory and all contents
- Covers `*.tsbuildinfo` and `tsconfig*.tsbuildinfo` for both `tsconfig.app.tsbuildinfo` and `tsconfig.node.tsbuildinfo`
- Placed adjacent to existing desktop build artifact entries for discoverability

Verification:
```
$ git check-ignore -v apps/hermes-dev-webui/dist/index.html
.gitignore:79:/apps/hermes-dev-webui/dist/   apps/hermes-dev-webui/dist/index.html

$ git check-ignore -v apps/hermes-dev-webui/tsconfig.app.tsbuildinfo
.gitignore:81:/apps/hermes-dev-webui/tsconfig*.tsbuildinfo   apps/hermes-dev-webui/tsconfig.app.tsbuildinfo

$ git check-ignore -v apps/hermes-dev-webui/tsconfig.node.tsbuildinfo
.gitignore:81:/apps/hermes-dev-webui/tsconfig*.tsbuildinfo   apps/hermes-dev-webui/tsconfig.node.tsbuildinfo
```

---

## 5. Files Removed from Git Tracking

```
git rm -r --cached apps/hermes-dev-webui/dist
  → apps/hermes-dev-webui/dist/assets/index-AxamzU0w.js
  → apps/hermes-dev-webui/dist/assets/index-CCl_6OPG.css
  → apps/hermes-dev-webui/dist/index.html

git rm --cached apps/hermes-dev-webui/tsconfig.app.tsbuildinfo
  → apps/hermes-dev-webui/tsconfig.app.tsbuildinfo

git rm --cached apps/hermes-dev-webui/tsconfig.node.tsbuildinfo
  → apps/hermes-dev-webui/tsconfig.node.tsbuildinfo
```

All local files preserved on disk. Only Git index entries removed.

---

## 6. Verification

| Check | Result |
|-------|--------|
| `pnpm lint` | ✅ Pass |
| `pnpm type-check` | ✅ Pass |
| `pnpm test` | ✅ 324 tests, 20 test files, all passing |
| `pnpm build` | ✅ Success (new hashes: `index-CTrHjy4d.css`, `index-f2k2pv_a.js`) |
| `git status` after build | ✅ No `dist/` or `tsbuildinfo` tracked modifications |
| `git check-ignore` | ✅ All 4 artifact paths matched |
| `memory-check` | ✅ PASS |
| `dev-check` | ✅ WARN (5 visual-review dirs only — expected, 0E-02 scope) |
| `compileall` | ✅ PASS |

---

## 7. Non-goals

- No changes to `apps/desktop/` or other workspace build artifacts
- No changes to frontend or backend source code
- No changes to build process or Vite configuration
- No local `.gitignore` file creation (root `.gitignore` is sufficient)
- No visual-review policy changes (0E-02 scope)
- No Playwright, smoke runner, or dev-check enhancement

---

## 8. Follow-up

- **0E-02:** Visual Review Artifact Policy — handle the 5 remaining untracked `visual-review/` directories
- **0E-05:** dev-check Enhancement — add build artifact dirty detection to `cmd_dev_check()`

---

## 9. Acceptance

Phase 0E-01 completed. Build artifact policy is now enforced. `pnpm build` no longer leaves tracked changes.
