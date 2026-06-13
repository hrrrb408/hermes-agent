# Phase 1G-06: Smoke Harness Runbook

## Document Information

| Field | Value |
|-------|-------|
| Phase | 1G-06 |
| Title | Execute / Audit Smoke Harness Runbook |
| Status | Authored |
| Date | 2026-06-14 |
| Branch | `dev-huangruibang` |
| Scope | Exact gate env vars, exact commands, expected results, troubleshooting, and cleanup for the execute / audit smoke harness. No code change. |

---

## 1. Purpose

This runbook fixes how the clarify controlled-execution + audit-viewer smoke is
executed. It replaces the ad-hoc `/tmp` harness used in earlier phases with a
committed, self-cleaning dev-only runner:

```
scripts/run-dev-webui-execute-audit-smoke.sh
```

The runner drives the smoke spec
`apps/hermes-dev-webui/tests/smoke/phase-1g-04-30-execute-audit-smoke.spec.ts`
across the two named gate profiles and prints a final summary (gate profile,
ports, PIDs, result, Production Gateway PID).

The smoke spec reads `EXECUTE_EXPECTED` to know which decision string to assert.
The Dev API reads the gate env vars at process startup, so each profile needs a
fresh server cycle — the harness handles that automatically for the `all` mode.

---

## 2. Environment

| Item | Value |
|------|-------|
| Source root | `/Users/huangruibang/Code/hermes-agent-dev` |
| Dev `HERMES_HOME` | `/Users/huangruibang/Code/hermes-home-dev` |
| Production `~/.hermes` | `/Users/huangruibang/.hermes` — **NEVER accessed** |
| Production Gateway PID | `69355` — **never touched** |
| Dev API bind | `127.0.0.1:5181` |
| WebUI bind | `127.0.0.1:5180` |

> The harness refuses production `HERMES_HOME`, refuses to start when the ports
> are occupied, binds to `127.0.0.1` only, and only kills the PIDs it started.

---

## 3. Scenario 1 — `blocked_tool_handler_call_not_enabled` (Profile A)

Goal: upstream execution gates are **on**, the handler-call gate is **off**, so
the execute route blocks right before the handler call.

### 3.1 Exact env vars

```bash
export HERMES_HOME=/Users/huangruibang/Code/hermes-home-dev
export HERMES_TOOL_EXECUTION_ENABLED=true
export HERMES_AGENT_TOOLS_ENABLED=true
unset HERMES_TOOL_HANDLER_CALL_ENABLED
unset HERMES_POST_EXECUTION_AUDIT_ENABLED
export EXECUTE_EXPECTED=blocked_tool_handler_call_not_enabled

unset XAI_API_KEY XAI_BASE_URL GROK_API_KEY GROK_BASE_URL
unset OPENAI_API_KEY ANTHROPIC_API_KEY ZAI_API_KEY
unset GEMINI_API_KEY GOOGLE_API_KEY OPENROUTER_API_KEY
```

### 3.2 Exact command

```bash
cd /Users/huangruibang/Code/hermes-agent-dev
./scripts/run-dev-webui-execute-audit-smoke.sh blocked
```

### 3.3 Expected results

| Check | Expected |
|-------|----------|
| API `decision` | `blocked_tool_handler_call_not_enabled` |
| `toolHandlerCalled` | `false` |
| `executionCompleted` | `false` |
| `providerSchemaSent` / `providerApiCalled` / `externalSideEffects` | all `false` |
| Post-execution audit visibility test | skipped (no execution → no post-audit) |
| Smoke count | **6 passed, 1 skipped, 0 failed** |
| Ports after run | `5180` / `5181` free |
| Production Gateway PID | `69355` unchanged |

### 3.4 Expected UI result

The Execute sub-tab renders; the dry-run surfaces a safe decision without the
raw token; the Execute decision shows the blocked decision; the Audit viewer
shows dry-run / pre-execution events but **no** post-execution event.

---

## 4. Scenario 2 — `clarify_execution_completed` (Profile B)

Goal: explicit dev/test gates on with `canonicalName=clarify`, so the bounded
clarify handler is invoked and a post-execution audit is written.

### 4.1 Exact env vars

```bash
export HERMES_HOME=/Users/huangruibang/Code/hermes-home-dev
export HERMES_TOOL_EXECUTION_ENABLED=true
export HERMES_AGENT_TOOLS_ENABLED=true
export HERMES_TOOL_HANDLER_CALL_ENABLED=true
export HERMES_POST_EXECUTION_AUDIT_ENABLED=true
export EXECUTE_EXPECTED=clarify_execution_completed

unset XAI_API_KEY XAI_BASE_URL GROK_API_KEY GROK_BASE_URL
unset OPENAI_API_KEY ANTHROPIC_API_KEY ZAI_API_KEY
unset GEMINI_API_KEY GOOGLE_API_KEY OPENROUTER_API_KEY
```

### 4.2 Exact command

```bash
cd /Users/huangruibang/Code/hermes-agent-dev
./scripts/run-dev-webui-execute-audit-smoke.sh completed
```

### 4.3 Expected results

| Check | Expected |
|-------|----------|
| API `decision` | `clarify_execution_completed` |
| `canonicalName` | `clarify` |
| `handlerCallId` | present, starts with `thc_` |
| `postExecutionAuditId` | present, starts with `pexa_` |
| `toolHandlerCalled` | `true` |
| `executionCompleted` | `true` |
| `providerSchemaSent` / `providerApiCalled` / `externalSideEffects` | all `false` |
| Smoke count | **7 passed, 0 failed** |
| Ports after run | `5180` / `5181` free |
| Production Gateway PID | `69355` unchanged |

### 4.4 Expected audit viewer result

The post-execution audit event renders under `auditKind=post_execution`; its
provider / external side-effect flags show `false`; no raw token, no full
tokenHash, no raw arguments, no provider payload.

---

## 5. Scenario 3 — fully disabled (Profile C, optional)

Goal: all gates unset (shipping default) — the system is blocked at the
earliest kill switch. This is a **safety supplement**; it does **not** replace
Profile A.

### 5.1 Exact env vars

```bash
export HERMES_HOME=/Users/huangruibang/Code/hermes-home-dev
unset HERMES_TOOL_EXECUTION_ENABLED HERMES_AGENT_TOOLS_ENABLED HERMES_TOOL_HANDLER_CALL_ENABLED
unset HERMES_POST_EXECUTION_AUDIT_ENABLED
export EXECUTE_EXPECTED=blocked_by_kill_switch   # informational only
```

### 5.2 How to run

Profile C is **not** a named harness mode (the smoke spec asserts one of the two
Profile A / B decision strings). To observe it manually, start the Dev API with
all gates unset and call the execute route directly, or set
`EXECUTE_EXPECTED=blocked_by_kill_switch` and run the smoke spec against a
manually-started server:

```bash
cd /Users/huangruibang/Code/hermes-agent-dev
export HERMES_HOME=/Users/huangruibang/Code/hermes-home-dev

# Start the Dev API with all gates unset (manual, debugging only):
.venv/bin/python -m hermes_cli.main dev-webui-api --host 127.0.0.1 --port 5181
```

### 5.3 Expected results

| Check | Expected |
|-------|----------|
| API `decision` | `blocked_by_kill_switch` (or the equivalent first-gate blocked decision) |
| `toolHandlerCalled` | `false` |
| `executionCompleted` | `false` |
| `providerSchemaSent` / `providerApiCalled` | `false` |

---

## 6. Common Mistake (important)

> **Unsetting all gates tests `blocked_by_kill_switch`, NOT
> `blocked_tool_handler_call_not_enabled`.**
>
> To test `blocked_tool_handler_call_not_enabled`, **enable the upstream
> execution gates** (`HERMES_TOOL_EXECUTION_ENABLED=true`,
> `HERMES_AGENT_TOOLS_ENABLED=true`) and **leave
> `HERMES_TOOL_HANDLER_CALL_ENABLED` unset.**

The gate order is:

```
kill switch (HERMES_TOOL_EXECUTION_ENABLED)
  → agent-tools switch (HERMES_AGENT_TOOLS_ENABLED)
  → STATIC_ALLOWLIST membership (canonical name must be "clarify")
  → dry-run historical lookup
  → confirmation token
  → digest verification
  → pre-execution audit
  → handler lookup
  → dispatch planning
  → handler-call enable gate (HERMES_TOOL_HANDLER_CALL_ENABLED)   ← Profile A stops here
  → clarify-only handler call                                      ← Profile B reaches here
  → post-execution audit
  → safe normalized response
```

The handler-call-blocked decision only appears when the upstream gates have
already passed. If the upstream gates are off, the first kill switch blocks the
request before the handler-call gate is ever evaluated.

---

## 7. Run Both Profiles (default)

```bash
cd /Users/huangruibang/Code/hermes-agent-dev
export HERMES_HOME=/Users/huangruibang/Code/hermes-home-dev
./scripts/run-dev-webui-execute-audit-smoke.sh all
```

`all` runs Profile A then Profile B, each as a **fresh** server cycle so the
gate env vars are isolated per profile. Expected overall:

- Profile A (blocked): 6 passed, 1 skipped, 0 failed.
- Profile B (completed): 7 passed, 0 failed.
- Final ports `5180` / `5181`: free.
- Production Gateway PID `69355`: unchanged.

---

## 8. Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `blocked_by_kill_switch` when you expected `blocked_tool_handler_call_not_enabled` | Upstream execution gates were unset | Set `HERMES_TOOL_EXECUTION_ENABLED=true` and `HERMES_AGENT_TOOLS_ENABLED=true`; leave the handler-call gate unset. (See §6.) |
| `blocked_tool_handler_call_not_enabled` when you expected `clarify_execution_completed` | `HERMES_TOOL_HANDLER_CALL_ENABLED` unset on the **running** API process | Stop the API, set the gate, restart. Gates are read at process startup; restarting the harness starts a fresh process with the right env. |
| `blocked_digest_mismatch` | Stale / cross-session dry-run digest | The harness mints a fresh dry-run per run; if you call the API manually, re-run the dry-run in the same server. |
| Harness aborts "Port 5180/5181 already occupied" | Leftover Dev API / WebUI | Free the port using only processes you own; the harness never kills processes it did not start. |
| Harness aborts "Expected exactly one Production Gateway with PID 69355" | Production gateway state unexpected | **Stop.** Do not modify the gateway. Report and investigate. |
| WebUI not ready within timeout | Vite cold start under load | Re-run; the harness waits up to 40s per service. Check the `/tmp/hermes-p1g06-smoke-vite.*.log` (auto-removed on clean exit). |
| `providerSchemaSent=true` / `providerApiCalled=true` | **Impossible by design** | If observed, treat as a **P0 boundary violation** — stop and report. |

---

## 9. Cleanup

The harness traps cleanup on `EXIT` / `INT` / `TERM`:

- Stops only the Dev API and WebUI PIDs it started.
- Kills WebUI child / grandchild processes (pnpm → node → vite).
- Warns (never kills) if a port is still held by a process it did not start.
- Removes its own `/tmp/hermes-p1g06-smoke-*.log` files.
- Prints the final Production Gateway PID (informational, never acted upon).

Manual confirmation after any run:

```bash
lsof -nP -iTCP:5180 -sTCP:LISTEN || echo "5180 free"
lsof -nP -iTCP:5181 -sTCP:LISTEN || echo "5181 free"
ps aux | grep '[h]ermes_cli.main gateway run'      # expect PID 69355
```

---

## 10. Final Port Checks

```bash
lsof -nP -iTCP:5180 -sTCP:LISTEN || echo "5180 free"   # expect free
lsof -nP -iTCP:5181 -sTCP:LISTEN || echo "5181 free"   # expect free
```

Both must be free at rehearsal end.

---

## 11. Production PID Checks

```bash
ps aux | grep '[h]ermes_cli.main gateway run'           # expect PID 69355 only
./scripts/run-dev-hermes.sh gateway-dev status          # Dev Gateway (read-only)
```

The Production Gateway PID must remain `69355` throughout and after the smoke.
The harness never starts, stops, restarts, replaces, or reconfigures it.

---

## 12. What the Harness Never Does

- Never reads or writes `~/.hermes`.
- Never modifies production `state.db`.
- Never exports a real provider key.
- Never prints a secret.
- Never commits test artifacts.
- Never modifies a route or the allowlist.
- Never kills a process it did not start.
- Never touches the Production Gateway.

---

## 13. Running a Single Spec Manually (debugging)

The harness is the canonical path. For debugging you may run the spec directly
against services you started yourself:

```bash
cd apps/hermes-dev-webui
EXECUTE_EXPECTED=clarify_execution_completed \
  pnpm exec playwright test tests/smoke/phase-1g-04-30-execute-audit-smoke.spec.ts
```

Reset the gate env vars afterward so the default safe posture is restored:

```bash
unset HERMES_TOOL_EXECUTION_ENABLED HERMES_AGENT_TOOLS_ENABLED \
      HERMES_TOOL_HANDLER_CALL_ENABLED HERMES_POST_EXECUTION_AUDIT_ENABLED \
      EXECUTE_EXPECTED
```

---

*Phase 1G-06 Smoke Harness Runbook — committed dev-only runner, exact gate env
vars per profile, expected UI / API / audit-viewer results, the common-mistake
note, troubleshooting, and cleanup. Production Gateway PID `69355` is never
affected.*
