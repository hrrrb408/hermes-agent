# Phase 3B Security Risk Register

## Document Information

| Field | Value |
|-------|-------|
| Phase | 3B Planning |
| Title | Phase 3B Security Risk Register (P0 / P1 / P2) |
| Status | Recorded |
| Date | 2026-06-16 |
| Branch | `dev-huangruibang` |
| Planning ID | `PHASE-3B-PLANNING-001` |
| Risk-Register ID | `PHASE-3B-RISK-REGISTER-001` |

> Companion to [phase-3b-planning.md](phase-3b-planning.md). This register covers
> the **future** Phase 3B implementation (Real Provider Read-only Controlled
> Integration). None of these risks is introduced by this planning phase — this
> is docs-only. The real provider remains blocked by default after this phase.

Each risk follows: ID · Severity · Description · Impact · Mitigation · Risk
owner · Gate · Blocking condition.

---

## 1. P0 Risks (block / stop immediately)

### R3B-P0-01 — Real provider enabled without authorization

- **Severity:** P0
- **Description:** A Phase 3B change wires or enables a real provider call when
  only disabled / fake is authorized, or makes a real call without all
  eligibility conditions.
- **Impact:** Unauthorized network call, real cost, prompt-injection exposure.
- **Mitigation:** Real provider disabled by default; eligibility gate requires
  `HERMES_PROVIDER_API_ENABLED=1` + `HERMES_PROVIDER_MODE=real` + key present +
  dev home + production gate + allowlisted base URL. Smoke uses fake + blocked-real.
- **Gate:** provider contract tests + smoke.
- **Blocking condition:** any `externalNetworkCalled=true` outside an explicitly
  authorized real round-trip.

### R3B-P0-02 — API-key leak

- **Description:** A Phase 3B surface renders, logs, audits, commits, or accepts
  via the UI a provider API key.
- **Impact:** Secret leak; unauthorized spend; account compromise.
- **Mitigation:** Key is env-only; never UI; sanitizer redacts `sk-…` / `Bearer …`
  / Authorization / PEM / forbidden stems; the no-leak test must fail the build.
- **Gate:** no-leak test + boundary search.
- **Blocking condition:** any key value rendered / logged / committed / in UI.

### R3B-P0-03 — Secret in audit / log / response

- **Description:** A raw prompt or response containing a secret reaches the audit
  store, a log, or the UI.
- **Impact:** Secret leak.
- **Mitigation:** Response is normalized to a bounded `contentSummary`; sanitizer
  re-redacts every audit event; oversize → blocked; secret-detected → blocked.
- **Gate:** no-leak test + audit redaction tests.
- **Blocking condition:** any secret in audit / log / response / UI.

### R3B-P0-04 — Prompt-injection-driven tool call

- **Description:** A provider response manipulates the system into executing a
  disallowed tool call or an arbitrary URL fetch.
- **Impact:** Unauthorized tool execution / data exfiltration.
- **Mitigation:** Every provider tool call is validated against the read-only
  `STATIC_ALLOWLIST`; write / shell / db / external-http calls are blocked;
  provider-requested URL fetch is blocked.
- **Gate:** tool-call validation tests.
- **Blocking condition:** any non-allowlisted / write / arbitrary-URL call
  executed.

### R3B-P0-05 — Arbitrary-URL fetch

- **Description:** A Phase 3B change allows fetching an arbitrary URL (SSRF).
- **Impact:** Data exfiltration / internal service probing.
- **Mitigation:** Base-URL allowlist only; `https://` only; redirects off the
  allowlist blocked; provider / tool URL fetch blocked.
- **Gate:** network-boundary tests.
- **Blocking condition:** any non-allowlisted URL fetched.

### R3B-P0-06 — Provider write / auto-write / autonomous execution

- **Description:** A provider path executes a write, auto-writes, or runs an
  autonomous loop.
- **Impact:** Unauthorized mutation.
- **Mitigation:** Provider write blocked (`blocked_provider_write_not_allowed`);
  no auto-write; single round-trip only; no autonomous agent.
- **Gate:** write / autonomy tests.
- **Blocking condition:** any provider-driven write / auto-write / autonomous run.

### R3B-P0-07 — Shell / database / external-service write

- **Description:** A Phase 3B change introduces shell, DB mutation, or external
  service write beyond the single provider HTTPS call.
- **Impact:** Arbitrary execution / state corruption / exfiltration.
- **Mitigation:** Boundary search rejects `subprocess` / `os.system` /
  `shell=True` / `sqlite3` mutations / `requests.post` / `httpx` / `urllib` /
  `aiohttp` / `curl` outside the single provider call.
- **Blocking condition:** any such execution / mutation introduced.

### R3B-P0-08 — Route governance drift

- **Description:** A Phase 3B change adds an HTTP route, a Tool write HTTP route,
  or a Provider route without explicit separate authorization.
- **Impact:** Surface / boundary drift.
- **Mitigation:** Default is "no new route"; the real round-trip reuses the
  existing `mode`-branched routes. Any change must be explicitly approved +
  recorded.
- **Gate:** `test_dev_check_webui.py` + `test_dev_web_0c06_closure.py`.
- **Blocking condition:** OpenAPI / runtime route count drifts from 34 / 34.

### R3B-P0-09 — Production rollout / non-loopback bind

- **Description:** A Phase 3B change binds to a non-loopback interface or rolls
  out to production.
- **Impact:** Production exposure.
- **Mitigation:** WebUI binds to `127.0.0.1` only; dev `HERMES_HOME` enforced.
- **Blocking condition:** any production rollout or `0.0.0.0` bind.

### R3B-P0-10 — `~/.hermes` / production `state.db` access

- **Description:** A Phase 3B change reads / writes `~/.hermes` or the production
  `state.db`.
- **Impact:** Production instance / state touched.
- **Mitigation:** `enforce_dev_environment()` allowlist; audit path resolver
  rejects the production home and any `state.db` path.
- **Blocking condition:** any `~/.hermes` / production `state.db` access.

### R3B-P0-11 — Production Gateway stopped / restarted / replaced / signaled / PID drift

- **Description:** A Phase 3B change touches the Production Gateway, or the PID
  drifts from `28428`.
- **Impact:** Production messaging outage.
- **Mitigation:** Dev WebUI never controls the production gateway; pre/post
  production-safety checks pin PID `28428` and count `1`.
- **Blocking condition:** PID != `28428` or count != `1` at any check.

### R3B-P0-12 — Runtime artifact commit

- **Description:** A Phase 3B change stages / commits an audit / token /
  rollback-manifest / cost-counter / runtime-audit-JSONL file or `.claude/`.
- **Impact:** Secret / state leak into the repository.
- **Mitigation:** Boundary search rejects these paths; `.gitignore` coverage
  verified.
- **Blocking condition:** any such artifact staged.

---

## 2. P1 Risks (block push until resolved)

### R3B-P1-01 — Retry storm / timeout misconfiguration

- **Description:** Timeouts are unbounded or retries exceed the cap.
- **Impact:** Cost runaway / availability hit.
- **Mitigation:** Bounded connect / read / total timeouts; hard retry cap;
  non-retryable classes short-circuit.
- **Gate:** failure / timeout / retry tests.

### R3B-P1-02 — Rate-limit bypass

- **Description:** The per-minute / daily caps can be bypassed by concurrency or
  counter races.
- **Impact:** Overspend.
- **Mitigation:** Atomic, single-generation-per-session-style counters; fail-closed
  on unreadable counters.
- **Gate:** cost / rate-limit tests.

### R3B-P1-03 — Budget-cap bypass

- **Description:** The daily budget / token cap is not enforced before the call.
- **Impact:** Overspend.
- **Mitigation:** Cost estimate before call; estimate-over-budget → blocked;
  audited.
- **Gate:** cost policy tests.

### R3B-P1-04 — Response-size DoS

- **Description:** A huge provider response exhausts memory.
- **Impact:** Availability hit.
- **Mitigation:** Max response byte size; oversize → aborted + blocked.
- **Gate:** response-size tests.

### R3B-P1-05 — Audit gap

- **Description:** A real round-trip terminates without a terminal audit event.
- **Impact:** Loss of traceability.
- **Mitigation:** Every round-trip emits exactly one terminal event; coverage
  test asserts it.
- **Gate:** audit coverage tests.

### R3B-P1-06 — Redaction regression

- **Description:** A new field or payload shape escapes the sanitizer.
- **Impact:** Secret leak.
- **Mitigation:** Reuse the Phase 2B-H1 widened patterns; extend the forbidden
  stems; parametrized no-leak tests across the real surface.
- **Gate:** redaction / no-leak tests.

### R3B-P1-07 — Response normalization drift

- **Description:** The real adapter envelope shape drifts from the fake adapter
  envelope shape.
- **Impact:** Contract tests pass offline but fail / misbehave on the real path.
- **Mitigation:** Both adapters produce the same envelope shape; contract tests
  assert against the envelope, not the wire payload.
- **Gate:** schema contract tests.

### R3B-P1-08 — Smoke consumes real budget

- **Description:** The smoke profile accidentally makes a real call.
- **Impact:** Real spend in CI.
- **Mitigation:** Smoke uses fake + blocked-real only; explicit assertion that
  no real call is made.
- **Gate:** smoke profile.

### R3B-P1-09 — UI shows raw failure / stack trace

- **Description:** A failure surfaces a raw stack trace or raw body in the UI.
- **Impact:** Internal exposure / poor UX.
- **Mitigation:** Safe blocked / error state with a `blocked_provider_*` reason;
  no raw stack / body / header.
- **Gate:** UI no-leak + failure tests.

---

## 3. P2 Risks (recorded, non-blocking)

### R3B-P2-01 — Streaming deferred

- The first implementation is non-streaming; streaming is a separately
  authorized later slice.

### R3B-P2-02 — Multi-provider routing deferred

- A single adapter at a time; routing across providers is deferred.

### R3B-P2-03 — Provider write deferred

- Provider write is out of Phase 3B entirely; a separately authorized phase owns
  it.

### R3B-P2-04 — Token encryption at rest deferred

- Confirmation tokens remain file-backed; encryption at rest is future work.

### R3B-P2-05 — Multi-user namespace deferred

- Single-user dev namespace only.

### R3B-P2-06 — Full WCAG deferred

- Phase 3B inherits the Phase 2E-H1 practical accessibility baseline.

### R3B-P2-07 — Future Production Gateway PID drift

- Smoke harness fails closed; an authorized refresh phase updates the constant.

---

## 4. Summary

| Tier | Count | Blocks Phase 3B implementation? |
|------|-------|---------------------------------|
| P0 | 12 | Each is a stop condition; none is introduced by this planning phase |
| P1 | 9 | Block push until resolved (during a future 3B execution phase) |
| P2 | 7 | Non-blocking; recorded for sequencing |

---

## 5. Cross-References

- [Phase 3B planning](phase-3b-planning.md)
- [Phase 3B scope freeze](phase-3b-provider-readonly-scope-freeze.md)
- [Phase 3B read-only provider threat model](phase-3b-readonly-provider-threat-model.md)
- [Phase 3B redaction & no-leak policy](phase-3b-provider-redaction-and-no-leak-policy.md)
- [Phase 3B GO / NO-GO](phase-3b-go-no-go.md)
- [Phase 3 risk register](phase-3-risk-register.md) (program-wide baseline)
