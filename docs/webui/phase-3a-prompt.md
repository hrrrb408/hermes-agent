# Phase 3A Prompt Draft — Dev-only Agent Workflow MVP

## Document Information

| Field | Value |
|-------|-------|
| Phase | 3A |
| Title | Phase 3A Execution Prompt (Draft) |
| Status | Draft prepared — **NOT to be executed in this planning phase** |
| Date | 2026-06-15 |
| Branch | `dev-huangruibang` |
| Planning ID | `PHASE-3-PLANNING-001` |
| Prompt ID | `PHASE-3A-PROMPT-001` |

> **This is a prompt draft only.** It is the starting brief for a future,
> separately-authorized Phase 3A. **Do not execute Phase 3A in this planning
> phase.** Phase 3A may begin only when the user explicitly asks for it and
> separately authorizes it.

---

## How to use this document

When the user is ready to start Phase 3A, the prompt in the fenced block below
is the copy-paste starting brief. It encodes the baseline, goal, schema, state
model, step types, approval gates, allowed / forbidden steps, audit model, UI
model, smoke, tests, safety gates, commit / push discipline, and final report
format.

Before running it, confirm the Phase 3A entry gate (see
[phase-3-go-no-go.md](phase-3-go-no-go.md) §5).

---

## Prompt (copy-paste draft)

```text
Phase 3A — Dev-only Agent Workflow MVP

You are responsible for executing Phase 3A of the Hermes Dev WebUI. Read and
respect CLAUDE.md and the Phase 3 planning docs under docs/webui/.

================================================================
0. CURRENT BASELINE (verify before any change)
================================================================
- Branch = dev-huangruibang; tree clean (only .claude/ untracked).
- HERMES_HOME = /Users/huangruibang/Code/hermes-home-dev
- Never read from or write to ~/.hermes (production).
- Never run setup-hermes.sh. Never modify the global hermes command.
- Never stop / restart / replace / signal the Production Gateway.
- Production Gateway expected PID = 28428, process count = 1.
- Route governance baseline = OpenAPI 34 / runtime 34 / Tool GET 5 /
  Tool write HTTP route 0 / Tool dry-run route 1 / Tool execution route 1.
- Input HEAD = the Phase 3 planning commit (docs(webui): plan phase 3 scope).
- Phase 3A is separately authorized by this prompt.

================================================================
1. PHASE 3A GOAL
================================================================
Chain the Phase 2 capabilities (read-only tool, fake provider, sandbox write
preview, rollback reference, durable audit) into an operator-driven workflow
runner with a plan, manual step execution, and approval gates. Fully dev-only.
No autonomous execution. No real provider.

================================================================
2. SCOPE (ALLOWED)
================================================================
- Workflow definition schema (plan + ordered typed steps + per-step gate flag).
- Workflow planner + dry-run preview (no write).
- Step list + manual step execution (operator advances one step at a time).
- Approval gates between steps; reuse the Phase 2C-H1 confirmation-token model.
- Step types: read-only tool (reuse 2A), fake provider (reuse 2B), sandbox
  write PREVIEW (reuse 2C mode=write_preview), rollback reference (reuse 2C-H1).
- Audit linkage: every step links its dry-run / execute / provider / write /
  rollback audit event ids in the Phase 2D durable store.
- Workflow timeline UI: an additive "Workflow" section in /#/console.
- Workflow state stored under the dev HERMES_HOME only.
- Tests + an additive smoke profile.

================================================================
3. WORKFLOW SCHEMA
================================================================
A workflow is an ordered list of typed steps:
  workflow := { id, name, createdAt, status, steps[], cursor }
  step := {
    id,
    type: read_only | provider_fake | write_preview | rollback_reference,
    mode: <the existing /tools mode for that type>,
    inputs: <tool/mode inputs, JSON-native, sanitized>,
    gateRequired: bool,
    status: pending | running | approved | completed | failed | skipped,
    auditLinkIds: []
  }
status transitions: draft -> running <-> paused -> completed | failed.

================================================================
4. WORKFLOW STATE MODEL
================================================================
- Stored as JSON under the dev HERMES_HOME only.
- Validated on load; corrupted state fails safe (read-only, no execution).
- Never committed; gitignored like the other dev stores.

================================================================
5. STEP TYPES + APPROVAL GATES
================================================================
- read_only: reuses POST /tools/dry-run + /tools/execute (read-only mode).
- provider_fake: reuses mode=provider_roundtrip with the fake adapter only.
- write_preview: reuses mode=write_preview. PREVIEW ONLY — never writes.
- rollback_reference: links to a Phase 2C-H1 rollback manifest id.
- A step with gateRequired=true requires explicit operator approval before its
  successor advances. No step auto-executes a write.

================================================================
6. ALLOWED STEPS
================================================================
Only the four step types above. Each calls the EXISTING controlled-execution
surface via mode branches on POST /tools/dry-run and POST /tools/execute.

================================================================
7. FORBIDDEN STEPS
================================================================
- No real provider step (real provider stays blocked).
- No autonomous write step.
- No shell / process step.
- No database mutation step.
- No external-service write step.
- No dynamic plugin / code-loading step.
- No schedule / cron / background autonomous step.

================================================================
8. ROUTES
================================================================
Default: NO new HTTP route, NO Tool write HTTP route, NO Provider route.
Workflow reuses the existing mode-branched routes. If a read endpoint for
workflow state is truly needed, stop, document the requirement, and request
explicit separate authorization before adding any route.

================================================================
9. AUDIT MODEL
================================================================
- Every executed step links to its audit event ids in the Phase 2D durable
  store.
- No new audit writer is required. If a workflow breadcrumb event is needed,
  request explicit approval first.
- No secret / token / hash / raw arg / callable repr may leak via the workflow
  surface (inherit the Phase 2E-H1 no-leak closure).

================================================================
10. UI MODEL
================================================================
- Additive /#/console "Workflow" section: step timeline, current-step panel,
  advance / approve-gate controls, audit cross-navigation chips (reuse
  AuditIdLink + devConsoleNav.prefillAuditSearch).
- Inherit the Phase 2E-H1 accessibility baseline (vertical tablist / roving
  tabindex / non-color badges / focus-visible) and the no-leak closure.
- /#/ (the 3-column chat workbench) stays unchanged.

================================================================
11. SMOKE
================================================================
- Add a new additive smoke profile (e.g. phase3a_workflow_mvp) + spec, wired
  into the `all` target.
- All existing smoke profiles must keep passing (zero regression).
- PID 28428 unchanged; ports 5180 / 5181 free at the end.

================================================================
12. TESTS
================================================================
- Backend unit / contract: schema validation, planner, dry-run preview, step
  execution, approval-gate enforcement, audit linkage, route-governance
  no-new-route, no-leak.
- Frontend unit: Workflow section timeline, step list, approval gate,
  cross-navigation, no-leak.
- Type-check (vue-tsc), lint (eslint), build (vite) must pass.

================================================================
13. SAFETY GATES (run before commit and before push)
================================================================
- Route governance: scripts/run_tests.sh tests/test_dev_check_webui.py
  tests/test_dev_web_0c06_closure.py -q  -> 34/34/5/0/1/1, 0 failed.
- Docs/product preservation as applicable.
- memory-check + dev-check PASS (only .claude/ untracked WARN allowed).
- Boundary searches on the diff:
  * no runtime artifacts (audit-store / token / rollback manifest / *.jsonl /
    test-results / playwright-report / coverage / dist / node_modules).
  * no secrets (api_key / authorization / bearer / sk- / PEM / BEGIN PRIVATE KEY)
    except inside safety statements / negations / risk descriptions.
  * no dangerous exec (subprocess / os.system / eval / exec / shell=True /
    sqlite3 mutations / requests.post / httpx / urllib / aiohttp / curl)
    except inside forbidden-item / risk / boundary statements.
  * no production access (~/.hermes / production state.db) except inside
    forbidden-item / boundary statements.
- Production safety: PID 28428, count 1, dev gateway stopped, dashboard not
  started, 5180 / 5181 free. No ~/.hermes access. No production state.db access.

================================================================
14. COMMIT / PUSH
================================================================
- Commit with a conventional message, e.g.:
    feat(webui): add dev workflow mvp
- Confirm .claude/ is not staged. Confirm no runtime artifact is staged.
- Push only with: git push origin dev-huangruibang
- Never force push / rebase / merge / reset --hard / amend.
- If push fails, stop and report; do not force anything.

================================================================
15. FINAL REPORT
================================================================
Produce a Phase 3A closeout report under docs/webui/ mirroring the Phase 2E-H1
structure: scope, what changed, what did NOT change, route governance,
production safety, gates, residual risks (P2), conclusion. Confirm Phase 3A did
not enable a real provider, did not perform autonomous write, did not add shell
/ db / external write, did not roll out to production, did not access ~/.hermes
or production state.db, and left route governance and PID 28428 unchanged.
```

---

## Reminder

**This is a prompt draft only. Do not execute Phase 3A in this planning
phase.** Phase 3A begins only when the user explicitly asks for it and
separately authorizes it.

---

## Cross-References

- [Phase 3 planning](phase-3-planning.md)
- [Phase 3 scope freeze](phase-3-scope-freeze.md)
- [Phase 3 risk register](phase-3-risk-register.md)
- [Phase 3 GO / NO-GO](phase-3-go-no-go.md)
- [Phase 3A execution brief](phase-3a-execution-brief.md)
