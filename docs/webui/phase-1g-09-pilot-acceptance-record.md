# Phase 1G-09: Pilot Acceptance Record — `PILOT-EXEC-1G-09-001`

## Document Information

| Field | Value |
|-------|-------|
| Phase | 1G-09 |
| Title | Pilot Acceptance Record |
| Status | Filled (Pilot executed) |
| Date | 2026-06-14 |
| Pilot Acceptance ID | `PILOT-1G-08-001` |
| Pilot Execution ID | `PILOT-EXEC-1G-09-001` |
| Related Release Candidate | `RC-1G-07-001` (Phase 1G-07, **GO**) |
| Baseline HEAD | `9812c069ee4370babdb8599efd67ac4cb12ce148` |
| Template | `docs/webui/phase-1g-08-pilot-acceptance-record-template.md` |
| Scope | A filled record of one Pilot run. No code change. |

---

## 1. Pilot Header

```text
Pilot ID:            PILOT-1G-08-001
Pilot Execution ID:  PILOT-EXEC-1G-09-001
RC ID:               RC-1G-07-001
Date:                2026-06-14
Operator:            Dev Agent (Phase 1G-09 pilot acceptance execution)
Observer:            none (single-operator execution)
Branch:              dev-huangruibang
Baseline HEAD:       9812c069ee4370babdb8599efd67ac4cb12ce148
Execution HEAD:      9812c069ee4370babdb8599efd67ac4cb12ce148
Environment:         HERMES_HOME=/Users/huangruibang/Code/hermes-home-dev ;
                     Dev API 127.0.0.1:5181 ; WebUI 127.0.0.1:5180
Route governance:    OpenAPI 34 / runtime 34 / Tool GET 5 /
                     Tool write 0 / dry-run 1 / execution 1
STATIC_ALLOWLIST:    frozenset({"clarify"})
Production PID:      before=69355 ; after=69355
```

---

## 2. Scenario Records

> Status is one of: PASS / FAIL / BLOCKED / SKIPPED. All 15 scenarios (A–O)
> executed under the two named server-gate profiles via the committed harness.

### Scenario A — WebUI loads

```text
Scenario ID:    A
Scenario name:  WebUI loads
Status:         PASS
Preconditions:  Dev API on 127.0.0.1:5181; WebUI on 127.0.0.1:5180;
                Production Gateway PID 69355.
Actual steps:   Harness started both services (PIDs 54855/54856 profile A,
                55053/55054 profile B); Dev API health reachable; WebUI ready.
Expected:       Three-column workbench renders; default theme (Obsidian) loads;
                no missing-API console error.
Actual result:  WebUI ready on 127.0.0.1:5180; Dev API /api/dev/v1/status
                reachable; UI render + dry-run UI tests passed both profiles.
Evidence:       EV-1G09-014 (smoke harness "WebUI: ready"); EV-1G09-007/008
                (UI Execute + Audit sub-tab render; UI dry-run safe decision).
Defect ID:      none
Severity:       n/a
Notes:          Services isolated to 127.0.0.1; harness self-cleaned.
```

### Scenario B — Tools panel visible

```text
Scenario ID:    B
Scenario name:  Tools panel visible
Status:         PASS
Preconditions:  Scenario A passed; Dev API up.
Actual steps:   Smoke spec opened the Tools panel and asserted the dry-run /
                Execute sub-tab and the Audit viewer sub-tab are reachable
                (test: "Execute and Audit sub-tabs render in the Tools panel").
Expected:       Tools panel renders; Execute + Audit sub-tabs present.
Actual result:  Both sub-tabs render in both profiles (profile A: passed;
                profile B: passed).
Evidence:       EV-1G09-007 / EV-1G09-008.
Defect ID:      none
Severity:       n/a
Notes:          —
```

### Scenario C — Tool schema / policy read-only inspection

```text
Scenario ID:    C
Scenario name:  Tool schema / policy read-only inspection
Status:         PASS
Preconditions:  Scenario B passed.
Actual steps:   dev-check static policy line; route governance tests;
                tool policy / schema preview API regression.
Expected:       Canonical tool inventory and risk tiers display; clarify is the
                only allowlisted tool; no Provider Schema sent.
Actual result:  dev-check "Static allowlist: clarify"; "Provider tool schema:
                not sent"; Tool GET 5; policy_api + schema_preview_api tests
                passed (0 failed).
Evidence:       EV-1G09-001 (route governance), EV-1G09-002 (backend regression),
                EV-1G09-013 (dev-check).
Defect ID:      none
Severity:       n/a
Notes:          —
```

### Scenario D — clarify dry-run

```text
Scenario ID:    D
Scenario name:  clarify dry-run
Status:         PASS
Preconditions:  Scenario C passed.
Actual steps:   Smoke spec "UI dry-run surfaces a safe decision without the raw
                token" (both profiles); backend dry_run / dry_run_api /
                dry_run_audit tests.
Expected:       Dry-run returns a safe decision, risk assessment, short digest,
                and confirmationTokenId; raw token absent.
Actual result:  UI dry-run surfaces a safe decision in both profiles; raw token
                absent; dry_run chain tests passed (0 failed).
Evidence:       EV-1G09-007 / EV-1G09-008; EV-1G09-002.
Defect ID:      none
Severity:       n/a
Notes:          raw token never observed in response, DOM, console, or storage.
```

### Scenario E — blocked profile (`blocked_tool_handler_call_not_enabled`)

```text
Scenario ID:    E
Scenario name:  blocked_tool_handler_call_not_enabled profile
Status:         PASS
Gate profile:   blocked (HERMES_TOOL_EXECUTION_ENABLED=true,
                HERMES_AGENT_TOOLS_ENABLED=true, handler-call gate unset)
Actual steps:   ./scripts/run-dev-webui-execute-audit-smoke.sh all → profile A.
Expected:       Execute returns blocked_tool_handler_call_not_enabled;
                toolHandlerCalled=false; executionCompleted=false; no
                post-execution audit.
Actual result:  decision=blocked_tool_handler_call_not_enabled;
                toolHandlerCalled=false; executionCompleted=false; all provider /
                external flags false; 6 passed / 1 skipped / 0 failed.
Evidence:       EV-1G09-007 (Profile A 6 passed / 1 skipped / 0 failed).
Defect ID:      none
Severity:       n/a
Notes:          the single skip is the post-execution-audit visibility test,
                correctly skipped (no execution → no post-audit) under the
                blocked profile.
```

### Scenario F — completed profile (`clarify_execution_completed`)

```text
Scenario ID:    F
Scenario name:  clarify_execution_completed profile
Status:         PASS
Gate profile:   completed (all three gates =true)
Actual steps:   ./scripts/run-dev-webui-execute-audit-smoke.sh all → profile B.
Expected:       Execute returns clarify_execution_completed; canonicalName=clarify;
                handlerCallId (thc_…); postExecutionAuditId (pexa_…); all
                provider / external flags false.
Actual result:  decision=clarify_execution_completed; canonicalName=clarify;
                handlerCallId present (thc_); postExecutionAuditId present
                (pexa_); provider / external flags false; 7 passed / 0 failed.
Evidence:       EV-1G09-008 (Profile B 7 passed / 0 failed).
Defect ID:      none
Severity:       n/a
Notes:          —
```

### Scenario G — audit viewer: dry-run event

```text
Scenario ID:    G
Scenario name:  audit viewer dry-run event
Status:         PASS
Preconditions:  Scenario D run.
Actual steps:   Smoke spec "GET audit-events returns safe items for each kind"
                (both profiles); dry_run_audit backend tests.
Expected:       Dry-run audit events render with safe per-event summaries;
                malformed lines skipped safely; empty state renders.
Actual result:  audit-events API returns safe items for each kind in both
                profiles; read-only (POST rejected); invalid kind → 400; no raw
                arguments.
Evidence:       EV-1G09-007 / EV-1G09-008; EV-1G09-002.
Defect ID:      none
Severity:       n/a
Notes:          —
```

### Scenario H — audit viewer: pre-execution event

```text
Scenario ID:    H
Scenario name:  audit viewer pre-execution event
Status:         PASS
Preconditions:  Scenario E or F run.
Actual steps:   audit-events API read-only tests (both profiles);
                pre_execution_audit backend tests.
Expected:       Pre-execution audit events render safely with correlation IDs.
Actual result:  pre-execution events render safely; no token / tokenHash / raw
                args / callable surfaced; pre_execution_audit tests passed.
Evidence:       EV-1G09-002; EV-1G09-007 / EV-1G09-008.
Defect ID:      none
Severity:       n/a
Notes:          —
```

### Scenario I — audit viewer: post-execution event

```text
Scenario ID:    I
Scenario name:  audit viewer post-execution event
Status:         PASS
Preconditions:  Scenario F completed.
Actual steps:   Profile B smoke "post-execution audit is visible in the audit
                viewer API"; post_execution_audit backend tests.
Expected:       Post-execution audit event renders; provider / external flags
                false; no raw token / full tokenHash / raw arguments / provider
                payload.
Actual result:  post-execution audit visible (profile B); provider / external
                flags false; no payload / token / tokenHash / raw args;
                post_execution_audit tests passed.
Evidence:       EV-1G09-008 (profile B post-audit visibility test passed);
                EV-1G09-002.
Defect ID:      none
Severity:       n/a
Notes:          postExecutionAuditId (pexa_) visible under auditKind=post_execution.
```

### Scenario J — `providerSchemaSent=false`

```text
Scenario ID:    J
Scenario name:  providerSchemaSent=false
Status:         PASS
Preconditions:  Any execute path (E or F).
Actual steps:   Inspect execute response / post-execution audit (both profiles);
                dev-check "Provider tool schema: not sent".
Expected:       providerSchemaSent=false everywhere.
Actual result:  providerSchemaSent=false on both profiles; dev-check confirms
                "Provider tool schema: not sent".
Evidence:       EV-1G09-007 / EV-1G09-008; EV-1G09-013.
Defect ID:      none
Severity:       n/a
Notes:          —
```

### Scenario K — `providerApiCalled=false`

```text
Scenario ID:    K
Scenario name:  providerApiCalled=false
Status:         PASS
Preconditions:  Any execute path (E or F).
Actual steps:   Inspect execute response / post-execution audit (both profiles);
                all Provider keys unset in the harness environment.
Expected:       providerApiCalled=false everywhere.
Actual result:  providerApiCalled=false on both profiles; no Provider API call
                observed.
Evidence:       EV-1G09-007 / EV-1G09-008; EV-1G09-014 (env scrub).
Defect ID:      none
Severity:       n/a
Notes:          —
```

### Scenario L — no non-clarify execution

```text
Scenario ID:    L
Scenario name:  no non-clarify execution
Status:         PASS
Preconditions:  Dev API up; explicit gate enabled.
Actual steps:   dev-check "Static allowlist: clarify"; route governance Tool
                write 0 / execution 1; execute / dispatch / handler_call backend
                tests assert non-clarify rejection.
Expected:       Non-clarify blocked at the allowlist gate (blocked_* decision).
Actual result:  STATIC_ALLOWLIST={clarify}; non-clarify rejected; no handler
                call, no execution for non-clarify tools.
Evidence:       EV-1G09-001 / EV-1G09-002 / EV-1G09-013.
Defect ID:      none
Severity:       n/a
Notes:          —
```

### Scenario M — route governance unchanged

```text
Scenario ID:    M
Scenario name:  route governance unchanged
Status:         PASS
Preconditions:  Dev API up.
Actual steps:   ./scripts/run_tests.sh tests/test_dev_check_webui.py
                tests/test_dev_web_0c06_closure.py; dev-check.
Expected:       OpenAPI 34 / runtime 34 / Tool GET 5 / write 0 / dry-run 1 /
                execution 1; STATIC_ALLOWLIST={"clarify"}.
Actual result:  34 / 34 / 5 / 0 / 1 / 1; STATIC_ALLOWLIST={"clarify"};
                route governance tests 124 passed / 0 failed.
Evidence:       EV-1G09-001; EV-1G09-013.
Defect ID:      none
Severity:       n/a
Notes:          —
```

### Scenario N — Production Gateway PID unaffected

```text
Scenario ID:    N
Scenario name:  Production Gateway PID unaffected
Status:         PASS
Preconditions:  Full Pilot run complete; servers torn down.
Actual steps:   ps aux | grep '[h]ermes_cli.main gateway run';
                ./scripts/run-dev-hermes.sh gateway-dev status.
Expected:       Production Gateway PID still 69355; Dev Gateway stopped; ports
                5180 / 5181 free; no production access.
Actual result:  PID 69355 before and after; exactly one production gateway
                process; Dev Gateway stopped; no ~/.hermes / state.db access.
Evidence:       EV-1G09-011 (PID before/after); EV-1G09-012 (final ports).
Defect ID:      none
Severity:       n/a
Notes:          —
```

### Scenario O — final ports free

```text
Scenario ID:    O
Scenario name:  final ports free
Status:         PASS
Preconditions:  Servers torn down.
Actual steps:   lsof -nP -iTCP:5180 -sTCP:LISTEN; lsof -nP -iTCP:5181 -sTCP:LISTEN.
Expected:       Both ports free.
Actual result:  5180 free; 5181 free (empty lsof output for each).
Evidence:       EV-1G09-012.
Defect ID:      none
Severity:       n/a
Notes:          —
```

### Scenario run matrix

| Scenario | Name | Status | Profile A | Profile B |
|----------|------|--------|-----------|-----------|
| A | WebUI loads | PASS | ✔ | ✔ |
| B | Tools panel visible | PASS | ✔ | ✔ |
| C | Tool schema / policy read-only | PASS | ✔ | ✔ |
| D | clarify dry-run | PASS | ✔ | ✔ |
| E | blocked profile | PASS | ✔ | — |
| F | completed profile | PASS | — | ✔ |
| G | audit viewer dry-run event | PASS | ✔ | ✔ |
| H | audit viewer pre-execution event | PASS | ✔ | ✔ |
| I | audit viewer post-execution event | PASS | — | ✔ |
| J | providerSchemaSent=false | PASS | ✔ | ✔ |
| K | providerApiCalled=false | PASS | ✔ | ✔ |
| L | no non-clarify execution | PASS | ✔ | ✔ |
| M | route governance unchanged | PASS | ✔ | ✔ |
| N | Production Gateway PID unaffected | PASS | ✔ | ✔ |
| O | final ports free | PASS | ✔ | ✔ |

---

## 3. Evidence Index

All evidence is recorded in `docs/webui/phase-1g-09-pilot-evidence-index.md`.
Per-scenario evidence references point to the Evidence IDs (EV-1G09-###) there.

No evidence entry contains a secret, an API key, the raw confirmation token, the
full token hash, or raw arguments.

---

## 4. Defects Index

```text
Defects:
  - none introduced by Phase 1G-09.
  - Carried-over P2 (8): see docs/webui/phase-1g-09-pilot-defect-feedback-log.md
    and docs/webui/phase-1g-05-risk-register.md.
```

---

## 5. Decision

```text
Pilot Result:        PASS (operator-executed; all technical PASS criteria met)
Reason:              No P0, no unresolved P1. All 15 required scenarios (A–O)
                    passed under the two named server-gate profiles. Route
                    governance unchanged (34 / 34 / 5 / 0 / 1 / 1);
                    STATIC_ALLOWLIST = frozenset({"clarify"}). No Provider
                    Schema / API, no non-clarify execution, no Tool write route.
                    Production Gateway PID 69355 unchanged; ports 5180 / 5181
                    free; no ~/.hermes / production state.db access; no
                    secret / token / tokenHash / raw-arguments exposure.
Required follow-up:  Human approver sign-off for a final Pilot-accepted PASS;
                    none otherwise.
Next phase:          Pilot execution complete; post-Pilot closeout / final
                    release decision preparation (separately approved).
                    Phase 1G-10 not started.
```

---

## 6. Sign-off

```text
Operator sign-off:   Dev Agent (Phase 1G-09 pilot acceptance execution) /
                    2026-06-14
Observer sign-off:   none (single-operator execution)
Approver sign-off:   pending human sign-off
```

> A real Pilot PASS requires a human approver sign-off. A PASS recorded without
> an approver is a recommendation only, not a release authorization.

---

## 7. Cross-References

- Pilot acceptance pack: `docs/webui/phase-1g-08-pilot-acceptance-pack.md`.
- Acceptance record template:
  `docs/webui/phase-1g-08-pilot-acceptance-record-template.md`.
- Defect / feedback template:
  `docs/webui/phase-1g-08-pilot-defect-feedback-template.md`.
- Exit criteria: `docs/webui/phase-1g-08-pilot-exit-criteria.md`.
- Phase 1G-09 execution: `docs/webui/phase-1g-09-pilot-acceptance-execution.md`.
- Phase 1G-09 evidence index:
  `docs/webui/phase-1g-09-pilot-evidence-index.md`.
- Phase 1G-09 defect / feedback log:
  `docs/webui/phase-1g-09-pilot-defect-feedback-log.md`.
- Phase 1G-09 final decision:
  `docs/webui/phase-1g-09-pilot-final-decision.md`.

---

*Phase 1G-09 Pilot Acceptance Record — `PILOT-EXEC-1G-09-001` against Pilot
`PILOT-1G-08-001` and RC `RC-1G-07-001` (GO). 15 scenarios (A–O) executed; all
PASS. Phase 1G-04 remains sealed; Production Gateway PID `69355` is unchanged.*
