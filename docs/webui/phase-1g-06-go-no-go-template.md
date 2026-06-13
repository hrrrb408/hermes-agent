# Phase 1G-06: Go / No-Go Decision Template

## Document Information

| Field | Value |
|-------|-------|
| Phase | 1G-06 |
| Title | Go / No-Go Decision Template (reusable) |
| Status | Template (copy per release) |
| Date | 2026-06-14 |
| Branch | `dev-huangruibang` |
| Scope | A copy-paste go / no-go record for any Dev WebUI release candidate. No code change. |

---

## 1. How to Use

Copy this file to a dated release record (e.g.
`docs/webui/release-<id>-go-no-go.md`) and fill in every field. A field may not
be left blank — if a check was not run, mark it `NOT RUN` with a reason. The
decision is **NO-GO** until every GO criterion is met.

---

## 2. Release Candidate ID

| Field | Value |
|-------|-------|
| Release candidate ID | `<e.g. dev-webui-1g-rehearsal-01>` |
| Phase | `<e.g. 1G-06 rehearsal>` |
| Date | `<YYYY-MM-DD>` |

---

## 3. Branch

| Field | Value |
|-------|-------|
| Branch | `dev-huangruibang` |
| Local HEAD | `<sha>` |
| Remote HEAD | `<sha>` |
| ahead / behind | `<n> / <n>` |
| Tracked worktree | clean / dirty (list) |
| Untracked | `.claude/` only / list |

---

## 4. HEAD

| Field | Value |
|-------|-------|
| Local HEAD | `<full sha>` |
| Short HEAD | `<short sha>` |
| Merge base with remote | `<sha>` |

---

## 5. Route Governance

| Metric | Observed | Expected |
|--------|----------|----------|
| OpenAPI paths |  | 34 |
| Runtime routes |  | 34 |
| Tool GET routes |  | 5 |
| Tool write routes |  | 0 |
| Tool dry-run routes |  | 1 |
| Tool execution routes |  | 1 |
| `STATIC_ALLOWLIST` |  | `frozenset({"clarify"})` |

Any deviation from the expected column → **NO-GO** (P0 if allowlist / write /
Provider route; P1 otherwise).

---

## 6. Smoke Result

| Profile | Command | Result | Notes |
|---------|---------|--------|-------|
| A — blocked | `./scripts/run-dev-webui-execute-audit-smoke.sh blocked` | <passed/skipped/failed> | expect 6 passed, 1 skipped, 0 failed |
| B — completed | `./scripts/run-dev-webui-execute-audit-smoke.sh completed` | <passed/failed> | expect 7 passed, 0 failed |
| C — fully disabled (optional) | manual | <decision> | expect `blocked_by_kill_switch` |

Any smoke failure → **NO-GO** (P1, or P0 if a provider flag is `true`).

---

## 7. Backend Result

| Check | Result |
|-------|--------|
| Route governance tests | 0 failed |
| Related backend regression (18 files) | 0 failed |
| `compileall` | pass |
| `py_compile toolsets.py` | pass |
| `ruff check` | all checks passed |

Any backend failure → **NO-GO** (P1).

---

## 8. Frontend Result

| Check | Result |
|-------|--------|
| `pnpm type-check` | pass |
| `pnpm lint` | 0 errors / 0 warnings |
| `pnpm test` | 0 failed |
| `pnpm build` | pass |

Any frontend failure → **NO-GO** (P1; build failure is P1).

---

## 9. Production Safety

| Check | Result |
|-------|--------|
| Production Gateway PID before | `69355` |
| Production Gateway PID after | `69355` |
| Production gateway process count | exactly 1 |
| Dev Gateway | stopped |
| Ports `5180` / `5181` | free |
| Production `~/.hermes` accessed | no |
| Production `state.db` accessed | no |

Any production impact → **NO-GO** (P0).

---

## 10. P0 / P1 / P2

| Severity | Count | Items |
|----------|-------|-------|
| P0 |  |  |
| P1 |  |  |
| P2 |  | (carry over from the risk register) |

---

## 11. Decision

| Field | Value |
|-------|-------|
| Decision | **GO** / **NO-GO** |
| Rationale |  |
| Date |  |

**GO requires:** items 5–9 all pass, no P0, no P1, route governance exactly
34 / 34 / 5 / 0 / 1 / 1, `STATIC_ALLOWLIST = frozenset({"clarify"})`, no Provider
Schema / API, no non-clarify execution, Production Gateway PID `69355`
unchanged, no audit JSONL / `.claude/` commit, no secret / raw-token /
raw-arguments exposure.

**NO-GO on:** any P0, any P1, backend regression failure, frontend build
failure, smoke failure, route governance change, allowlist change, production
PID change, or any provider-boundary violation.

---

## 12. Approver

| Field | Value |
|-------|-------|
| Approver |  |
| Role |  |
| Approval date |  |

---

## 13. Rollback Note

- No automatic rollback during a release task.
- If rollback is needed, **stop and request user confirmation** first.
- Use a new `git revert` commit — never `git reset --hard`, never force push,
  never production state mutation.
- Preserve evidence and logs before any controlled revert.
- See `docs/webui/phase-1g-05-ops-and-rollback-runbook.md` for the full runbook.

---

## 14. Next Action

| Field | Value |
|-------|-------|
| Push? | yes / no (Phase 1G-06 = local only, no push) |
| Start next phase? | yes / no (Phase 1G-07 not started by 1G-06) |
| Follow-on |  |

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

---

*Phase 1G-06 Go / No-Go Template — copy per release; GO only when every
criterion is met and every field is filled. Production Gateway PID `69355`
must remain unchanged.*
