# Phase 3H Filesystem Boundary Planning

| Field | Value |
|-------|-------|
| Phase | 3H (Sandbox Proof Planning — Filesystem Boundary) |
| Title | Real Plugin Runtime — Phase 3H Filesystem Boundary Planning |
| Planning ID | `PHASE-3H-PLANNING-001` |
| Date | 2026-06-19 |
| Branch | `dev-huangruibang` |
| Status | Docs-only planning — does **not** implement filesystem enforcement |

> This document is docs-only.
> This document plans filesystem boundary proof requirements only.
> This document does not implement filesystem enforcement.
> This document does not implement sandbox proof.
> This document does not authorize runtime execution.
> This document does not authorize production rollout.
> This document does not authorize new routes.

## A. Filesystem boundary summary

This document plans the filesystem boundary requirements that a future sandbox proof would
need to satisfy. It does not implement any filesystem enforcement, does not create a store,
and does not authorize implementation.

## B. Allowed future proof discussion

A future proof may discuss, as documentation only:

- read-only test fixtures;
- temporary isolated directories;
- denylist / allowlist planning;
- no `~/.hermes`;
- no production `state.db`;
- no production config;
- no secret files;
- no plugin install directories;
- no runtime store writes unless separately authorized.

```
"Allowed future proof discussion" means planning prose only.
It does not mean any of these is implemented or authorized now.
```

## C. Required future evidence

A future separately-authorized proof would need to produce, none of which is produced here:

- path boundary definition;
- forbidden path verification (including `~/.hermes`, production `state.db`, production
  config, secret files, plugin install directories);
- temporary-directory cleanup demonstration;
- write-denial demonstration outside the approved boundary;
- symlink traversal risk planning;
- path escape risk planning.

```
This document produces no evidence.
This document only lists what a future proof would need.
```

## D. Stop conditions

```
Any ambiguity around ~/.hermes means STOP.
Any ambiguity around production state.db means STOP.
Any uncontrolled write path means STOP.
Any symlink / path traversal ambiguity means STOP.
```

Any unresolved P0 means STOP toward implementation.

## E. Planning verdict

```
Filesystem proof implementation remains NO-GO.
This document authorizes no filesystem enforcement, no store, no runtime, no route, no
production change.
```

## Cross-references

- [Phase 3H sandbox proof planning](phase-3h-sandbox-proof-planning.md)
- [Phase 3H production isolation constraints](phase-3h-production-isolation-constraints.md)
- [Phase 3H GO / NO-GO](phase-3h-go-no-go.md)
