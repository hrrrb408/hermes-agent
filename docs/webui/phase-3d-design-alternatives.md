# Phase 3D — Design Alternatives (Optional)

| Field | Value |
|-------|-------|
| Phase | 3D (Planning) |
| Title | Plugin Runtime Planning — Design Alternatives Considered |
| Status | Optional companion |
| Date | 2026-06-18 |
| Planning ID | `PHASE-3D-PLANNING-001` |

> This document records the design alternatives that were considered and
> **rejected**, so the reasoning is auditable. The selected direction is the
> **Static Dev-only Plugin Descriptor Runtime Skeleton** (descriptor-only; no
> execution).

## 1. Alternatives considered

| # | Alternative | Verdict | Why |
|---|-------------|---------|-----|
| A | **Dynamic plugin runtime** with sandboxed code loading | **REJECTED** | Converts a descriptive layer into an arbitrary-code-execution surface; breaks the static / tracked / reviewable invariant; introduces supply-chain + secret-leak vectors (PLUG-THREAT-01). |
| B | **Local plugin directory** discovery | **REJECTED** | Untrusted files influence the descriptor set; path-traversal risk (PLUG-THREAT-02). |
| C | **Remote plugin registry** | **REJECTED** | Supply-chain attack surface (PLUG-THREAT-03). |
| D | **Plugin marketplace** | **REJECTED** | Malicious-listing install path (PLUG-THREAT-04). |
| E | **Provider- / LLM-generated plugins** | **REJECTED** | Untrusted model output gains an execution path (PLUG-THREAT-05/06). |
| F | **Static descriptor runtime skeleton (selected)** | **SELECTED** | Strongest isolation: descriptors carry no code, so there is nothing to sandbox; binds to existing capabilities; inherits all existing gates. |

## 2. Why descriptor-only is the safest first step

A descriptor is pure data. It cannot execute, so it has no execution surface to
isolate, no sandbox to escape, and no code to supply-chain-attack. Any capability
it *references* is executed only through that capability's existing gates. This
makes the first version maximally reversible and auditable, and lets a future,
separately-authorized phase add execution only behind its own threat model and
GO/NO-GO.

## 3. If execution is ever needed (future, not this phase)

A future phase that wants real plugin execution must, at minimum:

- be a separately authorized phase with its own scope freeze + threat model +
  GO/NO-GO;
- introduce a real sandbox (process / container / WASM) with no shell / DB /
  external-HTTP / production / secret access;
- keep descriptors capability-bound and disabled-by-default;
- add audit + kill switch + confirmation for every execution;
- not relax any existing gate.

None of that is in scope for Phase 3D.

## 4. Cross-references

- [Phase 3D planning](phase-3d-planning.md)
- [Phase 3D scope freeze](phase-3d-plugin-runtime-scope-freeze.md)
- [Phase 3D threat model](phase-3d-threat-model.md)
- [Phase 3C no dynamic loading policy](phase-3c-no-dynamic-loading-policy.md)
