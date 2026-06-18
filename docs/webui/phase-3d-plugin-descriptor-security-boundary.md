# Phase 3D — Plugin Descriptor Security Boundary

## Summary

Phase 3D implements a **static dev-only plugin descriptor registry skeleton**.
It is descriptor-only, disabled-by-default, capability-bound, and read-only. It
does not execute plugins, does not implement a plugin runtime, does not
implement a plugin loader, does not dynamically load code, does not read local
plugin directories, does not fetch remote registries, does not implement a
marketplace, and does not fetch external plugins.

## What the registry does NOT do (red lines)

- No plugin runtime execution; no plugin loader execution.
- No dynamic loading (`importlib` / `__import__` / path load / directory scan).
- No local plugin directory loading.
- No remote registry / marketplace / external plugin fetch.
- No provider-generated plugin; no LLM-generated plugin install.
- No shell execution, database mutation, external HTTP execution, production
  operation.
- No provider write; no autonomous write; no production rollout.
- No live provider request; no real API-key read; no external network call.
- No new HTTP route (baseline 34/34/5/0/1/1 unchanged).
- No `~/.hermes` access; no production `state.db` access.

## What the registry DOES

- Describes 12 descriptors binding only to existing Phase 3C capabilityIds.
- Inherits the most-restrictive permission class from bindings; rejects
  escalation + trust self-upgrade fail-closed.
- Rejects forbidden / nested / alias forbidden fields recursively, fail-closed.
- Surfaces a value-free `/status pluginDescriptorRegistry` block and a read-only,
  no-leak, accessible UI panel.

## Verification

- Recursive forbidden-field scan + alias coverage (schema tests).
- Permission-inheritance + escalation-rejection (binding policy tests).
- Trust/status coherence + self-upgrade rejection (trust policy tests).
- No-execution / no-dynamic-loading AST guards (no `importlib` / `subprocess` /
  remote fetch / directory walk in any module).
- `/status` + read-model + UI no-leak (status-api, security, frontend no-leak
  tests; smoke profile).
- Route governance preserved (34 OpenAPI / 34 runtime business paths).

## Production isolation

Production Gateway PID 28428 (count 1) was not stopped / restarted / replaced /
signaled / reconfigured. Dev services bind `127.0.0.1` only. No `~/.hermes`
access; no production `state.db` access; no runtime artifacts or `.claude/`
committed.
