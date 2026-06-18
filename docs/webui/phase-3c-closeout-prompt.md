# Phase 3C — Closeout Prompt (Draft)

| Field | Value |
|-------|-------|
| Phase | 3C (Closeout) |
| Title | Next-Step Prompt Drafts (not executed) |
| Status | Draft only |
| Date | 2026-06-18 |

> This document contains **draft** next-step prompts only. It is not executed
> by the closeout. Either branch requires explicit human approval before it
> may begin.

## 0. Non-negotiable constraints (apply to either branch)

- **Do not execute Phase 3D Implementation.**
- **Do not implement a plugin runtime during closeout.**
- **Do not dynamically load plugins.**
- **Do not access `~/.hermes`.**
- **Do not read API keys.**
- Branch must remain `dev-huangruibang`; Production Gateway PID must remain
  `28428`; route governance must remain `34/34/5/0/1/1`.

---

## Option A — Phase 3D Plugin Runtime Planning Prompt (draft)

```text
Phase 3D — Plugin Runtime Planning (docs-only).

Goal: produce a Phase 3D scope freeze, a dynamic-loading / plugin-execution
threat model, a remote-registry / marketplace security model (or an explicit
decision to keep them forbidden), a Phase 3D risk register, and a Phase 3D
GO/NO-GO — as documentation only.

This phase is PLANNING ONLY. Do not implement a plugin runtime. Do not
dynamically load plugins. Do not introduce importlib dynamic import, a remote
registry, a marketplace, or external plugin fetch. Do not read API keys or
access ~/.hermes. Do not add any HTTP route. Route governance must remain
34/34/5/0/1/1. Production Gateway PID must remain 28428.

Begin only after explicit user approval.
```

## Option B — Phase 3C Release Readiness / Human Review Prompt (draft)

```text
Phase 3C — Release Readiness / Human Review.

Goal: a human reviewer audits the Phase 3C closeout documents and the shipped
+ hardened Capability Registry, and records a final review decision.

The reviewer verifies: the registry is static / dev-only / read-only /
descriptive-only; it grants no permission and executes nothing; forbidden
fields (top-level, alias, nested) are rejected fail-closed; the read model,
/status block, audit events, and UI are no-leak; route governance is
34/34/5/0/1/1; no plugin runtime / dynamic loading / remote registry /
marketplace / provider write / autonomous write / production rollout / live
provider request / real API key read / external network / new route /
~/.hermes access / production state.db access was introduced.

Do not implement anything. Do not modify code, tests, or scripts. Do not
dynamically load plugins. Do not access ~/.hermes. Do not read API keys.
```

## 1. Cross-references

- [Closeout](phase-3c-closeout.md)
- [Final GO / NO-GO](phase-3c-final-go-no-go.md)
- [Phase 3D entry criteria](phase-3c-phase-3d-entry-criteria.md)
