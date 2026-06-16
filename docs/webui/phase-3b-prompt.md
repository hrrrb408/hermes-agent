# Phase 3B Prompt Draft — Real Provider Read-only Controlled Integration

## Document Information

| Field | Value |
|-------|-------|
| Phase | 3B |
| Title | Phase 3B Execution Prompt (Draft) |
| Status | Draft prepared — **NOT to be executed in this planning phase** |
| Date | 2026-06-16 |
| Branch | `dev-huangruibang` |
| Planning ID | `PHASE-3B-PLANNING-001` |
| Prompt ID | `PHASE-3B-PROMPT-001` |

> **This is a prompt draft only.** It is the starting brief for a future,
> separately-authorized Phase 3B. **Do not execute Phase 3B in this planning
> phase.** Phase 3B may begin only when the user explicitly asks for it and
> separately authorizes it.

---

## How to use this document

When the user is ready to start Phase 3B, the prompt in the fenced block below is
the copy-paste starting brief. It encodes the baseline, goal, scope, non-goals,
provider config, secret strategy, network boundary, request / response schema,
audit model, read-only tool-call allowlist, blocked reasons, tests, smoke, route
governance, production safety, commit / push discipline, and final report format.

Before running it, confirm the Phase 3B entry gate (see
[phase-3b-go-no-go.md](phase-3b-go-no-go.md) §5).

---

## Prompt (copy-paste draft)

```text
Phase 3B — Real Provider Read-only Controlled Integration

You are responsible for executing Phase 3B of the Hermes Dev WebUI. Read and
respect CLAUDE.md and the Phase 3B planning docs under docs/webui/
(phase-3b-planning.md and its companion scope / matrix / secret / network /
schema / audit / failure / cost / risk / GO-NO-GO / brief docs).

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
- Input HEAD = the Phase 3B planning commit
  (docs(webui): plan phase 3b provider integration).
- Phase 3B is separately authorized by this prompt.
- Do NOT read real API keys, do NOT print API keys, do NOT make a real network
  call until the explicit real path is implemented AND fully enabled by the
  operator. Smoke and tests must use the FAKE provider + blocked-real mode only.

================================================================
1. PHASE 3B GOAL
================================================================
Wire the one blocked thing left by Phase 2B-H1 — the concrete real-vendor HTTPS
round-trip inside RealProviderAdapter — as a disabled-by-default, operator-enabled,
single-round-trip, NON-STREAMING, READ-ONLY path behind the existing provider
boundary. Reuse Phase 2B (schema / request / fake adapter / blocked real adapter
/ audit / sanitizer), Phase 2A read-only allowlist, Phase 2C-H1 confirmation,
Phase 2D durable audit store, Phase 2E/2E-H1 console + no-leak closure. Every
request / response / tool call / failure is audited and redacted.

================================================================
2. SCOPE (ALLOWED)
================================================================
- Provider config model (env-driven, disabled by default).
- Generic provider adapter interface; first concrete impl = OpenAI-compatible
  (non-streaming).
- OpenAI-compatible read-only request/response schema (non-streaming).
- Real-provider disabled-by-default boundary + explicit enable flag.
- API-key env strategy: env only; never UI; never stored / logged / committed.
- Secret redaction: reuse + extend the Phase 2B-H1 sanitizer.
- Read-only tool-call allowlist: reuse the Phase 2A STATIC_ALLOWLIST unchanged
  (clarify, tool_policy_read, route_governance_read, audit_events_read,
  dev_environment_read, release_status_read).
- Provider request preview (redacted) + response normalization (safe summary).
- Timeout / retry / rate-limit / cost policies (bounded, capped, audited).
- provider_real_* audit events into the Phase 2D durable store.
- UI real-provider blocked / disabled / preview states; NO API-key input control.
- Tests + an additive smoke profile (fake + blocked-real; NO real spend).

================================================================
3. NON-GOALS (FORBIDDEN)
================================================================
- No provider write; no provider auto-write; no provider rollback execute.
- No autonomous agent; single round-trip only.
- No shell command; no database mutation; no external service write beyond the
  single allowed provider HTTPS call.
- No production rollout; no ~/.hermes access; no production state.db access.
- No dynamic plugin loading.
- No streaming in the first implementation.
- No multi-provider routing in the first implementation.
- No background tasks / schedule / cron.
- No storing / logging / committing an API key.
- No exposing a raw provider prompt or response containing secrets.
- No arbitrary-URL fetch (base-URL allowlist only).

================================================================
4. PROVIDER CONFIG (env only, future implementation)
================================================================
HERMES_PROVIDER_MODE=disabled|fake|real         (default disabled)
HERMES_PROVIDER_API_ENABLED=0|1                 (default 0)
HERMES_PROVIDER_NAME=openai_compatible|anthropic_compatible|zai_compatible|openrouter_compatible
HERMES_PROVIDER_BASE_URL=<allowlisted host; redacted in audit>
HERMES_PROVIDER_MODEL=<allowlisted model id; safe string>
HERMES_PROVIDER_TIMEOUT_SECONDS=<bounded>
HERMES_PROVIDER_MAX_RETRIES=<bounded>
HERMES_PROVIDER_DAILY_BUDGET_CENTS=<bounded>
Provider API key: read from env ONLY (e.g. OPENAI_API_KEY). Never UI. Never
stored / logged / committed. Audit records only apiKeySourceDetail =
env_present | env_missing.

================================================================
5. SECRET STRATEGY (env-only key)
================================================================
- The API key is read once per outbound request, into a local var, attached as a
  single header, dropped after the call. Never module-global, never cached, never
  serialized.
- The request envelope NEVER carries apiKey / Authorization / raw secret / raw
  token / full tokenHash / production path / raw file content / callable repr.
- The response envelope NEVER carries a raw secret / key / header / raw token /
  full tokenHash / callable repr / unbounded raw body.
- Reuse the Phase 2B-H1 sanitizer: sk-…, Bearer …, Authorization: …, PEM
  private keys, forbidden field stems -> [REDACTED]; non-JSON values ->
  <non_json_value>; nesting depth <= 8.
- Secret detected in request/response/args -> block with
  blocked_provider_secret_detected.

================================================================
6. NETWORK BOUNDARY
================================================================
- The ONLY allowed external network is a single outbound HTTPS POST to the
  allowlisted provider endpoint. https:// only. Off-allowlist redirects blocked.
- Requires HERMES_PROVIDER_API_ENABLED=1 AND HERMES_PROVIDER_MODE=real AND key
  present AND dev home AND production PID gate AND base URL on allowlist. Any
  missing -> blocked_provider_* with externalNetworkCalled=false.
- Bounded connect / read / total timeouts; bounded max response size; capped
  retries (safe-transient only; NO retry on auth / budget / policy / oversize /
  secret); per-minute + daily request caps; daily token cap; daily budget cap;
  model allowlist.
- Blocked reasons (frozen):
  blocked_provider_real_not_enabled, blocked_provider_api_disabled,
  blocked_provider_base_url_not_allowed, blocked_provider_api_key_missing,
  blocked_provider_timeout_invalid, blocked_provider_rate_limit_exceeded,
  blocked_provider_budget_exceeded, blocked_provider_response_too_large,
  blocked_provider_tool_call_not_allowed, blocked_provider_write_not_allowed,
  blocked_provider_external_url_not_allowed, blocked_provider_secret_detected.

================================================================
7. REQUEST / RESPONSE SCHEMA
================================================================
- Request includes: providerMode, providerName, model, requestId, conversationId,
  workflowId, toolAllowlist, messages, maxTokens, temperature, timeoutSeconds,
  redactionPolicy, auditRequired.
- Response includes: requestId, responseId, providerName, model, status,
  contentSummary, toolCalls, usageSummary, finishReason, blockedReason,
  auditLinks, redactionApplied, externalNetworkCalled, costEstimate.
- Both shapes are the SAME across fake and real adapters (only the adapter
  differs) so contract tests assert against the envelope, not the wire payload.

================================================================
8. READ-ONLY TOOL-CALL ALLOWLIST
================================================================
- Provider may request ONLY: clarify, tool_policy_read, route_governance_read,
  audit_events_read, dev_environment_read, release_status_read.
- Each call: validate tool id -> validate args -> dry-run -> manual approval if
  required -> execute read-only -> write provider tool-call audit -> write
  tool-result audit -> return safe summary (never raw args / secrets / tokens).
- Write / shell / db / external-http / production-operation / plugin-load calls
  are blocked.

================================================================
9. AUDIT MODEL
================================================================
- Emit provider_real_* events: request_previewed, request_blocked,
  request_started, request_completed, request_failed, response_redacted,
  tool_call_requested, tool_call_blocked, tool_call_completed, budget_blocked,
  rate_limit_blocked.
- Dual-write to the Phase 2D durable store (auditKind=provider) + the dev-only
  provider audit JSONL. Reuse the Phase 2B writer / sanitizer / containment.
- Every record carries safeMetadata (apiKeySource / apiKeyPresent /
  apiKeySourceDetail / allowlistedBaseUrl / modelName / adapterName) — NEVER the
  key value, header, raw token, full hash, raw body, or production path.

================================================================
10. ROUTES
================================================================
Default: NO new HTTP route, NO Tool write HTTP route, NO Provider route. The real
round-trip is a new mode branch (or providerMode=real extension) on the EXISTING
POST /tools/dry-run + POST /tools/execute. If a Provider route is truly needed,
stop, document the requirement, and request explicit separate authorization
before adding any route. Route governance stays 34/34/5/0/1/1.

================================================================
11. UI MODEL
================================================================
- The provider panel gains blocked / disabled / preview states for real mode, a
  redacted request preview, a safe response summary, a budget badge (safe
  metadata only), and blocked-reason panels. NO API-key input control.
- Inherit the Phase 2E-H1 accessibility baseline + no-leak closure.
- /#/ and the Workflow section stay unchanged.

================================================================
12. SMOKE
================================================================
- Add a new additive smoke profile (e.g. phase3b_provider_real_readonly) + spec,
  wired into the `all` target. It MUST exercise the fake path AND the blocked-real
  path (real provider disabled / not enabled -> blocked reason,
  externalNetworkCalled=false). It MUST NEVER make a real network call and MUST
  NEVER incur real spend.
- All existing smoke profiles must keep passing (zero regression).
- PID 28428 unchanged; ports 5180 / 5181 free at the end.

================================================================
13. TESTS
================================================================
- Backend unit / contract: config gating (disabled/fake/real), adapter interface,
  request/response schema, redaction, read-only tool-call validation,
  timeout/retry/rate-limit/cost enforcement, audit coverage, route-governance
  no-new-route, no-leak. An OFFLINE test asserts the real adapter returns a
  blocked reason when enablement is missing, externalNetworkCalled=false.
- Frontend unit: provider panel real-states, budget badge, blocked-reason panels,
  no-leak.
- Type-check (vue-tsc), lint (eslint), build (vite) must pass.

================================================================
14. SAFETY GATES (run before commit and before push)
================================================================
- Route governance: scripts/run_tests.sh tests/test_dev_check_webui.py
  tests/test_dev_web_0c06_closure.py -q  -> 34/34/5/0/1/1, 0 failed.
- memory-check + dev-check PASS (only .claude/ untracked WARN allowed).
- Boundary searches on the diff:
  * no runtime artifacts (audit-store / token / rollback manifest / cost-counter /
    *.jsonl / test-results / playwright-report / coverage / dist / node_modules).
  * no secrets (api_key / authorization / bearer / sk- / PEM / BEGIN PRIVATE KEY)
    except inside safety statements / negations / risk descriptions / blocked
    reasons / schema docs.
  * no dangerous exec (subprocess / os.system / eval / exec / shell=True /
    sqlite3 mutations / requests.post / httpx / urllib / aiohttp / curl) except
    inside forbidden-item / risk / boundary statements.
  * no production access (~/.hermes / production state.db) except inside
    forbidden-item / boundary statements.
- Production safety: PID 28428, count 1, dev gateway stopped, dashboard not
  started, 5180 / 5181 free. No ~/.hermes access. No production state.db access.

================================================================
15. COMMIT / PUSH
================================================================
- Commit with a conventional message, e.g.:
    feat(webui): add read-only real provider round-trip
- Confirm .claude/ is not staged. Confirm no runtime artifact is staged. Confirm
  no API key / secret is staged.
- Push only with: git push origin dev-huangruibang
- Never force push / rebase / merge / reset --hard / amend.
- If push fails, stop and report; do not force anything.

================================================================
16. FINAL REPORT
================================================================
Produce a Phase 3B closeout report under docs/webui/ mirroring the Phase 3A-H1
structure: scope, what changed, what did NOT change, route governance, production
safety, gates, residual risks (P2), conclusion. Confirm Phase 3B kept the real
provider disabled by default, performed NO provider write / auto-write /
autonomous execution, added NO shell / db / external write, NO streaming, NO
multi-provider routing, NO production rollout, did NOT access ~/.hermes or
production state.db, did NOT leak any API key / secret, and left route governance
and PID 28428 unchanged.
```

---

## Reminder

**This is a prompt draft only. Do not execute Phase 3B in this planning
phase.** Phase 3B begins only when the user explicitly asks for it and
separately authorizes it.

---

## Cross-References

- [Phase 3B planning](phase-3b-planning.md)
- [Phase 3B scope freeze](phase-3b-provider-readonly-scope-freeze.md)
- [Phase 3B provider selection matrix](phase-3b-provider-selection-matrix.md)
- [Phase 3B API-key & secret strategy](phase-3b-api-key-and-secret-strategy.md)
- [Phase 3B network boundary](phase-3b-network-boundary.md)
- [Phase 3B request / response schema](phase-3b-provider-request-response-schema.md)
- [Phase 3B audit model](phase-3b-provider-audit-model.md)
- [Phase 3B failure / timeout / retry policy](phase-3b-failure-timeout-retry-policy.md)
- [Phase 3B cost / rate-limit policy](phase-3b-cost-and-rate-limit-policy.md)
- [Phase 3B security risk register](phase-3b-security-risk-register.md)
- [Phase 3B GO / NO-GO](phase-3b-go-no-go.md)
- [Phase 3B execution brief](phase-3b-execution-brief.md)
