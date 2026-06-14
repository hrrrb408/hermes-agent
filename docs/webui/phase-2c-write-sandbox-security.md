# Phase 2C — Write Sandbox Security

## Sandbox root

`get_dev_write_sandbox_root()` resolves to
`$HERMES_HOME/gateway/dev/tool-write-sandbox`. The dev-home gate is
**fail-closed against the production home** (`/Users/huangruibang/.hermes`) and
requires a non-empty `HERMES_HOME`. Any other non-production home is accepted
(including the real dev home and test tmp dirs); the dev-home *identity* is
additionally enforced by the Dev WebUI server's environment guard.

## Path validation

`validate_sandbox_target_path()` enforces, in order:

1. **Relative only** — rejects `/abs`, `~/x`, `back\slash`, NUL, shell
   metacharacters, leading/trailing whitespace.
2. **No traversal** — rejects any `..` or `.` segment.
3. **Depth / length** — path depth ≤ 5, filename ≤ 120 chars.
4. **File type** — only `.txt/.md/.json/.yaml/.yml/.csv`.
5. **Forbidden substrings** — `.env`, `.claude`, `.git`, `.db`, `.sqlite`,
   `.jsonl`, `.log`, `test-results`, `playwright-report`, `node_modules`,
   `/dist/`, `/build/`, `state.db`.
6. **Symlink escape** — `Path.resolve()` follows symlinks; the resolved target
   must be strictly inside the resolved sandbox root.

## Size + binary limits

- single write payload ≤ 64 KiB (`MAX_SINGLE_WRITE_BYTES`)
- file after write ≤ 256 KiB (`MAX_FILE_AFTER_WRITE_BYTES`)
- binary detection: NUL byte anywhere, or any C0 control character (other than
  `\n`/`\r`/`\t`) in the first 1024 chars.

## Safe IO primitives

All writes use an **atomic** temp-file + `os.replace` inside the sandbox:

- `safe_write_text` (create-or-replace), `safe_append_text`,
  `safe_apply_patch` (single-occurrence find-and-replace),
  `safe_read_text`, `readback_summary`.
- `compute_sha256_text`, `build_diff_preview` (bounded unified diff).

## Guarantees

No write can occur outside the sandbox. Path traversal, symlink escape,
forbidden files, oversized content, binary content, production paths,
`~/.hermes`, production `state.db`, `.env`, `.claude`, runtime audit JSONL,
logs, and database files are all blocked. No shell, no subprocess, no sqlite,
no network — verified by source inspection in
`tests/test_dev_web_phase_2c_write_security.py`.
