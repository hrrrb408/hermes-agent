# Phase 2 Final Capability Map

## Document Information

| Field | Value |
|-------|-------|
| Phase | 2 (final) |
| Title | Phase 2 Final Capability Map |
| Status | Functionally complete |
| Date | 2026-06-15 |
| Branch | `dev-huangruibang` |
| Planning ID | `PHASE-3-PLANNING-001` |

> This map consolidates the Phase 2 capability chain that Phase 3 builds on.
> Phase 2 is **functionally complete for dev-only controlled tool execution
> and auditability.** Companion: [phase-2-to-phase-3-transition.md](phase-2-to-phase-3-transition.md).

---

## 1. Capability Chain

```
Read-only Tools (2A)
  → Provider Fake Round-trip (2B)
    → Sandbox Write (2C)
      → Rollback (2C-H1)
        → Durable Audit Store / Indexing (2D)
          → Audit Store Hardening (2D-H1)
            → Unified Dev Console (2E)
              → Frontend UX Hardening (2E-H1)
```

---

## 2. Per-Phase Capability

### Phase 2A — Real Tool Execution MVP (read-only)

- **What:** read-only multi-tool execution through the controlled chain.
- **Tools:** `clarify`, `tool_policy_read`, `route_governance_read`,
  `audit_events_read`, `dev_environment_read`, `release_status_read`
  (`STATIC_ALLOWLIST` frozen at six read-only tools).
- **Surface:** `POST /tools/dry-run` + `POST /tools/execute` (read-only) +
  `GET /tools/audit-events`.
- **Invariants:** every tool per-tool audited + read-only proven; no write;
  no provider; no shell.

### Phase 2A-H1 — Hardening (adversarial-review closure)

- **What:** deterministic 7-lens hardening audit replacing the unstable
  agent-only adversarial review.
- **Deliverables:** `tests/test_dev_web_phase_2a_hardening_boundaries.py` +
  `scripts/run-dev-webui-phase2a-hardening-audit.sh`.
- **Result:** 7 / 7 lenses PASS, 0 P0, 0 P1.

### Phase 2B — Provider Schema / API Controlled Integration

- **What:** controlled provider round-trip with a deterministic **fake**
  provider (offline); real provider adapter present but **blocked by default**.
- **Modes:** `disabled` (default), `fake` (offline, deterministic), `real`
  (blocked unless every eligibility condition holds, and even then no network
  call is wired in Phase 2B).
- **Surface:** reuses `POST /tools/execute` with `mode=provider_roundtrip`
  (no new route).
- **Invariants:** provider write preview-only; `externalNetworkCalled=false`
  on all paths; provider UI never accepts an API key.

### Phase 2B-H1 — Provider Round-trip Hardening

- **What:** 8-lens hardening; PEM private-key pattern widened to every variant;
  secret-field stems broadened (`apikey` / `privatekey` / `credential`).
- **Result:** 0 P0, 0 P1; transient flake closed as non-reproduced.

### Phase 2C — Controlled Tool Write Execution

- **What:** dev-sandbox write tools behind a separate allowlist + a two-phase
  (plan/preview → confirm/execute) chain, gated by
  `HERMES_TOOL_WRITE_EXECUTION_ENABLED`.
- **Tools:** `dev_sandbox_file_write`, `dev_sandbox_file_append`,
  `dev_sandbox_file_patch`, `dev_sandbox_file_readback`.
- **Surface:** reuses `POST /tools/dry-run` (`mode=write_preview`) +
  `POST /tools/execute` (`mode=write`) (no new route).
- **Rollback:** rollback manifest generated at write time.
- **Invariants:** writes only inside the dev sandbox; provider write
  preview-only and never auto-executes.

### Phase 2C-H1 — Write Execution Hardening

- **What:** automatic rollback execution + file-backed confirmation-token TTL.
- **Tools:** `dev_sandbox_rollback_execute`.
- **Stores:** `dev_web_confirmation_store.py` (file-backed token, TTL, scope +
  digest binding, persistent single-use replay protection),
  `dev_web_write_rollback_store.py` (manifest save/load/validate).
- **Surface:** reuses `mode=rollback_preview` / `mode=rollback` (no new route).

### Phase 2D — Advanced Audit Storage / Indexing (Durable Dev Audit Store)

- **What:** dev-only durable audit store at
  `$HERMES_HOME/gateway/dev/audit-store`.
- **Components:** canonical `audit_schema_v2`; unified audit sanitizer (closes
  the Phase 2A `str(object)` gap); append-only durable writer (file lock +
  on-disk sequence floor); audit index (build/update/rebuild/repair); opaque
  cursor pagination (legacy offset kept); filters + safe substring search;
  rotation by size / count; corruption detection + quarantine (non-destructive);
  legacy → canonical dual-write bridge (7 audit kinds); enhanced Audit Viewer
  (store-mode toggle, status badges).

### Phase 2D-H1 — Audit Storage Hardening

- **What:** 10-lens hardening (schema, sanitizer, append-only consistency,
  index, cursor query, rotation/recovery, corruption quarantine, legacy
  dual-write, no-leak API, production isolation); one latent fix
  (`_minimal_safe_event` `sequence: -1` → `0`).
- **Result:** 10 / 10 lenses PASS, 0 P0, 0 P1.

### Phase 2E — Frontend UX Polish (Unified Developer Console)

- **What:** unified developer console at `/#/console` — additive, zero
  regression. Seven first-class sections: Overview, Tool Execution, Provider
  Round-trip, Sandbox Write & Rollback, Audit Viewer, Safety Boundary,
  Diagnostics.
- **Cross-navigation:** `AuditIdLink` → `devConsoleNav.prefillAuditSearch`
  (switches section + store mode + filter + loads).
- **Invariants:** no backend change, no new route; frozen baselines
  (34/34/5/0/1/1, PID 28428) verified by gates, not fetched live.

### Phase 2E-H1 — Console UX Hardening

- **What:** 9-lens hardening; corrected the `blocked_write_forbidden_target` →
  `blocked_write_forbidden_path` catalogue drift + added 8 stable backend
  codes; updated frozen phase timeline (2E completed, 2E-H1 added); prefill
  marker rendered lossy; backend vocabulary pinned as a contract test.
- **Deliverables:** 6 vitest hardening files + 1 Playwright smoke spec +
  `phase2e_h1_frontend_ux_hardening` profile + 1 backend contract test +
  `scripts/run-dev-webui-phase2e-hardening-audit.sh`.
- **Result:** 9 / 9 lenses PASS, 0 P0, 0 P1.

---

## 3. Cross-Cutting Invariants (frozen)

| Invariant | Value |
|-----------|-------|
| Route governance | OpenAPI 34 / runtime 34 / Tool GET 5 / Tool write HTTP route 0 / dry-run 1 / execution 1 |
| Production Gateway PID | `28428` (count 1) |
| `STATIC_ALLOWLIST` | six read-only tools (per-tool audited) |
| Write allowlist | separate dev-sandbox write tools (gated) |
| Provider | disabled / fake only; real blocked |
| WebUI bind | `127.0.0.1` only |
| `~/.hermes` / production `state.db` | never accessed |
| Secrets / tokens / hashes / raw args / callable repr | never exposed |
| Audit / token / rollback-manifest / runtime JSONL / `.claude/` | never committed |
| Force push / rebase / `git reset --hard` | never attempted |

---

## 4. Carry-Forward P2 (non-blocking)

Real-vendor provider call; token encryption at rest; multi-user namespace;
audit retention deletion / compression / encryption at rest; advanced
full-text indexing; full WCAG 2.1 AA; advanced visual / motion polish; provider
streaming; future Production Gateway PID drift. None block Phase 3.

---

## 5. Conclusion

Phase 2 is functionally complete. The Dev WebUI can demonstrably and
auditably execute read-only tools, run a controlled fake provider round-trip,
perform a sandbox write + rollback under confirmation, and inspect the result
through a durable audit store inside a unified console — all dev-only, with
unchanged route governance and an untouched Production Gateway.
