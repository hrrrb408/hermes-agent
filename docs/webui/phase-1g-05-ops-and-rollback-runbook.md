# Phase 1G-05: Ops and Rollback Runbook

## Document Information

| Field | Value |
|-------|-------|
| Phase | 1G-05 |
| Title | Ops & Rollback Runbook — Dev WebUI Controlled-Execution |
| Status | Authored |
| Date | 2026-06-13 |
| Branch | `dev-huangruibang` |
| Scope | Operational procedures, troubleshooting, and rollback strategy. No code change. |

---

## 1. Environment

| Item | Value |
|------|-------|
| Source root | `/Users/huangruibang/Code/hermes-agent-dev` |
| Dev `HERMES_HOME` | `/Users/huangruibang/Code/hermes-home-dev` |
| Production `~/.hermes` | `/Users/huangruibang/.hermes` — **NEVER accessed** |
| Production Gateway PID | `69355` — **never stopped / restarted / replaced / reconfigured** |
| Dev API bind | `127.0.0.1:5181` |
| WebUI bind | `127.0.0.1:5180` |

> **Hard rule:** every Dev WebUI operation uses `/Users/huangruibang/Code/hermes-home-dev`
> and binds to `127.0.0.1` only. Production `~/.hermes` and production `state.db`
> are off-limits for all Dev WebUI work.

### 1.1 Production `~/.hermes` access prohibition

The Dev WebUI backend enforces a precise allowlist (not a deny-list) at startup:

- Source root must be `/Users/huangruibang/Code/hermes-agent-dev`.
- `HERMES_HOME` must be `/Users/huangruibang/Code/hermes-home-dev`.
- Bind host must be `127.0.0.1`.

Any mismatch → **fail closed** (refuse to start, refuse all API requests).
The audit JSONL reader additionally rejects any production path.

---

## 2. Production Gateway PID Check

```bash
ps aux | grep '[h]ermes_cli.main gateway run'
```

Expected: exactly one production gateway process with **PID `69355`**.

If the PID is **not** `69355`, or there is more than one gateway process, **stop
all Dev WebUI work immediately** and report. Do not attempt to "fix" the
production gateway.

```bash
./scripts/run-dev-hermes.sh gateway-dev status      # Dev Gateway only (read-only)
```

The Dev Gateway is a **separate** process from the production Gateway. The
status command is read-only and never touches production.

---

## 3. Dev Gateway Start / Stop

```bash
# Read-only status:
./scripts/run-dev-hermes.sh gateway-dev status

# Start (binds to 127.0.0.1, dev HERMES_HOME only):
./scripts/run-dev-hermes.sh gateway-dev run

# Stop:
./scripts/run-dev-hermes.sh gateway-dev stop
```

> **Note:** Unless explicitly requested, do **not** run `gateway-dev run` /
> `gateway-dev stop`. The Pilot and release gates do not require the Dev Gateway.
> The Dev Gateway must never collide with the production Gateway.

Dev Gateway state lives under `/Users/huangruibang/Code/hermes-home-dev/gateway/dev/`.

---

## 4. WebUI Dev Server Start / Stop

### 4.1 Quick smoke cycle (Dev API + WebUI)

```bash
cd /Users/huangruibang/Code/hermes-agent-dev
export HERMES_HOME=/Users/huangruibang/Code/hermes-home-dev

# Full smoke cycle (starts Dev API 5181 + WebUI 5180, runs Playwright smoke, tears down):
./scripts/run-dev-webui-smoke.sh

# Start services only (no smoke):
./scripts/run-dev-webui-smoke.sh --skip-smoke

# Keep services running after smoke:
./scripts/run-dev-webui-smoke.sh --keep-running
```

The runner:
- Binds to `127.0.0.1` only (ports `5180`, `5181`).
- Refuses to use production `HERMES_HOME` (`~/.hermes`).
- Refuses to start if the ports are occupied.
- Only kills processes **it** started.
- Never affects the production Gateway; never starts the Dev Gateway or Dashboard.

### 4.2 Manual Dev API / WebUI (debugging only)

```bash
# Dev API (isolated):
HERMES_HOME=/Users/huangruibang/Code/hermes-home-dev \
  .venv/bin/python -m hermes_cli.main dev-webui-api --host 127.0.0.1 --port 5181

# WebUI (separate terminal):
cd apps/hermes-dev-webui && pnpm dev --host 127.0.0.1 --port 5180
```

### 4.3 Gate env vars

The smoke runner **inherits** gate env vars from the calling shell. To select
the gate configuration, export them before invoking the runner:

```bash
# Default-blocked posture (shipping default; nothing to export):
unset HERMES_TOOL_EXECUTION_ENABLED HERMES_AGENT_TOOLS_ENABLED HERMES_TOOL_HANDLER_CALL_ENABLED
export EXECUTE_EXPECTED=blocked_tool_handler_call_not_enabled

# Explicit dev/test completed posture:
export HERMES_TOOL_EXECUTION_ENABLED=true
export HERMES_AGENT_TOOLS_ENABLED=true
export HERMES_TOOL_HANDLER_CALL_ENABLED=true
export EXECUTE_EXPECTED=clarify_execution_completed
```

`EXECUTE_EXPECTED` tells the smoke spec which decision string is expected on the
current server configuration. Always reset these with `unset` after a completed
run so the default safe posture is restored.

---

## 5. Browser Smoke Runbook

```bash
cd /Users/huangruibang/Code/hermes-agent-dev
export HERMES_HOME=/Users/huangruibang/Code/hermes-home-dev

# --- Blocked scenario ---
unset HERMES_TOOL_EXECUTION_ENABLED HERMES_AGENT_TOOLS_ENABLED HERMES_TOOL_HANDLER_CALL_ENABLED
export EXECUTE_EXPECTED=blocked_tool_handler_call_not_enabled
./scripts/run-dev-webui-smoke.sh

# --- Completed scenario ---
export HERMES_TOOL_EXECUTION_ENABLED=true
export HERMES_AGENT_TOOLS_ENABLED=true
export HERMES_TOOL_HANDLER_CALL_ENABLED=true
export EXECUTE_EXPECTED=clarify_execution_completed
./scripts/run-dev-webui-smoke.sh

# Reset to safe default:
unset HERMES_TOOL_EXECUTION_ENABLED HERMES_AGENT_TOOLS_ENABLED HERMES_TOOL_HANDLER_CALL_ENABLED EXECUTE_EXPECTED
```

Expected (sealed baseline):

- Blocked: **6 passed, 1 skipped, 0 failed** (the skip is the post-execution-audit
  visibility test, correctly skipped when execution is blocked).
- Completed: **7 passed, 0 failed**.

Run a single spec directly:

```bash
cd apps/hermes-dev-webui
pnpm exec playwright test tests/smoke/phase-1g-04-30-execute-audit-smoke.spec.ts
```

---

## 6. Log Locations

| What | Path |
|------|------|
| Dev API smoke log | `/tmp/hermes-dev-webui-smoke-api.<pid>.log` |
| WebUI (vite) smoke log | `/tmp/hermes-dev-webui-smoke-vite.<pid>.log` |
| Dev Gateway log | `/Users/huangruibang/Code/hermes-home-dev/logs/gateway-dev.log` |
| Dev WebUI logs | under `/Users/huangruibang/Code/hermes-home-dev/logs/` |

Smoke logs are written to `/tmp` and are safe to inspect/delete. They never
contain the raw confirmation token (held in-memory only).

---

## 7. Audit JSONL Locations

Audit JSONL files are **runtime-generated** under the dev `HERMES_HOME` only:

| Kind | Path |
|------|------|
| Dry-run audit | `/Users/huangruibang/Code/hermes-home-dev/gateway/dev/audit/tool-dry-run-audit.jsonl` |
| Pre-execution audit | `/Users/huangruibang/Code/hermes-home-dev/gateway/dev/audit/tool-pre-execution-audit.jsonl` |
| Post-execution audit | `/Users/huangruibang/Code/hermes-home-dev/gateway/dev/audit/tool-post-execution-audit.jsonl` |
| Confirmation tokens | `/Users/huangruibang/Code/hermes-home-dev/gateway/dev/audit/confirmation-tokens.jsonl` |

These files are **never committed** (verified by the forbidden-file check).
Read them only through the read-only audit events API
(`GET /api/dev/v1/tools/audit-events`) or the safe JSONL reader module — both
redact secrets, reject production paths, and whitelist-normalize arguments.

---

## 8. Safe Cleanup

```bash
# Confirm Dev API / WebUI (5180/5181) are stopped:
lsof -nP -iTCP:5180 -sTCP:LISTEN || echo "5180 free"
lsof -nP -iTCP:5181 -sTCP:LISTEN || echo "5181 free"

# Confirm production Gateway untouched:
ps aux | grep '[h]ermes_cli.main gateway run'      # expect PID 69355

# Smoke /tmp logs can be removed (optional):
rm -f /tmp/hermes-dev-webui-smoke-api.*.log /tmp/hermes-dev-webui-smoke-vite.*.log
```

**Do not** delete:

- Anything under `/Users/huangruibang/Code/hermes-home-dev/` unless explicitly
  told to (it holds dev sessions, memories, audit state).
- Anything under `/Users/huangruibang/.hermes` (production).
- Any tracked repo file via `git clean -fd` / `git reset --hard` (forbidden).

---

## 9. Rollback Strategy

### 9.1 Hard prohibitions during rollback

- ❌ `git reset --hard`
- ❌ `git push --force` / `--force-with-lease` / `-f`
- ❌ `git rebase`, `git merge` (to alter history)
- ❌ production state mutation (any write to `~/.hermes` or production `state.db`)
- ❌ stopping / restarting / replacing the production Gateway

### 9.2 Recommended rollback steps

1. **Do not auto-rollback** during a release task. If a rollback is needed,
   **stop and request user confirmation** first.
2. **Preserve evidence and logs** before any revert — copy the relevant smoke
   logs and note the failing decision / gate.
3. **Use a new `git revert` commit**, not `git reset --hard`. A revert is an
   additive, history-preserving change that can itself be reviewed and pushed.
4. After the revert, **re-run the release checklist**
   (`docs/webui/phase-1g-05-release-checklist.md`) to confirm the system returns
   to a known-good state.
5. Confirm production Gateway PID `69355` is unchanged and ports `5180` / `5181`
   are free.

### 9.3 When rollback is NOT the right tool

If the issue is a **safety-boundary** finding (allowlist expansion, Provider
activity, secret leak, production access), rollback alone is insufficient — the
boundary must be re-verified and the root cause addressed in a separately
approved phase. Rollback returns the code to a prior state; it does not by
itself prove the boundary holds.

---

## 10. Blocked-Execution Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `blocked_by_kill_switch` | `HERMES_TOOL_EXECUTION_ENABLED` / `HERMES_AGENT_TOOLS_ENABLED` unset | Expected in production-safe posture. To test execution, set both to `true`. |
| `blocked_tool_handler_call_not_enabled` | `HERMES_TOOL_HANDLER_CALL_ENABLED` unset | Expected when only kill switches are on. Set the handler-call gate to `true` **only** for the dev/test completed scenario. |
| Non-`clarify` tool blocked | Allowlist gate | **Correct behavior.** Only `clarify` is allowlisted. Do not expand the allowlist. |
| 409 / single-generation rejection | A generation already runs for the session | Wait for it to finish or use a different session. |

> `blocked_tool_handler_call_not_enabled` is the **intended** default. It is not
> a bug. A pre-execution audit record may still be written (durable attempt), but
> no execution occurs.

---

## 11. Audit Viewer Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Empty state | No audit events of the selected kind yet | Run a dry-run / execute first. |
| `audit_read_kind_invalid` (400) | Unknown `auditKind` | Use `dry_run`, `pre_execution`, or `post_execution`. |
| POST returns 405 | Audit events API is read-only GET only | Use GET. |
| Malformed-line skip note | A JSONL line failed to parse | Inspect the JSONL via the safe reader; the viewer skips bad lines safely. |
| Missing post-execution event | Execution was blocked (no post-execution audit) | Expected on the blocked path. |

The audit viewer shows only whitelist-normalized, redacted fields. If raw
arguments ever appear, treat it as a **P0 leak** and stop.

---

## 12. Digest-Mismatch Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `blocked_digest_mismatch` | Dry-run digest does not match execute recomputation | Re-run the dry-run in the same server/session; the digest-binding fix (Phase 1G-04-30) binds the digest to the real audit `eventId` / timestamp / expiry. A stale or cross-session digest must fail closed. |
| Expired confirmation token | Token TTL elapsed | Re-run dry-run to mint a fresh token. |
| `blocked_confirmation_token_*` | Token already consumed or invalid | One-shot tokens are consumed on use; re-run dry-run. |

A digest mismatch is a **safety feature**, not a bug. Do not weaken the
exact-match requirement.

---

## 13. Port Conflict Troubleshooting

```bash
lsof -nP -iTCP:5180 -sTCP:LISTEN
lsof -nP -iTCP:5181 -sTCP:LISTEN
```

| Symptom | Fix |
|---------|-----|
| Port occupied by a leftover Dev API / WebUI | Stop it via the process owning the PID; only kill processes you started. The smoke runner tracks its own PIDs and cleans them up. |
| Port occupied by an unknown process | **Do not kill blindly.** Identify the owner first; if it could be production, stop and report. |

The smoke runner refuses to start if the ports are occupied — that is intended.

---

## 14. Provider-Disabled Troubleshooting

Provider integration is a **permanent non-goal** for this controlled path. There
is no Provider Schema and no Provider API call.

| Symptom | Expected state |
|---------|----------------|
| No provider payload anywhere | **Correct.** `providerSchemaSent=false`, `providerApiCalled=false` everywhere. |
| A request attempts a Provider call | **Impossible by design.** If observed, it is a P0 — stop and report. |

If a `provider*` flag is ever `true`, treat it as a **P0 boundary violation**.

---

## 15. Emergency Stop Conditions

**Stop all Dev WebUI work immediately and report if any of these occur:**

1. `STATIC_ALLOWLIST` is not exactly `frozenset({"clarify"})`.
2. A non-`clarify` tool executes or becomes allowlisted.
3. `providerSchemaSent=true` or `providerApiCalled=true` appears anywhere.
4. The raw confirmation token appears in a response, the DOM, a log, the
   console, `localStorage`, `sessionStorage`, or an audit event.
5. The full token hash is surfaced (only a short digest / token ID is allowed).
6. Raw arguments appear in the audit viewer.
7. A secret / API key / credential is logged or committed.
8. The production `~/.hermes` or production `state.db` is accessed or modified.
9. Production Gateway PID `69355` changes (stopped, restarted, replaced).
10. A Tool write route, a second execution route, or a Provider route appears.
11. Audit JSONL or `.claude/` is staged or committed.
12. Any force push, rebase, or `git reset --hard` is attempted.

On any emergency stop, preserve logs, do **not** push, and report the boundary
violation for a separately approved remediation phase.

---

## 16. Phase 1G-06 Addendum — Committed Smoke Harness & Gate Profiles

Phase 1G-06 hardens this runbook's browser-smoke section (§5) with a committed
dev-only harness and fixed gate profiles. It changes nothing operational above.

- Phase 1G-04 remains **SEALED**; Phase 1G-05 remains the **pushed** baseline;
  route governance and `STATIC_ALLOWLIST` are unchanged.
- The ad-hoc `/tmp` harness is replaced by the committed runner
  `scripts/run-dev-webui-execute-audit-smoke.sh`:
  ```bash
  ./scripts/run-dev-webui-execute-audit-smoke.sh blocked     # Profile A
  ./scripts/run-dev-webui-execute-audit-smoke.sh completed   # Profile B
  ./scripts/run-dev-webui-execute-audit-smoke.sh all         # A then B
  ```
  It binds to `127.0.0.1` only, refuses production `HERMES_HOME`, pre-checks
  ports `5180` / `5181`, kills only the PIDs it started, traps cleanup, and
  never affects the Production Gateway.
- **Gate-config note (the key correction):** to observe
  `blocked_tool_handler_call_not_enabled` you must enable the upstream execution
  gates (`HERMES_TOOL_EXECUTION_ENABLED=true`, `HERMES_AGENT_TOOLS_ENABLED=true`)
  and leave `HERMES_TOOL_HANDLER_CALL_ENABLED` **unset**. Unsetting *all* gates
  instead yields `blocked_by_kill_switch` (the first kill switch) — it does
  **not** exercise the handler-call blocked decision.
- Full runbook, troubleshooting, and Profile C (fully-disabled) variant:
  `docs/webui/phase-1g-06-smoke-harness-runbook.md`.

---

*Phase 1G-05 Ops & Rollback Runbook — dev-only operations, read-only production
checks, revert-based rollback (never reset / force), and P0 emergency stop
conditions. Production Gateway PID `69355` must remain unaffected throughout.*
