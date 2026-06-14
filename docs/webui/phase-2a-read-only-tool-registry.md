# Phase 2A — Read-only Tool Registry

## 1. Purpose

The read-only tool registry
(`hermes_cli/dev_web_read_only_tool_registry.py`) is the single metadata source
for the five Phase 2A read-only inspection tools. It is the **only** place that
defines their rich metadata (display name, argument schema, safety tier,
category). It does NOT define a second allowlist — it re-exports
`STATIC_ALLOWLIST` from `dev_web_tool_policy.py`, which remains the single
source of truth for allowlist *membership*.

## 2. Single Source of Truth

- `STATIC_ALLOWLIST` is defined **once** in `dev_web_tool_policy.py:1019`.
- The registry re-exports it (`from hermes_cli.dev_web_tool_policy import
  STATIC_ALLOWLIST`).
- The registry cross-checks at import time that every registry tool id is a
  member of `STATIC_ALLOWLIST` (consistency guard `_verify_registry_consistency`).
- Tests pin the allowlist against both the policy literal and the registry, so
  the two cannot drift.

## 3. Public API

```python
PHASE_2A_READ_ONLY_TOOL_IDS      # frozenset of the 5 tool ids
STATIC_ALLOWLIST                 # re-exported (single source of truth)
get_read_only_tool_definition(tool_id) -> ReadOnlyToolDefinition | None
list_read_only_tool_definitions() -> tuple[ReadOnlyToolDefinition, ...]
is_phase_2a_read_only_tool(tool_id) -> bool
validate_read_only_tool_arguments(tool_id, args) -> (normalized, error_code)
normalize_read_only_tool_arguments(tool_id, args) -> dict
```

## 4. ReadOnlyToolDefinition

Each definition carries the invariant Phase 2A safety profile:

| Field | Value |
|-------|-------|
| `read_only` | `True` |
| `external_side_effects` | `False` |
| `provider_required` | `False` |
| `write_required` | `False` |
| `requires_confirmation` | `True` |
| `safety_tier` | `"read_only_safe"` |
| `enabled_in_phase` | `"2A"` |

Plus `tool_id`, `display_name`, `description`, `category`, `argument_schema`
(JSON Schema), `result_schema`, and `audit_redaction_policy`.

## 5. The Five Tools

| Tool ID | Category | Risk | Arguments |
|---------|----------|------|-----------|
| tool_policy_read | policy | R0 | `includeDisabled: bool` |
| route_governance_read | governance | R0 | `includeDetails: bool` |
| audit_events_read | audit | R1 | `limit: int(1..100)`, `eventType/toolId/status/correlationId: str` |
| dev_environment_read | environment | R1 | `includePorts: bool`, `includeProductionGatewayReadOnlyCheck: bool` |
| release_status_read | release | R1 | `includePhaseTimeline: bool`, `includeP2Backlog: bool` |

## 6. Argument Validation (strict whitelist)

`validate_read_only_tool_arguments` enforces a strict per-tool whitelist:

- Unknown keys → `READ_ONLY_ARG_UNKNOWN_KEY`.
- Forbidden stems (token, secret, password, path, command, sql, regex, glob…) →
  `READ_ONLY_ARG_FORBIDDEN_KEY`.
- Values resembling paths (`/`, `~`, `..`, `file://`), shell metacharacters
  (`| ; \` $ > < &`), or secret patterns (`sk-…`, `Bearer …`) →
  `READ_ONLY_ARG_INVALID_VALUE`.
- Integers bounded to declared `[min, max]`; strings bounded to `maxLength`.

`normalize_read_only_tool_arguments` always returns a default-populated dict so
a handler never receives untrusted or missing values.

## 7. Handler Layer

`hermes_cli/dev_web_read_only_tool_handlers.py` implements the five handlers +
`dispatch_read_only_tool(tool_id, arguments, hermes_home=None)`. Each handler
returns the safe envelope `{"type": <toolId>, "message": <summary>, "result":
<structured>}`. The dispatcher pre-normalizes arguments and re-redacts +
size-bounds every result. All hermes_cli imports are lazy (no import cycles).
