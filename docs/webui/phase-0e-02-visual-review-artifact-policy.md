# Phase 0E-02: Visual Review Artifact Policy

**Status:** Completed
**Date:** 2026-06-08
**Branch:** dev-huangruibang
**Base commit:** 04ce7eb9b (Phase 0E-01 build artifact policy)

---

## 1. Problem

The Dev WebUI working directory contained 5 untracked `visual-review/` subdirectories that persisted across all Phase 0B/0C/0D/0E work. These directories caused `dev-check` to continuously report `WARN` for dirty worktree, masking genuine dirty-tree issues. The directories contain local human visual review screenshots from Phase 0B theme refinement work.

---

## 2. Audit Result

### 2.1 Visual Review Artifacts

| Metric | Value |
|--------|-------|
| Total subdirectories | 9 |
| Total files | 62 |
| Tracked files | 10 (phase-0a PNGs, committed before this task) |
| Untracked directories | 5 (phase-0b, phase-0b-1, phase-0b-1-1, phase-0b-1-2, phase-0b-1-3) |
| Untracked files | 52 (all PNG screenshots) |
| Non-image/non-artifact files | 0 |

Directory structure:
```
apps/hermes-dev-webui/visual-review/
├── phase-0a/           (10 tracked PNGs — ink/ and sakura-night/ subdirs)
├── phase-0b/           (8 untracked PNGs)
├── phase-0b-1/         (11 untracked PNGs)
├── phase-0b-1-1/       (8 untracked PNGs + before/ subdir)
├── phase-0b-1-2/       (18 untracked PNGs)
└── phase-0b-1-3/       (7 untracked PNGs)
```

### 2.2 Dependency Audit

| Source | Searched | References Found | Dependency |
|--------|----------|-----------------|------------|
| `scripts/` | All `.py`, `.sh` files | None | No |
| `hermes_cli/` | All Python files | None | No |
| `apps/hermes-dev-webui/` | `package.json` | None | No |
| `docs/` | Phase 0B–0E docs | Descriptive only (problem statement) | No |
| `dev-check` | `hermes_cli/main.py` | Uses `git status --porcelain` | No special handling |

**Conclusion:** No script, test, build process, or deployment pipeline depends on the `visual-review/` directory. The directories are purely local human review artifacts. The `dev-check` dirty worktree WARN is caused by standard `git status --porcelain` detecting the untracked directories — no code explicitly references them.

### 2.3 Pre-existing Tracked Files

10 PNG files in `phase-0a/` were committed to Git before this task. These remain tracked (`.gitignore` does not affect already-tracked files). This is a pre-existing condition:

```
apps/hermes-dev-webui/visual-review/phase-0a/ink/ink-final-assistant-inline-code.png
apps/hermes-dev-webui/visual-review/phase-0a/ink/ink-final-bottom-bamboo-water.png
apps/hermes-dev-webui/visual-review/phase-0a/ink/ink-final-code-tools.png
apps/hermes-dev-webui/visual-review/phase-0a/ink/ink-final-first-screen.png
apps/hermes-dev-webui/visual-review/phase-0a/ink/ink-theme-first-screen.png
apps/hermes-dev-webui/visual-review/phase-0a/ink/ink-theme-full-page.png
apps/hermes-dev-webui/visual-review/phase-0a/sakura-night/sakura-night-01-hero.png
apps/hermes-dev-webui/visual-review/phase-0a/sakura-night/sakura-night-02-messages.png
apps/hermes-dev-webui/visual-review/phase-0a/sakura-night/sakura-night-03-code-tools.png
apps/hermes-dev-webui/visual-review/phase-0a/sakura-night/sakura-night-04-footer.png
```

These tracked files are not in scope for this task. They do not cause `dev-check` WARN (they are tracked and unchanged). A future cleanup task may `git rm --cached` them.

---

## 3. Decision

**Dev WebUI visual-review artifacts are local review artifacts and must not be tracked by Git.**

Reasons:
1. Visual-review directories contain human visual review output (screenshots)
2. They may contain UI screenshots with potentially sensitive layout data
3. They should not enter Git history — binary blobs bloat repository size
4. Long-term untracked status caused `dev-check` to persistently report WARN
5. The WARN masked genuine dirty-tree issues during Phase 0C/0D development
6. Phase 0D/0E governance identified this as an engineering hygiene problem
7. Future formal visual regression should use Playwright smoke matrix (0E-03) or dedicated artifact storage, not committed screenshots

---

## 4. .gitignore Rule Added

```gitignore
# Hermes Dev WebUI visual review artifacts
/apps/hermes-dev-webui/visual-review/
```

Design choices:
- Leading `/` anchors to repo root — avoids accidentally ignoring `visual-review/` in other projects or docs
- Covers the entire `visual-review/` directory and all contents
- Does not affect `docs/` screenshots or other repository images
- Does not affect future Playwright test artifacts (those will have their own `.gitignore` entries in 0E-03)
- Placed adjacent to existing Dev WebUI build artifact entries for discoverability

Verification:
```
$ git check-ignore -v apps/hermes-dev-webui/visual-review/phase-0b/
.gitignore:84:/apps/hermes-dev-webui/visual-review/   apps/hermes-dev-webui/visual-review/phase-0b/

$ git check-ignore -v apps/hermes-dev-webui/visual-review/phase-0b-1/
.gitignore:84:/apps/hermes-dev-webui/visual-review/   apps/hermes-dev-webui/visual-review/phase-0b-1/

$ git check-ignore -v apps/hermes-dev-webui/visual-review/phase-0b-1-1/
.gitignore:84:/apps/hermes-dev-webui/visual-review/   apps/hermes-dev-webui/visual-review/phase-0b-1-1/

$ git check-ignore -v apps/hermes-dev-webui/visual-review/phase-0b-1-2/
.gitignore:84:/apps/hermes-dev-webui/visual-review/   apps/hermes-dev-webui/visual-review/phase-0b-1-2/

$ git check-ignore -v apps/hermes-dev-webui/visual-review/phase-0b-1-3/
.gitignore:84:/apps/hermes-dev-webui/visual-review/   apps/hermes-dev-webui/visual-review/phase-0b-1-3/
```

All 5 previously untracked directories now match the `.gitignore` rule.

---

## 5. Existing Local Directories

The following directories remain on disk, untouched:

- `apps/hermes-dev-webui/visual-review/phase-0a/` (10 tracked PNGs)
- `apps/hermes-dev-webui/visual-review/phase-0b/` (8 PNGs, now ignored)
- `apps/hermes-dev-webui/visual-review/phase-0b-1/` (11 PNGs, now ignored)
- `apps/hermes-dev-webui/visual-review/phase-0b-1-1/` (8+ PNGs, now ignored)
- `apps/hermes-dev-webui/visual-review/phase-0b-1-2/` (18 PNGs, now ignored)
- `apps/hermes-dev-webui/visual-review/phase-0b-1-3/` (7 PNGs, now ignored)

**No deletion.** No migration. No archival. No renaming.

---

## 6. dev-check Behavior

| State | Git worktree check | dev-check result |
|-------|-------------------|------------------|
| Before 0E-02 | 5 untracked visual-review dirs | WARN (dirty) |
| After 0E-02 (pre-commit) | `.gitignore` modification only | WARN (dirty — expected, pending commit) |
| After 0E-02 (post-commit) | Clean | PASS |

**No code changes to `dev-check`** (`hermes_cli/main.py`). The existing `git status --porcelain` check in `cmd_dev_check()` correctly detects real dirty-tree state. Once `.gitignore` is committed, `git status --porcelain` returns empty, and the worktree check reports PASS.

This confirms Plan A (`.gitignore` only) is sufficient. Plan B (dev-check allowlist) is unnecessary.

---

## 7. Verification

| Check | Result |
|-------|--------|
| `memory-check` | PASS |
| `dev-check` (pre-commit) | WARN (`.gitignore` modification only — expected) |
| `dev-check` (post-commit, expected) | PASS |
| `compileall` | PASS |
| `git check-ignore` (all 5 dirs) | All matched |
| `git status` (pre-commit) | Only `.gitignore` modified |
| `git status` (post-commit, expected) | Clean |
| 0E-01 build artifact rules | Still effective (dist/, tsbuildinfo) |
| Existing directories on disk | Untouched (62 files) |
| Tracked phase-0a files | Still tracked (10 PNGs) |

This task did not modify frontend/backend business code. Previously passed: 479 backend tests + 324 frontend tests. 0E-01 validated 324 frontend tests.

---

## 8. Non-goals

- No deletion of existing visual-review directories
- No `git rm --cached` of tracked phase-0a PNGs (pre-existing, separate concern)
- No migration or archival of visual-review contents
- No new review directories or review workflow
- No Playwright integration or visual regression automation (0E-03 scope)
- No dev-check code changes (0E-05 scope)
- No business API, Memory, Context, Agent, Session, or Message changes

---

## 9. Follow-up

- **0E-03:** Playwright Smoke Matrix — automated visual validation replaces manual screenshot workflows
- **0E-05:** dev-check Enhancement — optional visual-review whitelist check (no longer needed if `.gitignore` suffices)
- **Future cleanup:** Consider `git rm --cached` for the 10 tracked phase-0a PNGs to fully remove visual-review from Git history

---

## 10. Acceptance

Phase 0E-02 completed. Visual review artifact policy is now enforced. `dev-check` will report PASS for Git worktree once this commit is applied.
