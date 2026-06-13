# Phase 1G-05: Release Checklist

## Document Information

| Field | Value |
|-------|-------|
| Phase | 1G-05 |
| Title | Release Checklist — Dev WebUI Pre-Release Gate Sequence |
| Status | Authored |
| Date | 2026-06-13 |
| Branch | `dev-huangruibang` |
| Candidate | Phase 1G-04 sealed mainline at `94f22f67b` |
| Scope | Copy-paste command checklist for a release go/no-go. No code change. |

---

## 1. Purpose

This checklist is the **pre-release gate sequence** for the Hermes Dev WebUI.
Every item must be verified before a release go decision. Commands are
copy-pasteable and use the dev environment exclusively.

**Environment (set before running):**

```bash
export HERMES_HOME=/Users/huangruibang/Code/hermes-home-dev

unset HERMES_AGENT_RUN_ENABLED
unset HERMES_TOOL_EXECUTION_ENABLED
unset HERMES_AGENT_TOOLS_ENABLED
unset HERMES_TOOL_HANDLER_CALL_ENABLED
unset HERMES_POST_EXECUTION_AUDIT_ENABLED

unset XAI_API_KEY XAI_BASE_URL GROK_API_KEY GROK_BASE_URL
unset OPENAI_API_KEY ANTHROPIC_API_KEY ZAI_API_KEY
unset GEMINI_API_KEY GOOGLE_API_KEY OPENROUTER_API_KEY
```

All commands run from the repo root
(`/Users/huangruibang/Code/hermes-agent-dev`) unless stated otherwise.

---

## 2. Git & Branch

```bash
git branch --show-current                              # expect: dev-huangruibang
git status --short --branch                            # expect: clean, only .claude/ untracked
git rev-parse HEAD                                     # expect: 94f22f67b... (or release HEAD)
git rev-parse origin/dev-huangruibang                  # expect: same as local HEAD
git rev-list --left-right --count origin/dev-huangruibang...HEAD   # expect: 0 / 0 (pre-push) or local ahead
```

| # | Item | Pass criterion |
|---|------|----------------|
| 1 | Branch | `dev-huangruibang` |
| 2 | Worktree | clean; only `.claude/` untracked |
| 3 | HEAD | matches intended release commit |
| 4 | Remote sync | local and remote in sync (ahead/behind as intended) |

---

## 3. Route Governance & Allowlist

```bash
.venv/bin/python -m pytest -q \
  tests/test_dev_check_webui.py \
  tests/test_dev_web_0c06_closure.py
```

| # | Item | Pass criterion |
|---|------|----------------|
| 5 | Route governance | OpenAPI 34 / runtime 34 / Tool GET 5 / Tool write 0 / dry-run 1 / execution 1 |
| 6 | `STATIC_ALLOWLIST` | exactly `frozenset({"clarify"})` |
| 7 | Allowlist expansion | none |

```bash
rg -n "STATIC_ALLOWLIST" hermes_cli tests docs/webui apps/hermes-dev-webui \
  --glob '!**/node_modules/**' --glob '!**/dist/**'
```

Confirm every allowlist reference keeps it exactly `frozenset({"clarify"})`.

---

## 4. Kill Switches (default safe posture)

| # | Item | Pass criterion |
|---|------|----------------|
| 8 | Kill switches | unset by default; execute blocks before any handler call |
| 9 | API keys | unset; no real Provider key in env |

```bash
echo "HERMES_TOOL_EXECUTION_ENABLED=${HERMES_TOOL_EXECUTION_ENABLED:-<unset>}"
echo "HERMES_AGENT_TOOLS_ENABLED=${HERMES_AGENT_TOOLS_ENABLED:-<unset>}"
echo "HERMES_TOOL_HANDLER_CALL_ENABLED=${HERMES_TOOL_HANDLER_CALL_ENABLED:-<unset>}"
```

All three should print `<unset>` in the release-default environment.

---

## 5. Production Isolation

```bash
./scripts/run-dev-hermes.sh dev-info
./scripts/run-dev-hermes.sh gateway-dev status

ps aux | grep '[h]ermes_cli.main gateway run'        # expect PID 69355 only
lsof -nP -iTCP:5180 -sTCP:LISTEN || echo "5180 free" # expect free
lsof -nP -iTCP:5181 -sTCP:LISTEN || echo "5181 free" # expect free
```

| # | Item | Pass criterion |
|---|------|----------------|
| 10 | Production Gateway PID | `69355`, exactly one production gateway process |
| 11 | Dev Gateway | stopped |
| 12 | Ports `5180` / `5181` | free before gates |

---

## 6. Backend Regression

```bash
.venv/bin/python -m pytest -q \
  tests/test_dev_web_tool_audit_read.py \
  tests/test_dev_web_tool_audit_read_api.py \
  tests/test_dev_web_tool_handler_call.py \
  tests/test_dev_web_tool_post_execution_audit.py \
  tests/test_dev_web_tool_dispatch.py \
  tests/test_dev_web_tool_handler_lookup.py \
  tests/test_dev_web_tool_pre_execution_audit.py \
  tests/test_dev_web_tool_execute_digest.py \
  tests/test_dev_web_tool_execute_confirmation.py \
  tests/test_dev_web_tool_execute_preflight.py \
  tests/test_dev_web_tool_policy_api.py \
  tests/test_dev_web_tool_schema_preview_api.py \
  tests/test_dev_web_tool_dry_run.py \
  tests/test_dev_web_tool_dry_run_api.py \
  tests/test_dev_web_tool_dry_run_audit.py \
  tests/test_dev_web_tool_execute.py \
  tests/test_dev_web_tool_execute_api.py \
  tests/test_dev_check_webui.py \
  tests/test_dev_web_0c06_closure.py
```

Reference (sealed baseline): **1471 passed, 2 skipped, 5 deselected, 0 failed.**

```bash
python -m compileall \
  hermes_cli/dev_web_api.py \
  hermes_cli/dev_web_tool_policy.py \
  hermes_cli/dev_web_tool_dry_run.py \
  hermes_cli/dev_web_tool_dry_run_audit.py \
  hermes_cli/dev_web_tool_execute.py \
  hermes_cli/dev_web_tool_execute_preflight.py \
  hermes_cli/dev_web_tool_execute_confirmation.py \
  hermes_cli/dev_web_tool_execute_digest.py \
  hermes_cli/dev_web_tool_pre_execution_audit.py \
  hermes_cli/dev_web_tool_handler_lookup.py \
  hermes_cli/dev_web_tool_dispatch.py \
  hermes_cli/dev_web_tool_handler_call.py \
  hermes_cli/dev_web_tool_post_execution_audit.py \
  hermes_cli/dev_web_tool_audit_read.py

python -m py_compile toolsets.py

ruff check \
  hermes_cli/dev_web_api.py \
  hermes_cli/dev_web_tool_policy.py \
  hermes_cli/dev_web_tool_execute.py \
  hermes_cli/dev_web_tool_dispatch.py \
  hermes_cli/dev_web_tool_handler_call.py \
  hermes_cli/dev_web_tool_post_execution_audit.py \
  hermes_cli/dev_web_tool_audit_read.py \
  hermes_cli/dev_web_tool_pre_execution_audit.py \
  tests/test_dev_web_tool_audit_read.py \
  tests/test_dev_web_tool_audit_read_api.py \
  tests/test_dev_web_tool_execute.py \
  tests/test_dev_web_tool_execute_api.py \
  tests/test_dev_check_webui.py \
  tests/test_dev_web_0c06_closure.py
```

| # | Item | Pass criterion |
|---|------|----------------|
| 13 | Backend regression | 0 failed (count may vary; must be 0 failed) |
| 14 | `compileall` | pass |
| 15 | `toolsets.py` compile | pass |
| 16 | `ruff check` | all checks passed |

---

## 7. Frontend Gates

```bash
cd apps/hermes-dev-webui
pnpm typecheck
pnpm lint
pnpm test
pnpm build
cd ../..
```

Reference (sealed baseline): typecheck pass; lint 0 errors / 0 warnings;
**vitest 674 passed (31 files)**; build pass.

| # | Item | Pass criterion |
|---|------|----------------|
| 17 | `pnpm typecheck` | pass |
| 18 | `pnpm lint` | 0 errors / 0 warnings |
| 19 | `pnpm test` | 0 failed |
| 20 | `pnpm build` | pass |

---

## 8. Browser Smoke / E2E

```bash
./scripts/run-dev-webui-smoke.sh          # full smoke cycle (Dev API 5181 + WebUI 5180)
```

Run in both gate configurations (see the Ops runbook for the exact env
combinations). Reference (sealed baseline):

- Blocked (`blocked_tool_handler_call_not_enabled`): **6 passed, 1 skipped, 0 failed**.
- Completed (`clarify_execution_completed`): **7 passed, 0 failed**.

| # | Item | Pass criterion |
|---|------|----------------|
| 21 | Browser smoke | 0 failed in both gate configurations |
| 22 | Ports after smoke | `5180` / `5181` free |
| 23 | Production Gateway PID after smoke | `69355` unchanged |

---

## 9. Hermes Gates

```bash
./scripts/run-dev-hermes.sh memory-check
./scripts/run-dev-hermes.sh dev-check
```

| # | Item | Pass criterion |
|---|------|----------------|
| 24 | `memory-check` | PASS |
| 25 | `dev-check` | PASS, or only `.claude/` dirty WARN |
| 26 | Route governance (dev-check) | 34 / 34 / 5 / 0 / 1 / 1 |
| 27 | Provider tool schema | not sent |
| 28 | Production isolation (dev-check) | PASS |

---

## 10. Forbidden File & Secret Scan

```bash
# Forbidden files must NOT appear in any staged/changed set:
git status --short | rg -n \
  "agent/|tools/|toolsets.py|runtime|memory|review|\.env|\.claude|\.hermes|state\.db|setup-hermes\.sh|tool-post-execution-audit\.jsonl|tool-pre-execution-audit\.jsonl|tool-dry-run-audit\.jsonl|confirmation-tokens\.jsonl" \
  || echo "no forbidden files"

# Audit JSONL / .claude must not be tracked:
git ls-files | rg -n \
  "\.claude/|tool-post-execution-audit\.jsonl|tool-pre-execution-audit\.jsonl|tool-dry-run-audit\.jsonl|confirmation-tokens\.jsonl" \
  && echo "TRACKED FORBIDDEN FILE — STOP" || echo "no tracked forbidden files"

# Secret scan over the tree (informational; review hits):
rg -n "sk-[A-Za-z0-9_-]{16,}|BEGIN PRIVATE KEY|password\s*=\s*['\"]" \
  hermes_cli tests docs/webui apps/hermes-dev-webui/src \
  --glob '!**/node_modules/**' --glob '!**/dist/**' || echo "no secret-like hits"
```

| # | Item | Pass criterion |
|---|------|----------------|
| 29 | Forbidden files | none changed/tracked |
| 30 | Audit JSONL committed | no |
| 31 | `.claude/` committed | no |
| 32 | Secret scan | no real secrets |

---

## 11. Rollback Plan

The rollback strategy is documented in
`docs/webui/phase-1g-05-ops-and-rollback-runbook.md`. In summary:

- **No automatic rollback** during the release task.
- If rollback is needed, **stop and request user confirmation** first.
- Use a **new revert commit** — never `git reset --hard`, never force push,
  never production state mutation.
- Preserve evidence and logs before any controlled revert.

| # | Item | Pass criterion |
|---|------|----------------|
| 33 | Rollback plan | documented; revert-commit based; no force/reset |

---

## 12. Go / No-Go

| # | Item | Pass criterion |
|---|------|----------------|
| 34 | Go / no-go decision | all items 1–33 pass → GO; any P0/P1 → NO-GO |

**GO requires:** items 1–33 all pass, no P0, no P1, route governance exactly
34 / 34 / 5 / 0 / 1 / 1, `STATIC_ALLOWLIST = frozenset({"clarify"})`, no
Provider Schema / API, no non-clarify execution, production Gateway PID `69355`
unchanged, no audit JSONL / `.claude/` commit, no secret leak.

**On NO-GO:** do not push; record the failure; address via a separately approved
phase. Do **not** reopen Phase 1G-04.

---

## 13. Quick-Reference Command Block

```bash
export HERMES_HOME=/Users/huangruibang/Code/hermes-home-dev
unset HERMES_TOOL_EXECUTION_ENABLED HERMES_AGENT_TOOLS_ENABLED HERMES_TOOL_HANDLER_CALL_ENABLED
unset OPENAI_API_KEY ANTHROPIC_API_KEY ZAI_API_KEY GEMINI_API_KEY GOOGLE_API_KEY OPENROUTER_API_KEY

git status --short --branch
git rev-parse HEAD
git rev-parse origin/dev-huangruibang
git rev-list --left-right --count origin/dev-huangruibang...HEAD

./scripts/run-dev-hermes.sh memory-check
./scripts/run-dev-hermes.sh dev-check

.venv/bin/python -m pytest -q tests/test_dev_check_webui.py tests/test_dev_web_0c06_closure.py
```

---

## 14. Phase 1G-06 Addendum — Release Rehearsal & Smoke Harness

Phase 1G-06 (Pilot Release Rehearsal / Smoke Harness Hardening) supersedes this
checklist's ad-hoc smoke section with a committed rehearsal baseline. It does
**not** change any item above.

- Phase 1G-04 remains **SEALED**. Phase 1G-05 remains the **pushed** readiness
  baseline. Phase 1G-06 adds no product capability and no route governance
  change (still 34 / 34 / 5 / 0 / 1 / 1; `STATIC_ALLOWLIST` still
  `frozenset({"clarify"})`).
- The execute/audit smoke is now driven by a committed dev-only harness:
  `scripts/run-dev-webui-execute-audit-smoke.sh` (item 21 above). It supports
  `blocked` / `completed` / `all` profiles, binds to `127.0.0.1` only, refuses
  production `HERMES_HOME`, and is self-cleaning.
- Gate profiles are now fixed: **Profile A** (upstream execution gates on,
  handler-call gate unset → `blocked_tool_handler_call_not_enabled`), **Profile
  B** (all three gates `=true` → `clarify_execution_completed`), optional
  **Profile C** (all gates unset → `blocked_by_kill_switch`).
- **Gate-config note:** unsetting *all* gates tests `blocked_by_kill_switch`,
  **not** `blocked_tool_handler_call_not_enabled`. To test the handler-call
  blocked decision, enable `HERMES_TOOL_EXECUTION_ENABLED=true` and
  `HERMES_AGENT_TOOLS_ENABLED=true` and leave `HERMES_TOOL_HANDLER_CALL_ENABLED`
  unset.
- Rehearsal docs: `docs/webui/phase-1g-06-pilot-release-rehearsal.md`,
  `docs/webui/phase-1g-06-smoke-harness-runbook.md`,
  `docs/webui/phase-1g-06-release-candidate-validation.md`,
  `docs/webui/phase-1g-06-go-no-go-template.md`.

---

*Phase 1G-05 Release Checklist — 34 pre-release items, copy-pasteable, dev-only.
Go requires all green, exact route governance, exact allowlist, production
isolation, and no secret / forbidden-file exposure.*
