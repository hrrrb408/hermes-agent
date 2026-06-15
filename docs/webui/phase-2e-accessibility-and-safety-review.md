# Phase 2E — Accessibility & Safety Review

## Scope

Phase 2E introduces the unified developer console (`/#/console`). This review
covers the accessibility baseline and the safety boundary for the new surface.
Phase 2E is frontend-only polish — it adds no backend capability and must not
drift any safety invariant.

## Accessibility

The console targets a practical, keyboard-operable baseline (not full WCAG
certification — that is a deferred P2 item). What is in place:

### Keyboard operability
- The left nav rail is a `role="tablist"` (vertical) with **roving tabindex**:
  the active section is `tabindex=0`, others `-1`. ArrowUp/Down/Left/Right,
  Home, and End move selection and focus (`#devconsole-nav-{section}`).
  Verified by `phase2e-accessibility.spec.ts`.
- The reused panels inherit their existing keyboard support (e.g. the audit
  kind tabs, the tool-policy sub-tabs, the catalog listbox). Phase 2E does not
  regress them.
- Every interactive element is a real `<button>` / `<select>` / `<input>` with
  an accessible name (visible label, `aria-label`, or `aria-labelledby`).

### State announcements
- `LoadingState`: `role="status"`, `aria-busy="true"`, `aria-live="polite"`.
- `ErrorState`: `role="alert"`.
- `BlockedReasonPanel`: `role="alert"` with a severity badge (not color-only —
  the severity label "Info / Caution / Blocked" is text).
- `AuditIdLink`: `aria-label="Jump to audit viewer for {label} {id}"`.

### Non-color redundancy
- Safety badges carry text labels (e.g. "Real provider blocked") in addition to
  tone; the Overview summary cards use a `data-tone` attribute plus a textual
  value, so status is not conveyed by color alone.
- Blocked-reason severity is rendered as both a colored badge and a text word.

### Responsive layout
- `devconsole.css` collapses the two-pane layout to a single column below
  820px: the nav rail becomes a horizontal wrap and the content stacks beneath.
- The content area scrolls; long JSON / diffs remain in scrollable `<pre>`
  blocks (`overflow-x: auto`) — no horizontal page overflow from the console.

### Reduced motion
- Transitions use the existing `--transition-fast` token; `prefers-reduced-motion`
  is honored by the theme system the console inherits.

### Deferred (P2)
Full WCAG 2.1 AA audit, focus-trap management for the future audit-event detail
drawer, screen-reader flow testing across all five themes.

## Safety

### No new backend capability
- No new HTTP route. Verified by `test_dev_web_phase_2e_frontend_contract.py`
  (OpenAPI 34, no provider route, no dedicated tool-write HTTP route).
- No tool execution is triggered by the Overview / Safety / Diagnostics
  sections. The Overview sources from read-only GETs (`/tools/policy`,
  `/tools/audit-events`) + frozen constants. `phase2e-overview.spec.ts` asserts
  that no dry-run / execute / write / provider API is called on mount.
- The console does **not** execute `route_governance_read` /
  `dev_environment_read` / `release_status_read` live — those would consume
  confirmation tokens and pollute the audit trail. Frozen baselines are verified
  by the smoke preflight + backend invariant tests.

### No data leakage
- The UI never renders API keys, raw tokens, full token hashes, raw arguments,
  secrets, callable/function reprs, or production paths. Asserted across all
  sections by `phase2e-accessibility.spec.ts` and `phase2e-overview.spec.ts`,
  and across the Overview data sources by the backend contract test.
- `AuditIdLink` truncates ids (lossy by design); the full id is only emitted as
  a navigation payload, never displayed at length.
- The blocked-reason catalogue (`blockedReasons.ts`) never suggests bypassing a
  boundary — `phase2e-foundations.spec.ts` asserts no safe-action instructs a
  bypass.

### Production isolation
- No `~/.hermes` access, no production `state.db` access, no production rollout.
- The console binds to `127.0.0.1` only (dev API 5181 / dev WebUI 5180).
- The frozen production PID baseline (28428) is displayed read-only; the smoke
  harness fails closed if the live PID drifts. The console never signals,
  stops, restarts, or replaces the production Gateway.

### Reused-panel safety preserved
- The reused panels (`ToolExecutePanel`, `ProviderRoundtripPanel`,
  `ToolWritePanel`, `AuditViewerPanel`) are mounted unmodified inside console
  section wrappers, so every existing safety guard (target-path validation,
  confirmation-token gating, rollback hash checks, audit redaction) is intact.
  The `<KeepAlive>` wrapper preserves their shared store state across switches
  without resetting it.

## Boundary search results (pre-commit)

| Check | Result |
|---|---|
| Runtime artifacts in diff | none |
| Real secrets in diff | none (safety terms only in docs/tests/negative assertions) |
| Dangerous execution (`subprocess`/`os.system`/`sqlite3`/…) | none introduced |
| Production access (`~/.hermes`, production `state.db`) | none |
| Frontend leak (`rawArguments`/`fullTokenHash`/`plainToken`/callable repr) | none |
| `.claude/`, audit-store, token-store, rollback-manifest, audit JSONL committed | none |

## Conclusion

Phase 2E improves the developer-console accessibility baseline and introduces
no safety-boundary expansion. Route governance stays 34/34/5/0/1/1 and the
production gateway PID 28428 is untouched. No P0 or P1 safety issues.
