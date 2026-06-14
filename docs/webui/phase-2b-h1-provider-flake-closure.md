# Phase 2B-H1 — Provider / Audit Redaction Transient Flake Closure

| Field | Value |
|-------|-------|
| Closure ID | `PROVIDER-FLAKE-CLOSURE-2B-H1-001` |
| Hardening ID | `HARDENING-2B-H1-001` |
| Date | 2026-06-14 |
| Status | Closed — non-reproduced with deterministic evidence |

---

## 1. Original transient flake

During one parallel backend run at the end of Phase 2B, a single test failed
once and then passed on every re-run and in isolation:

```
test_audit_jsonl_no_secret_or_repr[audit_events_read-R1]
```

Observed count: **545 / 546** (one failure among ~546 tests). It was recorded
in the Phase 2B round-trip test report as a pre-existing high-parallelism
flake, not a Phase 2B regression (Phase 2B does not modify the dry-run /
pre-execution / post-execution audit writers this test inspects).

## 2. Test mechanics

`tests/test_dev_web_phase_2a_hardening_boundaries.py ::
 test_audit_jsonl_no_secret_or_repr`:

1. Runs the `audit_events_read` read-only tool to completion into a per-test
   `tmp_path` hermes-home.
2. Reads `tool-dry-run-audit.jsonl`, `tool-pre-execution-audit.jsonl`, and
   `tool-post-execution-audit.jsonl` from that per-test audit dir.
3. Asserts none contain `Bearer `, `BEGIN PRIVATE KEY`, `sk-`, `<function`,
   `<bound method`, or `object at 0x`.

## 3. Observed context

- `pytest-xdist` is **not** installed in this environment, so the original
  "high parallelism" came from `scripts/run_tests.sh`'s per-file subprocess
  pool (`run_tests_parallel.py`, default `-j 28`).
- Each test file runs in its own `python -m pytest <file>` subprocess; within
  a file, tests run sequentially in one process.
- `tmp_path` is unique per test even across parallel subprocesses.

## 4. Reproduction attempt

### 4.1 Repeated deterministic reruns (30 runs)

| Regime | Command | Result |
|--------|---------|--------|
| Isolated variant ×10 | `run_tests.sh ... -k "test_audit_jsonl_no_secret_or_repr and audit_events_read"` | **10/10 pass** |
| Full hardening file ×10 | `run_tests.sh tests/test_dev_web_phase_2a_hardening_boundaries.py -- -q` | **10/10 pass** |
| High-parallelism batch ×10 | `run_tests.sh` over 8 audit + hardening files (default `-j 28`) | **10/10 pass** |

### 4.2 Repeated Phase 2B audit / hardening checks (10 runs)

`tests/test_dev_web_phase_2b_provider_audit.py` +
`tests/test_dev_web_phase_2b_hardening_boundaries.py`, ×10 → **10/10 pass**.

### 4.3 High-parallelism note

`pytest-xdist` is unavailable; the wrapper's per-file subprocess parallelism
(`-j 28`) was used as the high-parallelism condition, matching how the original
flake was observed. No new dependency was installed.

## 5. Root-cause analysis (no leak path exists)

An independent adversarial investigation traced every audit write/read path and
confirmed there is **no code path** by which any of the six forbidden fragments
can enter the audit JSONL files:

1. **Path isolation is sound.** Every writer/reader resolves the audit path
   purely functionally from the explicitly-passed `hermes_home` (no module-level
   cache, no `lru_cache`, no env mutation). Two parallel subprocesses with
   different `tmp_path` values get different audit files.
2. **No `default=` handler.** All three writers serialize via bare
   `json.dumps(..., ensure_ascii=False, separators=(",", ":"))`. A
   non-serializable object would raise `TypeError` → caught → fail-closed (no
   line written). There is no path that can render `<function`, `<bound method`,
   or `object at 0x`.
3. **All event fields are JSON-native.** The dry-run / pre / post audit
   packages are built from `str`/`int`/`bool`/`None`/`list`/`dict` only.
4. **The dry-run line in this test is written directly** by the test helper
   (`open(..., "a")` + `json.dumps(event)`), bypassing the dry-run writer's
   defense-in-depth `str(value)` fallback, so even that latent fallback is not
   on this path.
5. **No read/write race within a test.** `run_read_only_tool_to_completion`
   runs fully synchronously before the test reads the files back.

## 6. Result

**Reproduced: no.** The single observed failure had no preserved detail (which
fragment matched, which file) and passed on every immediate re-run. Its
signature is that of a transient harness/OS-level artifact under heavy I/O
pressure from N parallel subprocesses — not a sanitizer gap or a secret leak.

## 7. Root cause if reproduced

N/A — not reproduced.

## 8. Fix if applied

No fix was required for the flake itself. However, the adversarial review
performed alongside the flake hunt surfaced a **separate, real** latent gap in
the provider audit sanitizer (the PEM private-key value pattern matched only
bare/RSA — and the schema-module copy matched no standard header at all — and
suffixed secret field names escaped). That gap is **not** the flake (the flake
inspects the Phase 2A audit writers, which have no leak path), but it is in the
same Lens 6 domain and was fixed under `HARDENING-2B-H1-001`:

- PEM value pattern widened to `-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----` across
  all four provider modules.
- `_is_forbidden_field` substring stems broadened (`apikey`, `privatekey`,
  `credential`).

The Phase 2A dry-run sanitizer still has a `str(value)` defense-in-depth
fallback for unknown types; it is not reachable for the current JSON-native
event shape and is recorded as a Phase 2D residual (the Phase 2B provider
sanitizer is already hardened to `<non_json_value>`).

## 9. Closure decision

**Closed as non-reproduced** under `PROVIDER-FLAKE-CLOSURE-2B-H1-001`. The
closure is backed by deterministic, agent-independent evidence: a committed
8-lens hardening boundary test (including the `audit_events_read-R1` equivalent
scenario, parametrized 5× for stability) and a committed audit script that
re-runs the whole check with a PASS/FAIL verdict and a non-zero exit on failure.

A dead agent or a one-off OS hiccup can no longer leave the flake unclosed.

## 10. Residual risk

| Item | Note |
|------|------|
| Future high-parallelism recurrence | The committed repeated-run checks (10× + 5× in the audit script) would catch a recurrence; if it ever re-appears with a preserved failure detail, the dry-run sanitizer `str()` fallback is the prime suspect for a Phase 2D fix. |
| Phase 2A dry-run sanitizer `str()` fallback | Defense-in-depth only; not reachable for current event shapes; deferred to Phase 2D. |
