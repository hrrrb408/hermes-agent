# Phase 3D — Security Review Checklist (Optional)

| Field | Value |
|-------|-------|
| Phase | 3D (Planning) |
| Title | Plugin Runtime Planning — Security Review Checklist |
| Status | Optional companion |
| Date | 2026-06-18 |
| Planning ID | `PHASE-3D-PLANNING-001` |

> **Planning Closeout (2026-06-18):** Phase 3D Planning is **closed**
> (`PHASE-3D-PLANNING-CLOSEOUT-001`). This checklist now complements the closeout
> package — [final security boundary](phase-3d-final-security-boundary.md),
> [risk closure](phase-3d-risk-closure.md),
> [human review readiness](phase-3d-human-review-readiness.md). Every box still
> holds at the closeout baseline.

> A checklist a reviewer can run against this docs-only planning phase (and later,
> against any future implementation). Every box must hold.

## 1. Docs-only invariant

- [ ] Only files under `docs/webui/` were added / updated.
- [ ] No backend module added (`dev_web_plugin*.py`).
- [ ] No frontend component added.
- [ ] No test / smoke profile / smoke spec added.
- [ ] `toolsets.py`, runtime stores, `state.db` unchanged.
- [ ] No new HTTP / Provider / Tool write route.

## 2. No execution surface

- [ ] No plugin runtime implemented.
- [ ] No plugin loader implemented.
- [ ] No dynamic loading (`importlib` / `__import__` / path load / `pkgutil` walk).
- [ ] No remote registry / marketplace / external plugin fetch.
- [ ] No provider-generated plugin.
- [ ] No LLM-generated plugin install.
- [ ] No shell / DB / external-HTTP / production execution.
- [ ] No provider write / autonomous write.

## 3. Descriptor discipline (future contract)

- [ ] Manifest has an explicit forbidden-fields list (recursive + scalar type
      guard).
- [ ] Descriptor binds to existing Phase 3C capability IDs only.
- [ ] Descriptor permission class ≤ bound capability's class.
- [ ] Descriptor is `devOnly=true`, `productionAllowed=false`, disabled by default.
- [ ] No trust auto-upgrade; no auto-enable.

## 4. No leak

- [ ] No secret / Authorization / bearer / API key.
- [ ] No callable repr / dynamic import path.
- [ ] No production path / local plugin path / external URL / install command.
- [ ] Audit events carry safe fields only; `redactionApplied=true`; fail-closed.

## 5. Production safety

- [ ] Production Gateway PID `28428` (count 1) untouched.
- [ ] No `~/.hermes` access; no production `state.db` access.
- [ ] Dev services bind `127.0.0.1`.
- [ ] Route governance 34 / 34 / 5 / 0 / 1 / 1.
- [ ] No runtime artifact / `.claude/` committed.

## 6. Governance

- [ ] GO/NO-GO recorded ([phase-3d-go-no-go.md](phase-3d-go-no-go.md)).
- [ ] Implementation entry criteria recorded
      ([phase-3d-implementation-entry-criteria.md](phase-3d-implementation-entry-criteria.md)).
- [ ] Phase 3D Implementation is NO-GO until explicit approval.
