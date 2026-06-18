# PLUG-SMOKE-3D-H1-001 — Smoke / Preservation / Production Isolation

**Lens 12.** Smoke, preservation, and production isolation hold.

## Scope

- A new smoke profile `phase3d_h1_plugin_descriptor_registry_hardening` is wired
  into `run-dev-webui-execute-audit-smoke.sh` (case statement, usage, help,
  profile body, spec mapping, `all` aggregate) and into the default `all` run.
- The H1 smoke spec asserts: the `/status` block exists; descriptor count = 12;
  every frozen flag false; counts partition (3 / 4 / 5); route governance
  `34/34/5/0/1/1`; no plugin / descriptor route; UI panel + runtime-disabled
  banner; describes-only / does-not-grant-permission; blocked dynamic / remote /
  marketplace / production descriptors; badges carry text labels; no leak.
- `all` includes `phase3d_plugin_descriptor_registry_static` and
  `phase3d_h1_plugin_descriptor_registry_hardening`, and excludes the manual
  one-shot live profile, plugin execution, dynamic plugin runtime, local plugin
  directory loading, remote registry, marketplace, and external plugin fetch.
- No smoke run reads `OPENAI_API_KEY`, calls external network, accesses
  `~/.hermes`, or accesses production `state.db`.
- Phase 3D / 3C / 3C-H1 / 2A–2E / 3A / 3A-H1 / 3B / 3B-H1 / Live preservation
  tests pass.
- Production Gateway PID 28428 (count 1) is unchanged; not stopped / restarted /
  replaced / signaled. Dev Gateway stays stopped; Dashboard not started; 5180 /
  5181 free. No runtime artifact or `.claude` staged.

## Evidence

- `apps/hermes-dev-webui/tests/smoke/phase-3d-h1-plugin-descriptor-registry-hardening-smoke.spec.ts`
- `scripts/run-dev-webui-phase3d-hardening-audit.sh`
- `scripts/run-dev-webui-execute-audit-smoke.sh` (edited).

## Result

PASS. The hardening profile runs in `all`; forbidden profiles never run;
production isolation is preserved.
