# Phase 1G-08: Pilot Operator Guide

## Document Information

| Field | Value |
|-------|-------|
| Phase | 1G-08 |
| Title | Pilot Operator Guide |
| Audience | The Pilot operator (the person who executes the Pilot). Not end users. |
| Status | Prepared (Pilot execution pending explicit approval) |
| Date | 2026-06-14 |
| Branch | `dev-huangruibang` |
| Pilot Acceptance ID | `PILOT-1G-08-001` |
| Related Release Candidate | `RC-1G-07-001` (Phase 1G-07, **GO**) |
| Baseline HEAD | `6f9176953cec7676d668aa3b4b7a654a374834de` |
| Scope | Step-by-step operator instructions for executing `PILOT-1G-08-001`. No code change. |

---

## 1. Operator Responsibilities

As the Pilot operator you:

- execute the Pilot against the **development** instance only;
- keep all safety boundaries true throughout and after the run;
- capture evidence per scenario into the acceptance record;
- record any defect against the defect / feedback template;
- never reopen Phase 1G-04, never expand `STATIC_ALLOWLIST`, never touch the
  Production Gateway, never access `~/.hermes` or production `state.db`;
- record a PASS / NO-GO / PAUSED outcome against the exit criteria;
- never push, never force push, never rebase, never `git reset --hard`.

---

## 2. Before-Pilot Checklist

- [ ] `HERMES_HOME=/Users/huangruibang/Code/hermes-home-dev` is set.
- [ ] All execute gate env vars and all provider key env vars are **unset**.
- [ ] Branch is `dev-huangruibang`; HEAD is `6f9176953…`; local == remote;
      ahead/behind `0 / 0`; tracked worktree clean; only `.claude/` untracked.
- [ ] Route governance = 34 / 34 / 5 / 0 / 1 / 1.
- [ ] `STATIC_ALLOWLIST = frozenset({"clarify"})`.
- [ ] Production Gateway PID = `69355` (exactly one process); Dev Gateway
      stopped; Dashboard not started; `5180` / `5181` free.
- [ ] A fresh copy of the acceptance record template is ready to fill.

---

## 3. Environment Setup

```bash
cd /Users/huangruibang/Code/hermes-agent-dev

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

---

## 4. Git Baseline Check

```bash
git status --short --branch
git rev-parse HEAD
git rev-parse origin/dev-huangruibang
git rev-list --left-right --count origin/dev-huangruibang...HEAD
```

Expected: branch `dev-huangruibang`; HEAD `6f9176953…`; local == remote;
ahead/behind `0 / 0`; tracked worktree clean; only `.claude/` untracked.

---

## 5. Production PID Check

```bash
ps aux | grep '[h]ermes_cli.main gateway run'        # expect PID 69355 only
./scripts/run-dev-hermes.sh gateway-dev status        # Dev Gateway (read-only)
lsof -nP -iTCP:5180 -sTCP:LISTEN || echo "5180 free"
lsof -nP -iTCP:5181 -sTCP:LISTEN || echo "5181 free"
```

Expected: Production Gateway PID `69355`, exactly one production gateway
process; Dev Gateway stopped; `5180` / `5181` free.

> Never read from or write to `~/.hermes`. Never access production `state.db`.
> Production-untouched is established only via the PID, the dev `HERMES_HOME`
> isolation, the port state, the git diff scope, and the runtime safety gates.

---

## 6. Port Check

```bash
lsof -nP -iTCP:5180 -sTCP:LISTEN || echo "5180 free"
lsof -nP -iTCP:5181 -sTCP:LISTEN || echo "5181 free"
```

Both must be free before and after the Pilot.

---

## 7. Backend Validation

Route governance:

```bash
./scripts/run_tests.sh tests/test_dev_check_webui.py tests/test_dev_web_0c06_closure.py -- -q
```

Expected: 124 passed / 0 failed; OpenAPI 34 / runtime 34 / Tool GET 5 / Tool
write 0 / dry-run 1 / execution 1; `STATIC_ALLOWLIST = frozenset({"clarify"})`.

Related backend regression:

```bash
./scripts/run_tests.sh \
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
  tests/test_dev_web_0c06_closure.py \
  -- -q
```

Expected: 19 files, 1471 passed / 0 failed.

---

## 8. Frontend Validation

```bash
cd apps/hermes-dev-webui
pnpm type-check      # note: type-check, not typecheck
pnpm lint
pnpm test
pnpm build
cd ../..
```

Expected: type-check pass; lint 0 errors / 0 warnings; vitest 674 passed
(31 files); build pass.

---

## 9. Smoke Harness

```bash
cd /Users/huangruibang/Code/hermes-agent-dev
export HERMES_HOME=/Users/huangruibang/Code/hermes-home-dev
./scripts/run-dev-webui-execute-audit-smoke.sh all
```

Expected overall:

- Profile A (blocked): 6 passed, 1 skipped, 0 failed.
- Profile B (completed): 7 passed, 0 failed.
- Final ports `5180` / `5181` free.
- Production Gateway PID `69355` unchanged.

See `docs/webui/phase-1g-06-smoke-harness-runbook.md` for the exact gate env
vars per profile and the common-mistake note.

---

## 10. Recording Evidence

Fill the acceptance record
(`docs/webui/phase-1g-08-pilot-acceptance-record-template.md`) as you go:

- One row per scenario (A–O): status, actual result, evidence, defect ID,
  severity, notes.
- Record the two server-gate configurations used and their results.
- Record the Production Gateway PID before and after.
- Record the final `5180` / `5181` port state.

Evidence must not contain a secret, an API key, the raw confirmation token, the
full token hash, or raw arguments.

---

## 11. Recording Defects

For each finding, open a defect record against
`docs/webui/phase-1g-08-pilot-defect-feedback-template.md`:

- Assign a severity (P0 / P1 / P2) per the template.
- Record steps to reproduce, expected, actual, environment.
- Record the route-governance / security-boundary / production impact (default
  "none" unless the finding actually affects them).

---

## 12. Handling Failures

- **A scenario that fails its pass criteria** → record FAIL with the observed
  result and the defect ID; continue if the severity allows (P2 / P1), or stop
  if P0.
- **A gate that fails** (backend regression, frontend build, smoke, memory-check,
  dev-check) → record as P1 (or P0 if it touches a boundary); pause the Pilot.

---

## 13. Pause Criteria

Pause the Pilot and record a PAUSED outcome if:

- an unresolved P1 is blocking a required scenario but does not touch a P0
  boundary;
- an environment issue occurs (port conflict, smoke harness abort) that does not
  indicate a P0.

Resume only after the blocker is cleared and the baseline is re-verified.

---

## 14. Rollback Escalation

If rollback is needed:

- **Stop and request user confirmation** first.
- Use a new `git revert` commit — never `git reset --hard`, never force push,
  never production state mutation.
- Preserve evidence and logs before any controlled revert.
- See `docs/webui/phase-1g-05-ops-and-rollback-runbook.md` for the full runbook.

---

## 15. No-Go Criteria

Record a NO-GO and stop if any of these occur:

- any P0 boundary violation (allowlist, Provider, secret leak, production access,
  raw token / tokenHash / raw-args exposure);
- any unresolved P1 at Pilot end;
- route governance changed or allowlist expanded;
- Production Gateway PID `69355` changed;
- `~/.hermes` or production `state.db` accessed.

A NO-GO does **not** reopen Phase 1G-04. It is reported as a Pilot finding and
addressed via a separately approved phase.

---

## 16. After-Pilot Checklist

- [ ] Every scenario has a recorded status.
- [ ] All evidence captured; no secret / token / tokenHash / raw-args exposure.
- [ ] All defects have a record with severity + category.
- [ ] Production Gateway PID `69355` confirmed unchanged.
- [ ] `5180` / `5181` confirmed free.
- [ ] `memory-check` PASS; `dev-check` PASS (or only `.claude/` WARN).
- [ ] Acceptance record signed off (PASS / NO-GO / PAUSED).
- [ ] A local commit was created for any new Pilot record docs (no push).

---

## 17. Forbidden Actions

- Do **not** access `~/.hermes` (no `ls`, `stat`, `find`, `cat`, `sqlite3`, `du`,
  mtime).
- Do **not** access production `state.db`.
- Do **not** run `setup-hermes.sh`.
- Do **not** force push (`git push --force`, `--force-with-lease`, `-f`, `--all`,
  `--tags`).
- Do **not** rebase, merge, or `git reset --hard`.
- Do **not** expand `STATIC_ALLOWLIST` beyond `clarify`.
- Do **not** enable Provider Schema / Provider API.
- Do **not** stop, restart, replace, or reconfigure the Production Gateway.
- Do **not** commit audit JSONL or `.claude/`.
- Do **not** push.

---

## 18. Quick-Reference Command Block

```bash
cd /Users/huangruibang/Code/hermes-agent-dev
export HERMES_HOME=/Users/huangruibang/Code/hermes-home-dev
unset HERMES_TOOL_EXECUTION_ENABLED HERMES_AGENT_TOOLS_ENABLED HERMES_TOOL_HANDLER_CALL_ENABLED
unset OPENAI_API_KEY ANTHROPIC_API_KEY ZAI_API_KEY GEMINI_API_KEY GOOGLE_API_KEY OPENROUTER_API_KEY

git status --short --branch
git rev-parse HEAD
git rev-parse origin/dev-huangruibang
git rev-list --left-right --count origin/dev-huangruibang...HEAD

./scripts/run_tests.sh tests/test_dev_check_webui.py tests/test_dev_web_0c06_closure.py -- -q
./scripts/run-dev-webui-execute-audit-smoke.sh all
./scripts/run-dev-hermes.sh memory-check
./scripts/run-dev-hermes.sh dev-check
```

---

## 19. Cross-References

- Pilot acceptance pack: `docs/webui/phase-1g-08-pilot-acceptance-pack.md`.
- Participant guide: `docs/webui/phase-1g-08-pilot-participant-guide.md`.
- Acceptance record template:
  `docs/webui/phase-1g-08-pilot-acceptance-record-template.md`.
- Defect / feedback template:
  `docs/webui/phase-1g-08-pilot-defect-feedback-template.md`.
- Exit criteria: `docs/webui/phase-1g-08-pilot-exit-criteria.md`.
- Smoke harness runbook: `docs/webui/phase-1g-06-smoke-harness-runbook.md`.
- Ops / rollback runbook: `docs/webui/phase-1g-05-ops-and-rollback-runbook.md`.
- Release checklist: `docs/webui/phase-1g-05-release-checklist.md`.

---

*Phase 1G-08 Pilot Operator Guide — operator instructions for executing
`PILOT-1G-08-001` against RC `RC-1G-07-001` (GO). Production Gateway PID `69355`
is never affected.*
