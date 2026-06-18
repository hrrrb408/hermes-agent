# PLUG-PROVIDER-WORKFLOW-3D-H1-001 — Provider / Workflow Boundary / No Generated Plugin

**Lens 8.** A provider response, tool_calls, or workflow output can never create,
install, enable, or execute a descriptor.

## Scope

- The registry has no generation API (`create_descriptor_from_provider`,
  `create_descriptor_from_tool_calls`, `create_descriptor_from_workflow`,
  `install_from_provider`, `register_from_provider`, `ingest_provider_response`,
  `ingest_tool_calls`, `ingest_workflow_output`, `provider_install`,
  `workflow_install`, `auto_install`, `auto_enable`, `auto_advance`).
- The registry source references no provider-response / tool_calls /
  workflow-output handler.
- Frozen flags: `PROVIDER_GENERATED_PLUGIN_ALLOWED = False`,
  `LLM_GENERATED_PLUGIN_INSTALL_ALLOWED = False`. The status block surfaces both
  as false.
- The provider-boundary bridge descriptor is disabled (binds only read-only
  boundary capabilities — never a live request). The workflow-step bridge
  descriptor is disabled (binds only read-only workflow steps, READ_ONLY).
- The manifest is a frozen tuple — no runtime append path; the descriptor count
  is stable at 12.

## Evidence

`tests/test_dev_web_phase_3d_h1_descriptor_provider_workflow_boundary.py` (13 tests).

## Result

PASS. No provider-generated plugin, no LLM-generated plugin install, no workflow
auto-advance.
