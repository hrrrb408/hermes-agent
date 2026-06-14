# Phase 2C — Write Tool Registry

## Allowlists

The write registry defines its **own** allowlist, disjoint from the frozen
Phase 1G/2A read-only allowlist:

```python
STATIC_WRITE_ALLOWLIST = frozenset({
    "dev_sandbox_file_write",
    "dev_sandbox_file_append",
    "dev_sandbox_file_patch",
    "dev_sandbox_file_readback",
})
STATIC_READ_ONLY_ALLOWLIST = <re-export of dev_web_tool_policy.STATIC_ALLOWLIST>  # frozen, 6 tools
UNIFIED_EXECUTABLE_ALLOWLIST = STATIC_READ_ONLY_ALLOWLIST | STATIC_WRITE_ALLOWLIST  # 10
```

`STATIC_ALLOWLIST` in `dev_web_tool_policy.py` is **never modified** — it
remains exactly the six read-only tools (verified at import time and by ~30
frozen test assertions). The unified view is a new, derived name.

## Tool definitions

Each `WriteToolDefinition` carries the write safety profile, enforced by an
import-time consistency check:

- `readOnly = False`, `writeRequired = True`
- `externalSideEffects = False`, `localSideEffects = True`
- `providerRequired = False`, `sideEffectScope = "dev_sandbox_filesystem"`
- `requiresConfirmation = True`, `requiresWriteEnablement = True`,
  `requiresRollbackPlan = True`
- `category = "write"`, `safetyTier = "dev_sandbox_write"`, `enabledInPhase = "2C"`

The consistency check also verifies write tools are disjoint from the
read-only allowlist, the production tool inventory, and the denylist.

## Argument validation

The registry performs **structural** validation only:

- accepted keys per tool (`targetPath`, `content`, `mode`, `search`, `replace`);
- secret / shell / command / database key stems are rejected;
- content is checked for NUL and binary (C0 control chars);
- `targetPath` is checked as a bounded string — **path-safety classification**
  (traversal / absolute / symlink escape / forbidden target / file type) is
  delegated to `dev_web_write_sandbox`, which produces the precise blocked
  reason.

## Public API

`list_write_tool_definitions()`, `get_write_tool_definition(tool_id)`,
`is_phase_2c_write_tool(tool_id)`, `validate_write_tool_definition(tool)`,
`validate_write_tool_arguments(tool_id, args)`,
`normalize_write_tool_arguments(tool_id, args)`.
