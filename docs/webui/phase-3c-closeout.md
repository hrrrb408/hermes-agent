# Phase 3C — Closeout

| Field | Value |
|-------|-------|
| Phase | 3C (Closeout) |
| Title | Static Capability Registry — Closeout |
| Status | Closed |
| Date | 2026-06-18 |
| Branch | `dev-huangruibang` |
| Closeout ID | `PHASE-3C-CLOSEOUT-001` |

## 1. Phase 3C 起点

Phase 3C — **Plugin / Capability Registry** — was sequenced behind Phase 3A
(+ H1) and Phase 3B / 3B-Live-Enablement (+ H1). Its scope was intentionally
narrowed from any kind of plugin runtime to a **static, dev-only, descriptive
Capability Registry**: it declares the capabilities the dev instance knows
about and grants **no** permission. No dynamic loading, no marketplace, no
remote registry, no new route, no production rollout.

## 2. Phase 3C commit chain

| Milestone | Commit | Message |
|-----------|--------|---------|
| Planning | `8d70048d3649f2c9ea5b401643748b98b9dfd42d` | `docs(webui): plan phase 3c capability registry` |
| Implementation | `703a4a980427e2eaac925f4659af74e0a7ace070` | `feat(webui): add static capability registry` |
| H1 Hardening | `34b04d603ec1f7cc06feb562759cbdbd02e4d70c` | `chore(webui): harden static capability registry` |
| Closeout | _(set on commit)_ | `docs(webui): close phase 3c capability registry` |

## 3. Final HEAD

After closeout, `origin/dev-huangruibang` points to the closeout commit. Local
and remote are synchronized (ahead / behind = 0 / 0).

## 4. Current capability state

The Capability Registry is:

- **Static** — a tracked, deterministic in-process manifest (`phase3c-static-v1`),
  46 capabilities, pinned timestamps, no execution surface.
- **Dev-only** — `devOnly = true`, `productionAllowed = false` for every
  capability.
- **Read-only** — exposed only through the existing `GET /status` response
  (`data.capabilityRegistry`) and the read-only Dev WebUI panel. No
  enable/disable/promote/delete control.
- **Descriptive-only** — it describes capabilities; it grants no permission,
  executes nothing, and bypasses no gate.

## 5. Core deliverables

- Backend: schema, manifest, policy, audit bridge, loader/read-model
  (`hermes_cli/dev_web_capability_registry*.py`).
- Frontend: read-only Capability Registry section + summary/table/drawer/badges
  (`apps/hermes-dev-webui/src/components/devconsole/Capability*.vue`).
- Frozen policy flags surfaced under `/status`:
  `dynamicLoadingAllowed = remoteRegistryAllowed = marketplaceAllowed =
  productionAllowed = false`; `devOnly = true`; `redactionApplied = true`.
- Smoke: Profile P (`phase3c_capability_registry_static`) and Profile Q
  (`phase3c_h1_capability_registry_hardening`), both in `all`.
- Hardening audit script: `scripts/run-dev-webui-phase3c-hardening-audit.sh`.

## 6. Verified security boundary

- Forbidden fields (top-level, alias, and nested) are rejected fail-closed.
- The read model never carries a secret / callable repr / shell command / SQL
  statement / production path / local plugin path / dynamic import path /
  external URL / Authorization header / Bearer token.
- No dynamic loading (`importlib` / `__import__` / path-based load / `pkgutil`
  walk). No `eval` / `exec` / `subprocess` / `os.system` / `shell=True`.
- `capability_registry_*` audit (10 event types) is redacted + no-leak, reusing
  `AUDIT_KIND_INTERNAL`.
- Route governance unchanged: OpenAPI 34 / runtime 34 / 5 / 0 / 1 / 1.

## 7. The real defect found and closed (Phase 3C-H1)

The Phase 3C-H1 review found one real defect: the forbidden-field scanner was
shallow, so a forbidden field nested inside an allowed field's value (e.g.
`{"metadataSchema": {"shellCommand": ...}}`) could pass validation and leak
through the read model. Closed by a **recursive forbidden-field scan** plus a
**scalar-string type guard**. All 160 Phase 3C backend tests still pass.

## 8. Not implemented (intentional)

No plugin runtime. No dynamic loading. No remote registry. No marketplace. No
external plugin fetch. No provider-generated plugin. No shell / database /
external-HTTP / production-operation capability execution. No provider write.
No autonomous write. No live provider request. No real API key read. No
external network. No new route. No production rollout. No `~/.hermes` /
production `state.db` access.

## 9. Phase 3D Planning — CONDITIONAL GO

Phase 3D **Planning** (Plugin Runtime Planning, docs-only) may be prepared
**only after explicit user request**. Phase 3D **Implementation** is NO-GO by
default. See [Phase 3D entry criteria](phase-3c-phase-3d-entry-criteria.md).

## 10. Phase 3D Implementation — NO-GO

Phase 3D Implementation is not authorized. No plugin runtime, dynamic loading,
remote registry, or marketplace may be implemented without a separately
authorized planning phase, threat model, and GO/NO-GO.

## 11. Human approval requirement

Every transition beyond this closeout — Phase 3D Planning, Phase 3D
Implementation, any production rollout, any live provider execution — requires
explicit human approval. The manual one-shot live provider execution remains
separately gated and is not part of Phase 3D.

## 12. Final acceptance conclusion

Phase 3C is formally **closed** as a static dev-only Capability Registry
milestone. 12 / 12 hardening lenses PASS; P0 = 0; P1 = 0. Phase 3D has not
started. Plugin runtime is not implemented. Dynamic loading, remote registry,
marketplace, and production rollout remain forbidden.

## 13. Cross-references

- [Release readiness](phase-3c-release-readiness.md)
- [Final acceptance](phase-3c-final-acceptance.md)
- [Final security boundary](phase-3c-security-boundary-final.md)
- [Risk closure](phase-3c-risk-closure.md)
- [Final GO / NO-GO](phase-3c-final-go-no-go.md)
- [Phase 3D entry criteria](phase-3c-phase-3d-entry-criteria.md)
- [Closeout prompt](phase-3c-closeout-prompt.md)
