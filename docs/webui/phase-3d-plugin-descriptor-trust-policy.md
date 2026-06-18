# Phase 3D — Plugin Descriptor Trust Classification

Source of truth: `hermes_cli/dev_web_plugin_descriptor_policy.py`
(`check_descriptor_policy`).

## Trust / status coherence

| Trust level | Allowed status |
|-------------|----------------|
| `trusted_builtin_code` / `trusted_static_descriptor` | visible, disabled, blocked, … (visible requires one of these two) |
| `dev_reviewed_descriptor` | disabled, blocked |
| `experimental_disabled_descriptor` | disabled, blocked, planned |
| `external_forbidden` / `unknown_forbidden` / `production_forbidden` | **blocked** (required) |

## Rules

- `status=visible` **requires** a verified trust level
  (`trusted_builtin_code` / `trusted_static_descriptor`).
- A forbidden trust level **must** be `blocked`.
- `experimental_disabled_descriptor` must be disabled / blocked / planned.
- A forbidden permission class must be disabled / blocked.

## Trust self-upgrade rejection

A descriptor bound to a forbidden capability may **not** carry a verified trust
level. This blocks the trust self-upgrade path (a descriptor cannot launder a
forbidden binding into a verified descriptor). Verified trust on a forbidden
binding → rejected fail-closed.

## Non-grant

Trust classification never grants permission. A descriptor cannot self-promote,
cannot be auto-enabled, and cannot upgrade its trust from a provider response /
workflow output / UI input / local path / remote source.
