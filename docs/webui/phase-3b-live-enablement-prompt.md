# Phase 3B-Live-Enablement Prompt Draft — Strict Manual Real Provider Enablement

## Document Information

| Field | Value |
|-------|-------|
| Phase | 3B-Live-Enablement |
| Title | Phase 3B-Live-Enablement Execution Prompt (Draft) |
| Status | Draft prepared — **NOT to be executed in this planning phase** |
| Date | 2026-06-17 |
| Branch | `dev-huangruibang` |
| Planning ID | `PHASE-3B-LIVE-ENABLEMENT-PLANNING-001` |
| Prompt ID | `PHASE-3B-LIVE-ENABLEMENT-PROMPT-001` |

> **This is a prompt draft only.** It is the starting brief for a future,
> separately-authorized Phase 3B-Live-Enablement. **Do not execute live
> enablement during this planning phase.** Live enablement requires explicit user
> approval and may begin only when the user explicitly asks for it and separately
> authorizes it.

---

## How to use this document

When the user is ready to start live enablement, the prompt in the fenced block
below is the copy-paste starting brief. It encodes the baseline, scope,
non-goals, human approval model, secret-read policy, network allowlist, budget
policy, audit policy, kill switch, smoke strategy, GO / NO-GO, production safety,
commit / push discipline, and final report format.

Before running it, confirm the live-enablement entry gate (see
[phase-3b-live-enablement-go-no-go.md](phase-3b-live-enablement-go-no-go.md) §5).

---

## Prompt (copy-paste draft)

```text
Phase 3B-Live-Enablement — Strict Manual Real Provider Read-only Enablement

You are responsible for executing Phase 3B-Live-Enablement of the Hermes Dev
WebUI. Read and respect CLAUDE.md and the live-enablement planning docs under
docs/webui/ (phase-3b-live-enablement-planning.md and its companion scope /
human-approval / secret-read / network / budget / audit / kill-switch / smoke /
risk / GO-NO-GO / brief docs).

This prompt is a DRAFT. Do NOT execute live enablement during planning. Live
enablement requires explicit user approval. Only proceed when the user has
explicitly authorized the live test.

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
- Input HEAD = the live-enablement planning commit
  (docs(webui): plan provider live enablement).
- Live enablement is separately authorized by this prompt AND by an explicit
  user request. If the user has not explicitly authorized the live test, STOP.

================================================================
1. SCOPE (allowed)
================================================================
- Live human-approval model: issue / validate / expire / revoke. Single-use,
  5-minute window for the first live test; manual renewal required.
- Concrete real HTTP client wired into the EXISTING real-gated provider path.
  Reuse the mode-branched /tools/dry-run + /tools/execute surface. NO NEW ROUTE.
- Empty-default network allowlist; operator-approved HTTPS host only
  (recommended initial: api.openai.com).
- Live budget / rate-limit caps layered on the Phase 3B budget modules:
  1 request, <=1000 total tokens (<=200 output), <=5 cents, 0 retries, 60 s.
- Kill switch + disable / rollback procedure (14 triggers; revokes approval).
- provider_live_* audit events: redacted, dual-written, fail-closed.
- Smoke layers 0-5 (deterministic, injected MockHttpClient) + opt-in layer 6.

================================================================
2. NON-GOALS (forbidden)
================================================================
- No provider write / auto-write / rollback execute / autonomous write.
- No shell / database / external-tool calls.
- No streaming. No multi-provider routing. No background tasks / cron.
- No production rollout. No ~/.hermes access. No production state.db access.
- No dynamic plugin loading. No arbitrary-URL fetch. No off-allowlist redirect.
- No storing / logging / committing an API key. No UI API-key input.
- No new HTTP route, no Provider route, no Tool write HTTP route.
- No reading a real API key outside the live process local.
- No executing provider tool calls in the first live test (classify / block only).

================================================================
3. HUMAN APPROVAL MODEL
================================================================
- No approval => fail closed (blocked_live_provider_not_human_approved).
- Approval record fields: approvalId, approvalScope=provider_live_enablement,
  providerName, providerMode=real, model, baseUrlHost, budgetCap, requestCap,
  tokenCap, toolAllowlist, expiresAt, approvedBy=human_operator, auditRequired.
- Approval record MUST NEVER contain: API key, Authorization header, bearer
  token, raw prompt/response with secrets, production path.
- Scope mismatch => blocked_live_provider_approval_scope_invalid.
- Expiry => blocked_live_provider_approval_expired. Renewal = fresh approval.

================================================================
4. SECRET READ POLICY
================================================================
- API key source = environment ONLY (OPENAI_API_KEY). Never UI / file / store /
  docs / git.
- Read once into a local; attach to a single outbound Authorization header on the
  single approved request; drop both immediately after the call.
- The value MUST NEVER appear in audit, logs, exceptions, responses, UI, tests,
  or commits.
- Secret-state audit may record ONLY: keySource=environment,
  keyState=env_present|env_missing, keyFingerprint=disabled, keyValue=never,
  authorizationHeader=never.

================================================================
5. NETWORK ALLOWLIST
================================================================
- HTTPS only. Empty default allowlist. Operator-approved host at approval time.
- No http://, no arbitrary URL, no off-allowlist redirect, no response fetch,
  no localhost/private-IP host unless separately approved.
- Bounded timeout; bounded response size (<=64 KiB).

================================================================
6. BUDGET / RATE LIMIT
================================================================
- First live test: maxRequests=1, maxTotalTokens=1000, maxInputTokens=800,
  maxOutputTokens=200, maxBudgetCents=5, maxRuntimeSeconds=60, maxRetries=0.
- Counters atomic, under dev HERMES_HOME only, fail-closed on corruption.
- spentEstimate / remainingEstimate derived from token counts, never key material.

================================================================
7. READ-ONLY TOOL POLICY
================================================================
- Allowed tools (unchanged from Phase 2A): clarify, tool_policy_read,
  route_governance_read, audit_events_read, dev_environment_read,
  release_status_read.
- Blocked: dev_sandbox_file_write/append/patch/readback, rollback_execute, shell,
  database, external_http, production_operation, plugin_dynamic_load, workflow
  write/rollback execution.
- Provider tool calls are validated (not executed) in the first live test.

================================================================
8. AUDIT POLICY
================================================================
- provider_live_* events: requested/approved/denied/expired/started/completed/
  failed/kill_switch_triggered, secret_state_checked, network_request_started/
  completed/blocked, budget_checked/blocked, tool_call_requested/blocked/
  completed, disable_completed.
- Safe fields only (providerName, providerMode, approvalId, requestId,
  responseId, workflowId, model, baseUrlHost, toolId, toolCallId, status,
  blockedReason, redactionApplied, budgetCap, requestCap, tokenCap,
  usageSummary, costEstimate, safeMetadata).
- redactionApplied=true; defensive re-redaction before write; audit write
  failure on a live request => fail closed.

================================================================
9. KILL SWITCH / ROLLBACK
================================================================
- 14 triggers: manual, budget exceeded, rate exceeded, secret detected, response
  too large, malformed/unsafe response, off-allowlist redirect, route drift, PID
  drift, audit write failure, unexpected tool-call, write/autonomous suggestion,
  smoke failure, manual abort.
- On trigger: set live disabled, invalidate approval, block future live
  requests, write kill-switch audit (redacted), surface safe UI status, require
  fresh approval to re-enable.
- Disable procedure: unset HERMES_PROVIDER_API_ENABLED; set
  HERMES_PROVIDER_MODE=disabled; clear approval store; confirm UI disabled;
  re-run route governance (34/34/5/0/1/1); re-run blocked-real smoke; verify no
  live request possible; verify PID unchanged; document.

================================================================
10. SMOKE STRATEGY
================================================================
- Layers 0-5 deterministic/offline (injected MockHttpClient).
- Layer 6 = single live request, opt-in, operator-witnessed, never in the
  default `all` target. One request, no tool execution, no write, no retry,
  <=5 cents, non-streaming, redacted audit, immediate auto-disable.

================================================================
11. GO / NO-GO
================================================================
- Implementation prompt may be prepared: yes.
- Live provider may be enabled now: only under the entry gate (go-no-go §5).
- Real API key may be read now: only inside the live process local, under an
  active approval.
- Real network may be called now: only one HTTPS POST to the allowlisted host.
- Human approval required: yes. Budget cap required: yes. Kill switch required:
  yes. Production rollout allowed: no. Provider write allowed: no. Autonomous
  write allowed: no.

================================================================
12. PRODUCTION SAFETY
================================================================
- Production Gateway PID 28428 must stay unchanged; count must stay 1.
- Dev services bind 127.0.0.1 only. No ~/.hermes access. No production state.db
  access. No runtime artifacts committed. No .claude/ committed.

================================================================
13. COMMIT / PUSH
================================================================
- Commit message (planning phase): docs(webui): plan provider live enablement
- Future execution commit, e.g.: feat(webui): add live provider enablement layer
- Push only: git push origin dev-huangruibang
- No force push / rebase / merge / reset / amend.

================================================================
14. FINAL REPORT
================================================================
- Mirror the Phase 3B / 3B-H1 closeout structure: scope, what changed, what did
  not change, route governance (34/34/5/0/1/1), production safety (PID 28428),
  gates, smoke layers, residual risks (P2), conclusion.
```

---

## Cross-references

- [Phase 3B-Live-Enablement planning](phase-3b-live-enablement-planning.md)
- [Phase 3B-Live-Enablement execution brief](phase-3b-live-enablement-execution-brief.md)
- [Phase 3B-Live-Enablement GO / NO-GO](phase-3b-live-enablement-go-no-go.md)
- [Phase 3B prompt draft](phase-3b-prompt.md)
