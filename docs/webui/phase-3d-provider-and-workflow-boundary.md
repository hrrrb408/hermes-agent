# Phase 3D — Provider & Workflow Boundary

| Field | Value |
|-------|-------|
| Phase | 3D (Planning) |
| Title | Plugin Runtime — Provider & Workflow Boundary (Frozen) |
| Status | Frozen (docs-only planning; Plugin Runtime **not started**) |
| Date | 2026-06-18 |
| Planning ID | `PHASE-3D-PLANNING-001` |
| Boundary ID | `PHASE-3D-PROVIDER-WORKFLOW-BOUNDARY-001` |

> Neither a provider response nor a workflow may create, install, enable, or
> execute a plugin. This boundary is frozen.

## 1. Provider boundary

- A provider response **cannot create** a plugin.
- A provider response **cannot install** a plugin.
- A provider response **cannot enable** a plugin.
- A provider response **cannot execute** a plugin.
- Provider `tool_calls` remain **classified only** unless separately approved (the
  existing tool policy governs them; they never become plugins).
- Provider write remains **forbidden**.
- Provider auto-write remains **forbidden**.
- Provider autonomous action remains **forbidden**.
- Manual one-shot live execution remains **separate** (Phase 3B-Live-Enablement)
  and is **not part of Phase 3D**.

## 2. Workflow boundary

- A workflow **cannot create** a plugin.
- A workflow **cannot install** a plugin.
- A workflow **cannot enable** a plugin.
- A workflow **cannot auto-advance** plugin execution.
- A workflow **cannot execute** plugin write.
- A workflow **cannot bypass** approval.
- Workflow background scheduling remains **forbidden**.

## 3. Why

A provider response is untrusted model output; a workflow is operator-orchestrated
state. Allowing either to materialize a plugin would let untrusted input or
orchestrated state gain an execution path outside the existing gates. Both are
therefore terminal boundaries: no plugin originates from them.

## 4. Cross-references

- [Phase 3D planning](phase-3d-planning.md)
- [Phase 3D threat model](phase-3d-threat-model.md)
- [Phase 3D execution isolation model](phase-3d-execution-isolation-model.md)
- [Phase 3B security boundary](phase-3b-security-boundary.md)
- [Phase 3B-Live-Enablement security boundary](phase-3b-live-enablement-security-boundary.md)
- [Phase 3A workflow approval gates](phase-3a-workflow-approval-gates.md)
