# Phase 3C — Tool Capability Mapping

| Field | Value |
|-------|-------|
| Phase | 3C (Planning) |
| Title | Tool Capability Mapping (Existing Tools → Capabilities) |
| Status | Frozen (docs-only planning; Capability Registry **not started**) |
| Date | 2026-06-17 |
| Planning ID | `PHASE-3C-PLANNING-001` |
| Mapping ID | `PHASE-3C-TOOL-MAP-001` |

> This document maps the **existing** tool surface to capability records. The
> registry describes these; it does **not** change any tool's execution
> conditions. READ_ONLY tools keep their read-only allowlist; WRITE_CONFIRM /
> ROLLBACK_CONFIRM tools keep their dry-run + confirmation + audit chains.

## 1. READ_ONLY allowlist

| Tool | capabilityId | permissionClass | trustLevel | status |
|------|--------------|-----------------|------------|--------|
| `clarify` | `tool.read.clarify` | `READ_ONLY` | `BUILTIN_VERIFIED` | `enabled` |
| `tool_policy_read` | `tool.read.tool_policy` | `READ_ONLY` | `BUILTIN_VERIFIED` | `enabled` |
| `route_governance_read` | `tool.read.route_governance` | `READ_ONLY` | `BUILTIN_VERIFIED` | `enabled` |
| `audit_events_read` | `tool.read.audit_events` | `READ_ONLY` | `BUILTIN_VERIFIED` | `enabled` |
| `dev_environment_read` | `tool.read.dev_environment` | `READ_ONLY` | `BUILTIN_VERIFIED` | `enabled` |
| `release_status_read` | `tool.read.release_status` | `READ_ONLY` | `BUILTIN_VERIFIED` | `enabled` |

These capabilities are descriptive. Their executability continues to be governed
by the Phase 2A `STATIC_ALLOWLIST` and the existing read-only tool chain. The
registry grants nothing.

## 2. Phase 2C sandbox write tools

| Tool | capabilityId | permissionClass | trustLevel | executionMode | status |
|------|--------------|-----------------|------------|---------------|--------|
| `dev_sandbox_file_write` | `sandbox.write.file_write` | `WRITE_CONFIRM` | `BUILTIN_VERIFIED` | `confirmed_execute` | `enabled` (gated) |
| `dev_sandbox_file_append` | `sandbox.write.file_append` | `WRITE_CONFIRM` | `BUILTIN_VERIFIED` | `confirmed_execute` | `enabled` (gated) |
| `dev_sandbox_file_patch` | `sandbox.write.file_patch` | `WRITE_CONFIRM` | `BUILTIN_VERIFIED` | `confirmed_execute` | `enabled` (gated) |
| `dev_sandbox_file_readback` | `sandbox.read.file_readback` | `READ_ONLY` | `BUILTIN_VERIFIED` | `read_only` | `enabled` |
| `dev_sandbox_rollback_execute` | `sandbox.rollback.execute` | `ROLLBACK_CONFIRM` | `BUILTIN_VERIFIED` | `confirmed_execute` | `enabled` (gated) |

### Invariants preserved

- `WRITE_CONFIRM` tools still require dry-run + confirmation token + digest +
  audit (Phase 2C / 2C-H1). The registry does not relax this.
- `ROLLBACK_CONFIRM` still requires a rollback manifest + confirmation + audit
  (Phase 2C-H1). The registry does not relax this.
- "enabled (gated)" means the capability is registered, but its execution still
  depends on `HERMES_TOOL_WRITE_EXECUTION_ENABLED` and the full confirmation
  chain. The registry grants nothing.

## 3. Forbidden tool capabilities

The registry must declare the following as forbidden / blocked so they are
**visible as blocked** in the UI and audit, and never executable:

| capabilityId | permissionClass | trustLevel | status | blockedReason |
|--------------|-----------------|------------|--------|---------------|
| `tool.forbidden.shell` | `ADMIN_FORBIDDEN` | `EXTERNAL_FORBIDDEN` | `blocked` | `blocked_shell_forbidden` |
| `tool.forbidden.database_mutation` | `ADMIN_FORBIDDEN` | `EXTERNAL_FORBIDDEN` | `blocked` | `blocked_database_mutation_forbidden` |
| `tool.forbidden.external_http` | `EXTERNAL_FORBIDDEN` | `EXTERNAL_FORBIDDEN` | `blocked` | `blocked_external_http_forbidden` |
| `tool.forbidden.production_operation` | `PRODUCTION_FORBIDDEN` | `EXTERNAL_FORBIDDEN` | `blocked` | `blocked_production_operation_forbidden` |
| `tool.forbidden.plugin_dynamic_load` | `EXTERNAL_FORBIDDEN` | `EXTERNAL_FORBIDDEN` | `blocked` | `blocked_plugin_dynamic_load_forbidden` |
| `tool.forbidden.provider_write` | `ADMIN_FORBIDDEN` | `EXTERNAL_FORBIDDEN` | `blocked` | `blocked_provider_write_forbidden` |
| `tool.forbidden.provider_auto_write` | `ADMIN_FORBIDDEN` | `EXTERNAL_FORBIDDEN` | `blocked` | `blocked_provider_auto_write_forbidden` |
| `tool.forbidden.autonomous_write` | `ADMIN_FORBIDDEN` | `EXTERNAL_FORBIDDEN` | `blocked` | `blocked_autonomous_write_forbidden` |

These declarations are descriptive: they make the prohibition explicit and
auditable. They do not create an execution path.

## 4. Non-negotiable statement

The Capability Registry **does not change** any existing tool's execution
conditions. Every tool keeps its current policy, allowlist membership,
confirmation chain, audit chain, and route exposure. The registry only labels
and describes.

## 5. Cross-references

- [Phase 3C planning](phase-3c-planning.md)
- [Phase 3C capability model](phase-3c-capability-model.md)
- [Phase 3C permission classes + trust levels](phase-3c-capability-permission-classes.md)
- [Phase 1G tool execution safety scope](phase-1g-00-tool-execution-safety-scope.md)
- [Phase 2C controlled write execution](phase-2c-controlled-tool-write-execution.md)
