# Phase 2E-H1 — Console Workflow Review

**Review ID:** `CONSOLE-WORKFLOW-2E-H1-001`
**Scope:** The five first-class console workflows as observed inside the unified
developer console (`/#/console`) after the Phase 2E-H1 hardening.

This review traces each workflow from entry to its terminal state and confirms
state transitions are coherent, no workflow loses state or misleads the operator,
and every blocked outcome degrades to a safe, human-readable explanation.

## Top-level flow

```
/#/  (3-column chat workbench, unchanged)
  └── TopStatusBar "Dev Console" link
       └── /#/console  (DevConsoleLayout: top bar + nav rail | content)
            ├── Overview        (read-only GETs + frozen baseline)
            ├── Tool Execution  (dry-run → confirm → execute)
            ├── Provider        (fake round-trip; real blocked)
            ├── Write & Rollback (preview → confirm → execute → rollback)
            ├── Audit Viewer    (store filters + cursor pagination)
            ├── Safety Boundary (frozen invariants + live flags)
            └── Diagnostics     (frozen environment + release status)
```

The nav rail is a vertical `role="tablist"` with roving tabindex; ArrowUp/Down,
Left/Right, Home, End move selection and focus. The active section persists to
localStorage and is restored on entry; an invalid persisted value falls back to
Overview. Each section is wrapped in `<KeepAlive>` so shared store state survives
switches.

## Read-only execution flow

```
ToolExecutionSection → ToolExecutePanel
  tool select → dry-run (POST /tools/dry-run) → confirmation
  → execute (POST /tools/execute) → executeResult
  → cross-reference strip: post-exec audit · pre-exec audit · execute request · dry-run request
       └── AuditIdLink @navigate → devConsoleNav.prefillAuditSearch(id)
            → audit section + store mode + search filter + loadStoreEvents()
```

Verified: a completed execute surfaces all four correlation ids; a null result
shows no strip (clean empty state). Default gates block before any handler call;
the provider schema is never sent. Pinned by `phase2e-h1-workflow-continuity`.

## Provider flow

```
ProviderSection → ProviderRoundtripPanel
  mode select (disabled / fake) → runProviderRoundtrip (POST /tools/execute mode=provider_roundtrip)
  → result { blockedReason?, providerAuditIds[] }
  → BlockedReasonPanel (if blocked) + provider-audit cross-reference strip
```

Verified: a blocked real-mode round-trip renders the unified panel ("Real
provider blocked") whose action never suggests bypass; a completed fake
round-trip surfaces the provider-audit cross-references and no blocked panel.
The UI never accepts an API key. Pinned by `phase2e-h1-workflow-continuity`.

## Write flow

```
WriteRollbackSection → ToolWritePanel
  tool + sandbox-relative target → preview (POST /tools/dry-run mode=write_preview)
  → confirmation → execute (POST /tools/execute mode=write) → executeResult { rollbackId, audits }
  → cross-reference strip: rollback manifest · write post/pre-exec audit
```

Verified: an executed write surfaces the rollback manifest + write audit ids; a
`blocked_write_forbidden_path` block renders the unified panel under its **real**
backend code (Phase 2E-H1 corrected the prior `…_forbidden_target` drift).
Writes operate only inside the dev sandbox and require
`HERMES_TOOL_WRITE_EXECUTION_ENABLED`. Pinned by `phase2e-h1-workflow-continuity`.

## Rollback flow

```
WriteRollbackSection → rollback manifest id input
  → preview (POST /tools/dry-run mode=rollback_preview)
  → confirmation → execute (POST /tools/execute mode=rollback) → rollbackResult { audits }
  → cross-reference strip: rollback post/pre-exec audit
  → BlockedReasonPanel (danger) on hash mismatch
```

Verified: an executed rollback surfaces the rollback audit ids; a
`blocked_rollback_current_hash_mismatch` renders the danger panel ("Current hash
mismatch") with the non-color severity badge. Rollback reuses the write gate.
Pinned by `phase2e-h1-workflow-continuity`.

## Audit flow

```
AuditViewerSection → AuditViewerPanel (Phase 2D durable store)
  store-mode toggle → kind / status / provider-mode / write-required / search filters
  → opaque cursor pagination → sanitized event detail
  + prefill marker (lossy) when reached via cross-navigation → clear button
```

Verified: the prefill marker is rendered lossy (the full id lives only in the
store as the active filter); clearing removes it; no prefill → no marker. Raw
tokens / full hashes / raw arguments / callable reprs are never surfaced — every
event is sanitized before display. Pinned by `phase2e-h1-audit-cross-navigation`.

## Safety Boundary flow

```
SafetySection
  SafetyBadgeBar (all invariants) + grouped badges (production / environment /
  route / provider / write / audit) + frozen route-governance baseline
  (34/34/5/0/1/1) + production isolation (PID 28428 read-only) + live policy flags
```

The badges are frozen invariants (guarantees), not live probes. Live safety
flags come from `GET /tools/policy`; governance/PID numbers are the frozen
baseline verified by gates. The console never acts on the production instance.

## Cross-navigation review

`devConsoleNav.prefillAuditSearch(id)` is the keystone "回链": it switches to the
audit section, enables store mode, sets the search filter, **and fires
`loadStoreEvents`** — setting a filter alone is not enough (the panel only
queries from onMounted / Apply / pagination). `AuditIdLink` chips emit the full
id (display is lossy); every result surface (execute / write / rollback /
provider / overview recent events) wires `@navigate` to the bridge.

## Blocked reason review

The `blockedReasons.ts` catalogue now covers every STABLE backend blocked-reason
code (literal constant strings). The prior `blocked_write_forbidden_target` key
was dead (the backend emits `blocked_write_forbidden_path`); it is corrected.
Unknown / dynamic codes (f-strings, message phrases) degrade to the safe
`UNKNOWN_FALLBACK`, which never suggests bypassing a boundary. The backend
vocabulary is pinned by `tests/test_dev_web_phase_2e_h1_frontend_contract.py`
so frontend/backend drift is caught at the Python level.
