# Phase 3D Execution Brief — Static Dev-only Plugin Descriptor Runtime Skeleton

## Document Information

| Field | Value |
|-------|-------|
| Phase | 3D |
| Title | Static Dev-only Plugin Descriptor Runtime Skeleton (Execution Brief) |
| Status | Brief prepared — Plugin Runtime **not started** |
| Date | 2026-06-18 |
| Branch | `dev-huangruibang` |
| Planning ID | `PHASE-3D-PLANNING-001` |
| Brief ID | `PHASE-3D-EXECUTION-BRIEF-001` |

> This brief is the one-page contract for a future, separately-authorized Phase
> 3D. **The Plugin Runtime is not started by this planning phase.** The full
> copy-paste prompt is [phase-3d-prompt.md](phase-3d-prompt.md).

## 1. Name

Static Dev-only Plugin Descriptor Runtime Skeleton.

## 2. Goal

Ship a **static, tracked, deterministic, dev-only** plugin descriptor runtime
skeleton that declares reviewed descriptors, binds each to an existing Phase 3C
capability ID, classifies each by a frozen permission class and trust level,
validates against a forbidden-fields list, exposes a read-only view, and audits
descriptor lifecycle events. The runtime grants no permission, loads no code, and
executes nothing.

## 3. Scope (allowed, future)

- A static plugin descriptor module (single tracked Python file).
- Descriptor validation with the frozen forbidden-fields list (recursive + scalar
  type guard).
- Descriptor classification (permissionClass + trustLevel + status).
- Capability binding to **existing** Phase 3C capability IDs only.
- Descriptor status surfaced inside the **existing** `/status` response only if no
  new route is required (`pluginRuntime` block, value-free markers).
- Frontend read-only descriptor panel + detail drawer + runtime-disabled banner.
- `plugin_*` audit events (safe fields only, dual-write, fail-closed).
- Backend + frontend unit / contract tests; a no-leak test; a route-governance
  contract test.
- A new additive smoke profile + spec (only if a UI surface is added).

## 4. Non-goals (forbidden)

Dynamic plugin runtime; dynamic loading (`importlib`, path load, npm / remote JS
plugin); marketplace; remote registry; remote manifest; arbitrary-URL fetch;
local plugin directory loading; shell-command / database / external-HTTP plugin;
provider-generated plugin; LLM-generated tool installed as plugin; self-modifying
plugin; auto-enable; trust auto-upgrade; provider write / auto-write / autonomous
write; production rollout; `~/.hermes` access; production `state.db` access; a new
HTTP route / Provider route / Tool write route by default; reading any API key;
any network call.

## 5. Inputs

- Baseline: `26da46b9cf90d9f1e41c65574fbad0a545495982` (Phase 3C closeout).
- HERMES_HOME: `/Users/huangruibang/Code/hermes-home-dev`.
- Reused surfaces: Phase 3C Capability Registry (binding target), Phase 2A
  read-only allowlist, Phase 2C / 2C-H1 write + rollback confirmation, Phase 2D
  durable audit store, Phase 3A workflow approval gates, Phase 3B / 3B-Live
  provider boundary.

## 6. Outputs

- A static, validated plugin descriptor module.
- A `pluginRuntime` status block under the existing `/status` (no new route).
- A read-only frontend descriptor panel + drawer.
- `plugin_*` audit events dual-written to the Phase 2D store + dev JSONL.
- Phase 3D closeout docs.

## 7. Manifest / lifecycle / permission

Frozen in [phase-3d-plugin-manifest-contract.md](phase-3d-plugin-manifest-contract.md),
[phase-3d-plugin-lifecycle-model.md](phase-3d-plugin-lifecycle-model.md), and
[phase-3d-permission-and-approval-model.md](phase-3d-permission-and-approval-model.md).
Every descriptor is `devOnly=true`, `productionAllowed=false`, disabled by default.
Forbidden classes are terminal and non-executable.

## 8. Risk gates

P0 stop conditions and P1 push-gates from
[phase-3d-risk-register.md](phase-3d-risk-register.md).

## 9. Commit message (this planning phase)

```
docs(webui): plan phase 3d plugin runtime
```

The future implementation uses its own conventional commit, e.g.
`feat(webui): add static dev plugin descriptor runtime`.

## 10. Final report format

A closeout report mirroring the Phase 3C structure: scope, what changed, what did
not change, route governance, production safety, gates, residual risks (P2),
conclusion.

## 11. Phase 3D implementation must NOT start here

This brief is the contract for a future, separately-authorized phase. It does not
start the Plugin Runtime. The copy-paste prompt lives at
[phase-3d-prompt.md](phase-3d-prompt.md).

## 12. Cross-references

- [Phase 3D planning](phase-3d-planning.md)
- [Phase 3D GO / NO-GO](phase-3d-go-no-go.md)
- [Phase 3D implementation entry criteria](phase-3d-implementation-entry-criteria.md)
- [Phase 3D prompt draft](phase-3d-prompt.md)
