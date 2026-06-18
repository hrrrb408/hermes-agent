# Phase 3D — Static Plugin Descriptor Registry Implementation

> Phase 3D Implementation — Static Reviewed Plugin Descriptor Registry Skeleton,
> Capability-bound, Disabled-by-default, No Plugin Execution.

## 1. Status

**Implemented.** Phase 3D adds a **static dev-only plugin descriptor registry
skeleton** to the Hermes Dev WebUI. It is descriptor-only, disabled-by-default,
capability-bound, and read-only.

**It is explicitly NOT:**

- a plugin runtime
- a plugin loader / executor
- a dynamic plugin loading system (no `importlib`, no `__import__`, no
  path-based load, no directory scan)
- a local plugin directory loader
- a remote registry / marketplace / external plugin fetch
- a provider-generated plugin surface
- an LLM-generated plugin install surface
- a production rollout

## 2. Goal

The registry **describes** future plugin descriptors. It does not execute a
plugin, does not load a plugin, does not grant permission, does not create an
approval / confirmation / dry-run / route, and does not introduce an execution
path. Every descriptor binds only to existing Phase 3C Capability Registry
capabilityIds.

## 3. Backend deliverables

| Module | Responsibility |
|--------|----------------|
| `hermes_cli/dev_web_plugin_descriptor_schema.py` | Frozen taxonomies (trust levels, statuses, execution modes, sources, permission classes), allowed/required/forbidden field sets (canonical + alias), dataclasses, validation predicates, permission-restrictiveness ordering. |
| `hermes_cli/dev_web_plugin_descriptor_manifest.py` | Static, tracked, deterministic, descriptor-only manifest of 12 descriptors. Pure data; no executable reference. |
| `hermes_cli/dev_web_plugin_descriptor_policy.py` | Capability binding + permission inheritance (most-restrictive) + trust classification. Reads the validated Phase 3C manifest read-only. |
| `hermes_cli/dev_web_plugin_descriptor_registry.py` | Loader, validation, read model, and the `/status` block builder. Fail-closed. |
| `hermes_cli/dev_web_plugin_descriptor_audit.py` | `plugin_descriptor_*` audit bridge into the Phase 2D durable store. No-leak, fail-safe. |
| `hermes_cli/dev_web_api.py` | Adds `pluginDescriptorRegistry` to the existing `/status` response. **No new route.** |

## 4. Frontend deliverables

| Artifact | Role |
|----------|------|
| `types/api/pluginDescriptorRegistry.ts` | Frozen types (detail + summary). |
| `api/pluginDescriptorRegistry.ts` | Reads `GET /status data.pluginDescriptorRegistry`. No new route. |
| `stores/pluginDescriptorRegistry.ts` | Pinia store + frozen policy flags + read-only filters. |
| `constants/pluginDescriptorRegistryManifest.ts` | Deterministic mirror of the 12 descriptors. |
| `components/devconsole/PluginDescriptorRegistrySection.vue` | Read-only section (banner + summary + filters + table + drawer). |
| `components/devconsole/PluginDescriptorRegistrySummary.vue` | Frozen flags + counts. |
| `components/devconsole/PluginDescriptorRegistryTable.vue` | Read-only descriptor table. |
| `components/devconsole/PluginDescriptorRegistryDetailDrawer.vue` | Safe detail drawer. |
| `components/devconsole/PluginDescriptor{Trust,Status,Permission}Badge.vue` | Non-color badges (label + icon). |
| `components/devconsole/PluginRuntimeDisabledBanner.vue` | Runtime-disabled invariants. |
| `stores/devConsoleNav.ts` + `DevConsoleLayout.vue` + `DevConsoleNav.vue` | New `plugins` nav section. |

## 5. Descriptor model

12 descriptors: 3 visible, 4 disabled, 5 blocked.

| Descriptor | Status | Permission | Trust | Binding(s) |
|-----------|--------|-----------|-------|-----------|
| `plugin.descriptor.registry_status` | visible | READ_ONLY | trusted_static_descriptor | `registry.capability_registry_status` |
| `plugin.descriptor.capability_binding_view` | visible | READ_ONLY | trusted_static_descriptor | `registry.capability_registry_detail` |
| `plugin.descriptor.audit_view` | visible | READ_ONLY | trusted_static_descriptor | `registry.capability_registry_audit` |
| `plugin.descriptor.read_only_tool_bridge` | disabled | READ_ONLY | dev_reviewed_descriptor | `tool.read.tool_policy_read`, `tool.read.route_governance_read` |
| `plugin.descriptor.sandbox_write_preview_bridge` | disabled | WRITE_CONFIRM | dev_reviewed_descriptor | `tool.sandbox.dev_sandbox_file_{write,append,patch}` |
| `plugin.descriptor.provider_boundary_bridge` | disabled | READ_ONLY | dev_reviewed_descriptor | `provider.real_boundary_status`, `provider.real_request_preview` |
| `plugin.descriptor.workflow_step_bridge` | disabled | READ_ONLY | dev_reviewed_descriptor | `workflow.step.read_only_tool`, `workflow.step.manual_note` |
| `plugin.descriptor.dynamic_plugin_load_blocked` | blocked | EXTERNAL_FORBIDDEN | external_forbidden | `capability.forbidden.dynamic_plugin_load` |
| `plugin.descriptor.remote_registry_blocked` | blocked | EXTERNAL_FORBIDDEN | external_forbidden | `capability.forbidden.remote_registry` |
| `plugin.descriptor.marketplace_blocked` | blocked | EXTERNAL_FORBIDDEN | external_forbidden | `capability.forbidden.marketplace` |
| `plugin.descriptor.external_execution_blocked` | blocked | EXTERNAL_FORBIDDEN | external_forbidden | `capability.forbidden.{external_http,shell,database_mutation}` |
| `plugin.descriptor.production_operation_blocked` | blocked | PRODUCTION_FORBIDDEN | production_forbidden | `capability.forbidden.production_operation` |

Every descriptor: `devOnly=true`, `productionAllowed=false`,
`disabledByDefault=true`, `executionMode=descriptor_only`.

## 6. Hard invariants

- Every binding references an **existing** Phase 3C capabilityId. No descriptor
  introduces a new capabilityId or permission class.
- A descriptor inherits the **most-restrictive** permission class among its
  bindings. Declaring a less-restrictive class (escalation) is rejected
  fail-closed.
- A descriptor bound to a forbidden capability **must** be `blocked` and may not
  carry a verified trust level (no trust self-upgrade).
- Forbidden fields (canonical + alias + casing variants) are rejected at any
  depth (recursive scan), fail-closed.
- `/status pluginDescriptorRegistry` and the UI are value-free (no secret /
  callable / path / command / URL).
- Route governance unchanged: **OpenAPI 34 / runtime 34 / Tool GET 5 / Tool
  write 0 / Tool dry-run 1 / Tool execution 1**.

## 7. Gates passed

- Phase 3D backend tests (10 files, 316 tests): PASS.
- Phase 3D frontend tests (7 files): PASS.
- Frontend type-check / lint / build: PASS.
- Route governance (`test_dev_check_webui.py`, `test_dev_web_0c06_closure.py`): PASS.
- Smoke profile `phase3d_plugin_descriptor_registry_static`: PASS.
- `memory-check` / `dev-check`: PASS.

## 8. Deferred / not implemented

Plugin runtime execution, plugin loader, dynamic loading, local plugin
directory loading, remote registry, marketplace, external plugin fetch,
provider-generated plugin, LLM-generated plugin install, shell execution,
database mutation, external HTTP execution, production operation, provider
write, autonomous write, live provider request, real API-key read, external
network, production rollout, and any new HTTP route are all **deferred /
permanently forbidden** in this version.

**Next recommended task:** Phase 3D-H1 Plugin Descriptor Registry Hardening
before any future consideration of real plugin runtime execution.

## Update — Phase 3D-H1 Hardening COMPLETE

Phase 3D-H1 hardened the static dev-only plugin descriptor registry skeleton
(HARDENING-3D-H1-001). The hardening pass added 10 backend + 8 frontend
hardening tests, a `phase3d_h1_plugin_descriptor_registry_hardening` smoke
profile + spec, and `scripts/run-dev-webui-phase3d-hardening-audit.sh`. **No
implementation code changed** — no defect required a fix. All 12 lenses PASS;
P0 = 0; P1 = 0. The registry remains descriptor-only, disabled-by-default,
capability-bound, read-only, and dev-only — no plugin runtime, no loader, no
dynamic loading, no local plugin directory loading, no remote registry, no
marketplace, no external plugin fetch, no provider-generated plugin, no
LLM-generated plugin install. Route governance unchanged (34 / 34 / 5 / 0 / 1 /
1); Production Gateway PID `28428` untouched. See
[phase-3d-h1-plugin-descriptor-registry-hardening](phase-3d-h1-plugin-descriptor-registry-hardening.md)
and [phase-3d-h1-test-report](phase-3d-h1-test-report.md).
