# Phase 1G-08: Pilot Acceptance Record Template

> Copy this file to a new file (for example
> `docs/webui/phase-1g-08-pilot-acceptance-record-PILOT-1G-08-001.md`) and fill
> it in during Pilot execution. Phase 1G-08 ships the **template** only; the
> filled record is produced when the Pilot is executed.

## Document Information

| Field | Value |
|-------|-------|
| Phase | 1G-08 |
| Title | Pilot Acceptance Record (Template) |
| Status | Template (awaiting Pilot execution) |
| Date | _(fill on execution)_ |
| Pilot Acceptance ID | `PILOT-1G-08-001` |
| Related Release Candidate | `RC-1G-07-001` (Phase 1G-07, **GO**) |
| Baseline HEAD (target) | `6f9176953cec7676d668aa3b4b7a654a374834de` |
| Scope | A copy-fill record of one Pilot run. No code change. |

---

## 1. Pilot Header

```text
Pilot ID:            PILOT-1G-08-001
RC ID:               RC-1G-07-001
Date:                <YYYY-MM-DD>
Operator:            <name / role>
Observer:            <name / role, or "none">
Branch:              dev-huangruibang
HEAD:                <fill from `git rev-parse HEAD`>
Environment:         HERMES_HOME=/Users/huangruibang/Code/hermes-home-dev ;
                     Dev API 127.0.0.1:5181 ; WebUI 127.0.0.1:5180
Route governance:    OpenAPI 34 / runtime 34 / Tool GET 5 /
                     Tool write 0 / dry-run 1 / execution 1
STATIC_ALLOWLIST:    frozenset({"clarify"})
Production PID:      before=69355 ; after=<fill>
```

---

## 2. Scenario Records

> One block per scenario. Status is one of: PASS / FAIL / BLOCKED / SKIPPED.

### Scenario A — WebUI loads

```text
Scenario ID:    A
Scenario name:  WebUI loads
Status:         <PASS / FAIL / BLOCKED / SKIPPED>
Actual result:  <one line>
Evidence:       <text summary / screenshot ref>
Defect ID:      <none / DEF-###>
Severity:       <P1 if fail / n/a>
Notes:          <optional>
```

### Scenario B — Tools panel visible

```text
Scenario ID:    B
Scenario name:  Tools panel visible
Status:         <PASS / FAIL / BLOCKED / SKIPPED>
Actual result:  <one line>
Evidence:       <text summary>
Defect ID:      <none / DEF-###>
Severity:       <P1 if fail / n/a>
Notes:          <optional>
```

### Scenario C — Tool schema / policy read-only inspection

```text
Scenario ID:    C
Scenario name:  Tool schema / policy read-only inspection
Status:         <PASS / FAIL / BLOCKED / SKIPPED>
Actual result:  <allowlist shown, Provider Schema absent, etc.>
Evidence:       <text summary>
Defect ID:      <none / DEF-###>
Severity:       <P0 allowlist/Provider / P1 otherwise / n/a>
Notes:          <optional>
```

### Scenario D — clarify dry-run

```text
Scenario ID:    D
Scenario name:  clarify dry-run
Status:         <PASS / FAIL / BLOCKED / SKIPPED>
Actual result:  <decision + confirmationTokenId; raw token absent>
Evidence:       <text summary; confirm raw token not present>
Defect ID:      <none / DEF-###>
Severity:       <P0 token leak / P1 otherwise / n/a>
Notes:          <optional>
```

### Scenario E — blocked profile (`blocked_tool_handler_call_not_enabled`)

```text
Scenario ID:    E
Scenario name:  blocked_tool_handler_call_not_enabled profile
Status:         <PASS / FAIL / BLOCKED / SKIPPED>
Gate profile:   blocked (HERMES_TOOL_EXECUTION_ENABLED=true,
                HERMES_AGENT_TOOLS_ENABLED=true, handler-call gate unset)
Actual result:  decision=blocked_tool_handler_call_not_enabled ;
                toolHandlerCalled=false ; executionCompleted=false
Evidence:       <providerSchemaSent/providerApiCalled/externalSideEffects = false>
Defect ID:      <none / DEF-###>
Severity:       <P0 if execution completes / n/a>
Notes:          <optional>
```

### Scenario F — completed profile (`clarify_execution_completed`)

```text
Scenario ID:    F
Scenario name:  clarify_execution_completed profile
Status:         <PASS / FAIL / BLOCKED / SKIPPED>
Gate profile:   completed (all three gates =true)
Actual result:  decision=clarify_execution_completed ; canonicalName=clarify ;
                handlerCallId=thc_… ; postExecutionAuditId=pexa_…
Evidence:       <providerSchemaSent/providerApiCalled/externalSideEffects = false>
Defect ID:      <none / DEF-###>
Severity:       <P0 Provider/non-clarify / P1 otherwise / n/a>
Notes:          <optional>
```

### Scenario G — audit viewer: dry-run event

```text
Scenario ID:    G
Scenario name:  audit viewer dry-run event
Status:         <PASS / FAIL / BLOCKED / SKIPPED>
Actual result:  <dry-run events render; empty state renders>
Evidence:       <no raw arguments>
Defect ID:      <none / DEF-###>
Severity:       <P0 raw args / P1 otherwise / n/a>
Notes:          <optional>
```

### Scenario H — audit viewer: pre-execution event

```text
Scenario ID:    H
Scenario name:  audit viewer pre-execution event
Status:         <PASS / FAIL / BLOCKED / SKIPPED>
Actual result:  <pre-execution events render safely>
Evidence:       <no token / tokenHash / raw args / callable>
Defect ID:      <none / DEF-###>
Severity:       <P0 leak / P1 otherwise / n/a>
Notes:          <optional>
```

### Scenario I — audit viewer: post-execution event

```text
Scenario ID:    I
Scenario name:  audit viewer post-execution event
Status:         <PASS / FAIL / BLOCKED / SKIPPED>
Actual result:  <post-execution event renders; provider/external flags false>
Evidence:       <no token / tokenHash / raw args / provider payload>
Defect ID:      <none / DEF-###>
Severity:       <P0 Provider/leak / P1 otherwise / n/a>
Notes:          <optional>
```

### Scenario J — `providerSchemaSent=false`

```text
Scenario ID:    J
Scenario name:  providerSchemaSent=false
Status:         <PASS / FAIL / BLOCKED / SKIPPED>
Actual result:  providerSchemaSent=false on every path
Evidence:       <flag value from response + audit>
Defect ID:      <none / DEF-###>
Severity:       <P0 if true / n/a>
Notes:          <optional>
```

### Scenario K — `providerApiCalled=false`

```text
Scenario ID:    K
Scenario name:  providerApiCalled=false
Status:         <PASS / FAIL / BLOCKED / SKIPPED>
Actual result:  providerApiCalled=false on every path
Evidence:       <flag value from response + audit>
Defect ID:      <none / DEF-###>
Severity:       <P0 if true / n/a>
Notes:          <optional>
```

### Scenario L — no non-clarify execution

```text
Scenario ID:    L
Scenario name:  no non-clarify execution
Status:         <PASS / FAIL / BLOCKED / SKIPPED>
Actual result:  <non-clarify rejected with blocked_* decision>
Evidence:       <rejected decision string>
Defect ID:      <none / DEF-###>
Severity:       <P0 if non-clarify executes / n/a>
Notes:          <optional>
```

### Scenario M — route governance unchanged

```text
Scenario ID:    M
Scenario name:  route governance unchanged
Status:         <PASS / FAIL / BLOCKED / SKIPPED>
Actual result:  34 / 34 / 5 / 0 / 1 / 1 ; STATIC_ALLOWLIST={"clarify"}
Evidence:       <test / dev-check summary line>
Defect ID:      <none / DEF-###>
Severity:       <P0 allowlist/write/Provider / P1 otherwise / n/a>
Notes:          <optional>
```

### Scenario N — Production Gateway PID unaffected

```text
Scenario ID:    N
Scenario name:  Production Gateway PID unaffected
Status:         <PASS / FAIL / BLOCKED / SKIPPED>
Actual result:  PID 69355 before and after ; Dev Gateway stopped ;
                ports 5180 / 5181 free
Evidence:       <PID before/after; port state>
Defect ID:      <none / DEF-###>
Severity:       <P0 if changed / n/a>
Notes:          <optional>
```

### Scenario O — final ports free

```text
Scenario ID:    O
Scenario name:  final ports free
Status:         <PASS / FAIL / BLOCKED / SKIPPED>
Actual result:  5180 free ; 5181 free
Evidence:       <empty lsof output for each port>
Defect ID:      <none / DEF-###>
Severity:       <P1 / P0 if held by unaccounted process / n/a>
Notes:          <optional>
```

---

## 3. Evidence Index

```text
Evidence:
  - Scenario A: <ref>
  - Scenario B: <ref>
  - ...
  - Scenario O: <ref>
```

> No evidence entry may contain a secret, an API key, the raw confirmation
> token, the full token hash, or raw arguments.

---

## 4. Defects Index

```text
Defects:
  - DEF-001: <title> (severity, category) — see defect record
  - DEF-002: ...
  - or: none
```

Each defect is recorded against
`docs/webui/phase-1g-08-pilot-defect-feedback-template.md`.

---

## 5. Decision

```text
Pilot Result:        PASS / NO-GO / PAUSED
Reason:              <one paragraph>
Required follow-up:  <list / none>
Next phase:          <e.g. Pilot execution complete; Phase 1G-09 not started>
```

---

## 6. Sign-off

```text
Operator sign-off:   <name> / <date>
Observer sign-off:   <name> / <date>  (or "none")
Approver sign-off:   <name> / <date>  (required for a final PASS)
```

> A real Pilot PASS requires a human approver sign-off. A PASS recorded without
> an approver is a recommendation only, not a release authorization.

---

## 7. Cross-References

- Pilot acceptance pack: `docs/webui/phase-1g-08-pilot-acceptance-pack.md`.
- Operator guide: `docs/webui/phase-1g-08-pilot-operator-guide.md`.
- Defect / feedback template:
  `docs/webui/phase-1g-08-pilot-defect-feedback-template.md`.
- Exit criteria: `docs/webui/phase-1g-08-pilot-exit-criteria.md`.

---

*Phase 1G-08 Pilot Acceptance Record Template — copy and fill per Pilot run.
Pilot `PILOT-1G-08-001` against RC `RC-1G-07-001` (GO).*
