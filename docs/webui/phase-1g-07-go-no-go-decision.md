# Phase 1G-07: Go / No-Go Decision — `RC-1G-07-001`

## Document Information

| Field | Value |
|-------|-------|
| Phase | 1G-07 |
| Title | Go / No-Go Decision — Release Candidate `RC-1G-07-001` |
| Status | Decision recorded |
| Date | 2026-06-14 |
| Branch | `dev-huangruibang` |
| Template | `docs/webui/phase-1g-06-go-no-go-template.md` |
| Scope | A filled go / no-go record for the Phase 1G-07 release candidate. No code change. |

---

## 1. Release Candidate ID

| Field | Value |
|-------|-------|
| Release candidate ID | `RC-1G-07-001` |
| Phase | 1G-07 Release Candidate Dry Run |
| Date | 2026-06-14 |

---

## 2. Branch

| Field | Value |
|-------|-------|
| Branch | `dev-huangruibang` |
| Local HEAD | `311221e0dd7c583dcd6c07f3bcef7f304bd669e0` |
| Remote HEAD | `311221e0dd7c583dcd6c07f3bcef7f304bd669e0` |
| ahead / behind | `0 / 0` |
| Tracked worktree | clean |
| Untracked | `.claude/` only |

---

## 3. HEAD

| Field | Value |
|-------|-------|
| Local HEAD | `311221e0dd7c583dcd6c07f3bcef7f304bd669e0` |
| Short HEAD | `311221e0d` |
| Merge base with remote | `311221e0dd7c583dcd6c07f3bcef7f304bd669e0` |

---

## 4. Route Governance

| Metric | Observed | Expected |
|--------|----------|----------|
| OpenAPI paths | 34 | 34 |
| Runtime routes | 34 | 34 |
| Tool GET routes | 5 | 5 |
| Tool write routes | 0 | 0 |
| Tool dry-run routes | 1 | 1 |
| Tool execution routes | 1 | 1 |
| `STATIC_ALLOWLIST` | `frozenset({"clarify"})` | `frozenset({"clarify"})` |

**No deviation.** Route governance matches the sealed baseline exactly.

---

## 5. Smoke Result

| Profile | Command | Result | Notes |
|---------|---------|--------|-------|
| A — blocked | `./scripts/run-dev-webui-execute-audit-smoke.sh blocked` | 6 passed, 1 skipped, **0 failed** | expect 6 passed, 1 skipped, 0 failed — matched |
| B — completed | `./scripts/run-dev-webui-execute-audit-smoke.sh completed` | 7 passed, **0 failed** | expect 7 passed, 0 failed — matched |
| C — fully disabled (optional) | manual | not run | optional safety supplement; `blocked_by_kill_switch` not asserted this RC |

**No smoke failure.** Both named profiles passed.

---

## 6. Backend Result

| Check | Result |
|-------|--------|
| Route governance tests | 124 passed, 0 failed |
| Related backend regression (19 files) | 1471 passed, 0 failed |
| `compileall` (14 dev_web modules) | pass (exit 0) |
| `py_compile toolsets.py` | pass |
| `ruff check` (14 files) | all checks passed |

**No backend failure.**

---

## 7. Frontend Result

| Check | Result |
|-------|--------|
| `pnpm type-check` | pass |
| `pnpm lint` | 0 errors / 0 warnings |
| `pnpm test` | 674 passed (31 files), 0 failed |
| `pnpm build` | pass (1862 modules) |

**No frontend failure.**

---

## 8. Production Safety

| Check | Result |
|-------|--------|
| Production Gateway PID before | `69355` |
| Production Gateway PID after | `69355` |
| Production gateway process count | exactly 1 |
| Dev Gateway | stopped |
| Ports `5180` / `5181` | free |
| Production `~/.hermes` accessed | no (no `ls` / `stat` / `find` / `cat` / `sqlite3` / `du` / mtime) |
| Production `state.db` accessed | no |

**No production impact.**

---

## 9. Security Boundary

| Check | Result |
|-------|--------|
| `STATIC_ALLOWLIST` changed | no |
| Allowlist expanded beyond clarify | no |
| Raw token exposed | no |
| Full tokenHash exposed | no |
| Raw arguments exposed | no |
| Secrets exposed | no |
| Callable / function repr exposed | no |
| `~/.hermes` accessed | no |
| Production `state.db` accessed | no |
| Provider Schema sent | no |
| Provider API called | no |
| Non-clarify execution | no |
| Tool write route added | no |
| New backend route added | no |
| Second execution route added | no |
| Provider route added | no |
| Audit JSONL committed | no |
| `.claude/` committed | no |

---

## 10. P0 / P1 / P2

| Severity | Count | Items |
|----------|-------|-------|
| P0 | 0 | — |
| P1 | 0 | — |
| P2 | 8 | Carried over from the Phase 1G-05 risk register (stale dormant `auditWritten=false` assumption; offset-based audit pagination; multi-file JSONL rotation; JSONL race handling; non-clarify disabled by design; Provider permanent non-goal; frontend visual polish optional; large-scale audit search / index). All non-blocking. |

---

## 11. Decision

| Field | Value |
|-------|-------|
| Decision | **GO** |
| Rationale | No P0, no P1. All required gates pass (route governance, backend regression 1471 passed / 0 failed, compile / ruff, frontend type-check / lint / 674 unit / build, smoke A 6 passed / 1 skipped / 0 failed, smoke B 7 passed / 0 failed, memory-check PASS, dev-check WARN only for `.claude/`). Route governance unchanged at 34 / 34 / 5 / 0 / 1 / 1. `STATIC_ALLOWLIST = frozenset({"clarify"})`. No Provider Schema / API, no non-clarify execution, no Tool write / new / Provider route. Production Gateway PID `69355` unchanged. Ports `5180` / `5181` free. No forbidden file touched; no audit JSONL / `.claude/` / secret / token / tokenHash / raw-arguments exposure. |
| Date | 2026-06-14 |

> **Decision: GO**
> Current `dev-huangruibang` is eligible to enter Pilot acceptance.

---

## 12. Approver

| Field | Value |
|-------|-------|
| Approver | Dev Agent (Phase 1G-07 RC dry run) |
| Role | Release-candidate validation (local, dry run) |
| Approval date | 2026-06-14 |

> A real Pilot / production go decision requires a human approver. This RC dry
> run establishes eligibility only; it is not a production release authorization.

---

## 13. Rollback Note

- No automatic rollback during this release task.
- If rollback is needed, **stop and request user confirmation** first.
- Use a new `git revert` commit — never `git reset --hard`, never force push,
  never production state mutation.
- Preserve evidence and logs before any controlled revert.
- See `docs/webui/phase-1g-05-ops-and-rollback-runbook.md` for the full runbook.

---

## 14. Next Action

| Field | Value |
|-------|-------|
| Push? | **no** (Phase 1G-07 = local commit only, no push) |
| Start next phase? | **no** (Phase 1G-08 explicitly not started) |
| Follow-on | Pilot execution (optional, pending explicit approval) |

---

## 15. Emergency Stop Conditions (carry in every release)

Stop immediately and report if any of these occur:

1. `STATIC_ALLOWLIST` is not exactly `frozenset({"clarify"})`.
2. A non-`clarify` tool executes or becomes allowlisted.
3. `providerSchemaSent=true` or `providerApiCalled=true` appears anywhere.
4. The raw confirmation token appears in a response, the DOM, a log, the
   console, `localStorage`, `sessionStorage`, or an audit event.
5. The full token hash is surfaced.
6. Raw arguments appear in the audit viewer.
7. A secret / API key / credential is logged or committed.
8. The production `~/.hermes` or production `state.db` is accessed or modified.
9. Production Gateway PID `69355` changes.
10. A Tool write route, a second execution route, or a Provider route appears.
11. Audit JSONL or `.claude/` is staged or committed.
12. Any force push, rebase, or `git reset --hard` is attempted.

None of these occurred during `RC-1G-07-001`.

---

## 16. Phase 1G-08 Addendum — Pilot Acceptance Prepared

Phase 1G-08 (Pilot Acceptance Preparation) prepared Pilot `PILOT-1G-08-001`
against this GO decision (`RC-1G-07-001`).

- The GO conclusion is **unchanged**. `RC-1G-07-001` remains the GO RC.
- Phase 1G-08 added no product capability and no route governance change; it
  produced the Pilot acceptance pack, operator / participant guides, record /
  defect templates, and PASS / NO-GO / PAUSED exit criteria.
- Pilot execution is **separately approved**; Phase 1G-09 is explicitly **not
  started**.
- See `docs/webui/phase-1g-08-pilot-acceptance-preparation.md` and
  `docs/webui/phase-1g-08-pilot-exit-criteria.md`.

---

*Phase 1G-07 Go / No-Go Decision — `RC-1G-07-001`: **GO**. Current
`dev-huangruibang` is eligible to enter Pilot acceptance. Phase 1G-04 remains
sealed; Phase 1G-05 remains the pushed readiness baseline; Phase 1G-06 remains
the pushed release rehearsal baseline. Production Gateway PID `69355` is
unchanged.*
