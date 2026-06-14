# Phase 2B — Provider Round-trip Test Report

Status: **PASS**
Date: 2026-06-14

## 1. Scope

Verified the controlled Provider Schema / API round-trip end-to-end:
schema projection, mode gating, fake-provider determinism, tool-call
validation, full controlled-chain execution, audit, and the UI panel.

## 2. Backend tests (74 new Phase 2B tests, 1798 across the related regression)

| File | Coverage |
|------|----------|
| `test_dev_web_phase_2b_provider_schema.py` | exact allowlist tools; no write/provider tools; readOnly flags; boundary rejection; redaction; no callable/secret |
| `test_dev_web_phase_2b_provider_request.py` | disabled/fake/real gating; real blocked without env/key; allowedToolIds bounded; redaction; message bounding |
| `test_dev_web_phase_2b_fake_provider_adapter.py` | deterministic per-message routing for all 6 tools + clarify; finalize; offline; real adapter blocked even when enabled |
| `test_dev_web_phase_2b_provider_roundtrip.py` | per-tool fake round-trip completion; clarify round-trip; real/disabled blocked; unknown/write-like/malformed/secret/provider-recursive blocked; Phase 2A compatibility |
| `test_dev_web_phase_2b_provider_audit.py` | full lifecycle events; redactionApplied always true; no secret/key in audit; callable placeholder; production-path rejection |
| `test_dev_web_phase_2b_provider_security.py` | no API-key/secret/callable leak; externalNetworkCalled=false in fake; write tool never reachable; real blocked under partial enablement; route governance unchanged (no provider route, tool write = 0) |

Result: **0 failed**.

## 3. Frontend tests (708 pass)

New: `tool-provider-store.spec.ts` (8 tests), `tool-provider-panel.spec.ts`
(9 tests). The workspace-panel and accessibility tests were updated for the
new seventh `provider` workspace tab.

## 4. Route governance (frozen)

```
OpenAPI paths = 34
Runtime routes = 34
Tool GET = 5
Tool write = 0
Tool dry-run = 1
Tool execution = 1
```

No new route. The provider round-trip reuses `POST /tools/execute` with
`mode=provider_roundtrip`.

## 5. Compile / lint

- `compileall` on all 6 provider modules + `dev_web_api.py`: OK.
- `py_compile toolsets.py`: OK.
- `ruff check` on all provider modules + tests + dev-check tests: clean.
- Frontend `vue-tsc -b` (build) + `--noEmit` (type-check): OK.
- Frontend `eslint`: clean.

## 6. Smoke / E2E

`./scripts/run-dev-webui-execute-audit-smoke.sh all` — **Overall PASS**.

Profiles: `blocked` PASS, `completed` PASS, `phase2a` PASS,
`phase2b_provider_fake_roundtrip` PASS (6/6: API round-trip, tool-write
disabled, real blocked, audit queryable, UI panel visible, UI round-trip
renders).

Final state: Port 5180 free, Port 5181 free, Production Gateway PID 1962
unchanged.

## 7. Hermes gates

- `memory-check`: **PASS**.
- `dev-check`: **WARN** (Git worktree dirty pre-commit; resolves to clean
  except `.claude/` after commit). OpenAPI paths 34, Tool write 0, static
  allowlist unchanged.

## 8. Production safety

- Production Gateway PID 1962 unchanged; count 1; never stopped/restarted/
  replaced/signaled.
- No `~/.hermes` access; no production `state.db` access.
- No real Provider API call; no API key committed or exposed.

## 9. Known transient

During one parallel backend run, `test_audit_jsonl_no_secret_or_repr
[audit_events_read-R1]` failed once (545/546) then passed on every
re-run and in isolation. It inspects the dry-run/pre/post audit writers,
which Phase 2B does not modify; the failure did not reproduce. Recorded as
a pre-existing high-parallelism flake, not a Phase 2B regression.

## 10. Acceptance

Phase 2B Provider Schema / API Controlled Integration — **all gates green**.
