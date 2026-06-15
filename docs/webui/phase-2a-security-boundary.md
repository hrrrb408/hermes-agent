# Phase 2A — Security Boundary

## 1. Boundary Statement

Phase 2A admits **only read-only, side-effect-free inspection tools** to the
controlled-execution chain. Every Phase 2A tool is structurally read-only and
is individually audited + authorized. The Phase 1G controlled-execution chain
(dry-run → confirmation token → digest → pre-execution audit → handler lookup
→ dispatch → handler call → post-execution audit) is preserved exactly; only
the allowlist membership broadened from `{clarify}` to six read-only tools.

## 2. What Phase 2A Tools May Do

- Read in-process constants (policy inventory, route tables).
- Read dev-local files via containment-guarded readers
  (`dev_web_tool_audit_read` rejects `~/.hermes` and `state.db`).
- Read repo-local `docs/webui/` markdown basenames.
- Perform read-only process/port observation via bounded, `shutil.which`-guarded
  `ps` / `pgrep` / `lsof` (errors swallowed, output bounded).

## 3. What Phase 2A Tools Must NEVER Do

- Write files, mutate databases, or change any state.
- Send Provider Schema or call any Provider API (Phase 2B).
- Access `~/.hermes` or production `state.db`.
- Stop, restart, replace, or signal the production gateway.
- Execute arbitrary shell commands or user-supplied code.
- Make network calls.
- Expose raw tokens, full tokenHash, raw arguments, secrets, or callable reprs.

## 4. Enforcement Points

| Concern | Enforcement |
|---------|-------------|
| Allowlist membership | `STATIC_ALLOWLIST` (Gate 3) — single source of truth. |
| Risk tier | Inventory classifies tools R0/R1; Gate 6 blocks R2+. |
| Handler existence | `_SAFE_HANDLER_DESCRIPTORS` + `is_phase_2a_read_only_tool` dispatch guard. |
| Side effects | `_build_side_effect_flags` hardcodes all flags False; never overridden. |
| Argument safety | Registry strict-whitelist validator rejects forbidden/path/shell/secret input. |
| Production paths | `dev_web_tool_audit_read`, `_resolve_audit_path`, and the handler module reject `~/.hermes` / `state.db`. |
| Secret exposure | Three independent redaction layers (dry-run, digest, handler-call) + post-exec audit `_sanitize_event`. |
| Output bounds | 64 KiB serialized / 16 KiB agent / 8 KiB preview; handler `_truncate_result`. |
| Route governance | 34/34/5/0/1/1 frozen — Phase 2A added zero routes (asserted by tests + dev-check). |

## 5. Production Gateway Safety

`dev_environment_read` observes the production gateway PID via read-only `pgrep`
and compares against the approved baseline `1962` (Phase 1G-10A refreshed
value). It **only reports** drift as a warning — it never stops, restarts,
replaces, or signals the gateway. A future authorized refresh phase updates the
constant; Phase 2A does not.

The smoke harness `scripts/run-dev-webui-execute-audit-smoke.sh` independently
verifies PID 1962 (fail-closed) and is unchanged by Phase 2A.

## 6. Block Reasons (Preserved)

The Phase 1G block reasons all still fire:

- `blocked_tool_handler_call_not_enabled` — handler-call gate unset.
- `blocked_by_allowlist` — tool not in STATIC_ALLOWLIST.
- `blocked_digest_mismatch` — digest binding failure.
- `blocked_requires_confirmation_token` — token verify failed.
- `blocked_handler_call_not_clarify` — non-supported tool (not clarify, not a
  Phase 2A read-only tool) reached the handler-call gate.

## 7. Verification

- `tests/test_dev_web_phase_2a_security_boundaries.py` asserts every tool's
  safety profile, the production-PID baseline, no `~/.hermes`/`state.db` access
  in handler source, no secret/callable-repr leak, and the 34/34/5/0/1/1 route
  governance freeze.
- `tests/test_dev_web_phase_2a_read_only_execute.py` asserts the block reasons
  fire for unsupported tools, missing tokens, and digest mismatches.

## Phase 2D update — sanitizer gap closed

The Phase 2A dry-run sanitizer's `str(value)` fallback for unknown types is
**closed** by the Phase 2D unified audit sanitizer (`dev_web_audit_sanitizer.py`):
non-JSON-native values (callables, functions, objects, bytes, exceptions)
collapse to sentinels (`<non_json_value>`, `<bytes_redacted>`,
`<exception:ClassName>`) rather than a repr. This is now the single redaction
surface for every audit event entering the durable store. See
[phase-2d-audit-security-boundary](phase-2d-audit-security-boundary.md).
