# Phase 3D — Non-goals & Forbidden Scope

| Field | Value |
|-------|-------|
| Phase | 3D (Planning) |
| Title | Plugin Runtime — Non-goals & Forbidden Scope (Frozen) |
| Status | Frozen (docs-only planning; Plugin Runtime **not started**) |
| Date | 2026-06-18 |
| Planning ID | `PHASE-3D-PLANNING-001` |
| Policy ID | `PHASE-3D-NON-GOALS-001` |

> Phase 3D Planning is a **planning phase**, not an implementation phase. This
> document freezes the explicit non-goals and the forbidden scope. Every item
> below is a P0 stop condition if violated in any future implementation (see
> [phase-3d-risk-register.md](phase-3d-risk-register.md), `PLUG-P0-*`).

## 1. Non-goals (explicit)

Phase 3D Planning explicitly does **not** pursue any of the following — now or as
an implicit consequence of this planning phase:

- No plugin runtime implementation in this planning phase.
- No dynamic import (no `importlib`, no `__import__`, no path-based load).
- No user plugins directory.
- No remote registry.
- No marketplace.
- No external plugin fetch.
- No package install.
- No provider-generated plugin.
- No LLM-generated plugin installation.
- No shell execution.
- No DB mutation.
- No external HTTP execution.
- No production operation.
- No permission grant by plugin.
- No Tool policy bypass.
- No Provider live gate bypass.
- No Workflow approval bypass.
- No autonomous write.
- No production rollout.
- No new route by default.

## 2. Forbidden scope (frozen prohibition)

The following are **forbidden** in any future Phase 3D implementation unless each
is covered by a **separately authorized** phase that carries its own scope freeze,
threat model, and GO / NO-GO:

1. Python `importlib` dynamic import.
2. `__import__` dynamic import.
3. Path-based loading of a Python file.
4. Reading a user's local plugin directory.
5. Reading arbitrary `plugins/` directories for discovery.
6. Scanning the local filesystem to find plugins.
7. Loading remote JS plugins.
8. Installing external packages.
9. Executing external plugin code.
10. Executing built-in plugin code.
11. Executing provider-generated plugins.
12. Executing LLM-generated tools.
13. A marketplace.
14. A remote registry.
15. Remote manifest fetch.
16. External plugin fetch.
17. Accessing an arbitrary `externalUrl` / `downloadUrl`.
18. A new capability execution path.
19. A new Tool write route.
20. A new Provider route.
21. A new HTTP route.
22. Provider write.
23. Provider auto-write.
24. Autonomous write.
25. Workflow auto-advance.
26. Workflow autonomous write.
27. Shell execution.
28. Database mutation.
29. External HTTP tool execution.
30. Production operation.
31. Reading `OPENAI_API_KEY` or checking for a real key.
32. A real Provider request.
33. An external network call.
34. Production rollout.
35. `~/.hermes` access.
36. Production `state.db` access.
37. Modifying the global `hermes` command.
38. Running `setup-hermes.sh`.
39. Committing runtime artifacts.
40. Committing `.claude/`.

## 3. What planning may do instead

- Declare a **static, reviewed** plugin descriptor model
  ([phase-3d-plugin-manifest-contract.md](phase-3d-plugin-manifest-contract.md)).
- Freeze the **trust boundary**
  ([phase-3d-trust-boundary.md](phase-3d-trust-boundary.md)).
- Freeze the **lifecycle model** (descriptor → validated → visible → disabled)
  ([phase-3d-plugin-lifecycle-model.md](phase-3d-plugin-lifecycle-model.md)).
- Freeze the **execution isolation model**
  ([phase-3d-execution-isolation-model.md](phase-3d-execution-isolation-model.md)).
- Bind descriptors to **existing** Phase 3C capability IDs only
  ([phase-3d-capability-registry-integration.md](phase-3d-capability-registry-integration.md)).
- Record the **threat model**
  ([phase-3d-threat-model.md](phase-3d-threat-model.md)) and **risk register**
  ([phase-3d-risk-register.md](phase-3d-risk-register.md)).

## 4. What must hold (future implementation gate)

Any future implementation must affirm at runtime:

- No `importlib` / `__import__` / `importlib.util.spec_from_file_location` call
  path in any plugin module.
- No `subprocess` / `os.system` / `eval` / `exec` / `shell=True` path.
- No `requests` / `httpx` / `urllib` / `aiohttp` fetch for plugin discovery.
- No filesystem walk of a user plugin directory.
- No remote registry / marketplace URL configured or fetched.
- An audit event `plugin_no_dynamic_loading_checked` confirming these invariants.

## 5. Manual one-shot live provider execution — out of scope

The manual one-shot live provider execution remains **separately gated** (Phase
3B-Live-Enablement) and is **not** part of Phase 3D. A plugin descriptor must not
reference or trigger it.

## 6. Cross-references

- [Phase 3D planning](phase-3d-planning.md)
- [Phase 3D scope freeze](phase-3d-plugin-runtime-scope-freeze.md)
- [Phase 3D threat model](phase-3d-threat-model.md)
- [Phase 3D risk register](phase-3d-risk-register.md)
- [Phase 3C no dynamic loading policy](phase-3c-no-dynamic-loading-policy.md)
