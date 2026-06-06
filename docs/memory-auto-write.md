# Automatic Memory Writer V2.1

## Architecture

Automatic memory evaluation runs after Agent Runtime produces a reply:

```text
user message
-> Memory Candidate Extractor
-> Memory Scorer
-> Similarity and Tag Analysis
-> Safety Decision
-> Optional Memory Writer
```

The implementation is rule-based. It does not call an LLM, use embeddings, or
use a vector database. Existing `memory-add` and `memory-update` writer paths
remain responsible for persistence.

## Memory Writer V2.1 Safety Model

The safety model separates candidate evaluation from file modification. A
dry-run always evaluates with the production rules but never writes files.
Runtime writes require explicit configuration and a safe `WRITE` or `UPDATE`
decision.

The candidate is based primarily on the user message. Assistant output is
supplemental context and cannot independently authorize a write.

## Decision Types

- `WRITE`: high-confidence new fact with no related existing memory.
- `UPDATE`: high-confidence match satisfying every update safety condition.
- `REVIEW`: useful but ambiguous, related, protected, or disabled by policy.
- `SKIP`: low-value, temporary, casual, one-off, or explicitly excluded.
- `SKIP_DUPLICATE`: existing memory already contains essentially identical
  information.

`REVIEW`, `SKIP`, and `SKIP_DUPLICATE` never modify memory files.

## MemoryCandidate

```text
summary
category
tags
title
type
importance
ttl
source_confidence
```

`source_confidence` distinguishes user-confirmed facts from assistant-only
inferences.

## Scoring

Candidates are scored from 0 to 100. Progress terms, commit hashes, completion
phrases, verification results, and project-specific terms add points. Casual
chat, one-off questions, short messages, and assistant-only inference reduce
the score.

Defaults:

- write threshold: 80
- review threshold: 65

## WRITE Rules

`WRITE` requires a score of at least 80, an active existing category, valid
candidate fields, and no existing memory above the candidate similarity
threshold. Actual persistence additionally requires auto-write to be enabled
and a non-dry-run runtime call.

## UPDATE Rules

Automatic update requires all of the following:

- score at least 80
- auto-write enabled
- auto-update enabled separately
- same category
- active target
- overall similarity at least 90%
- at least one non-generic core tag overlap
- title similarity at least 85% or summary similarity at least 90%
- target is not protected

Failure of any update condition produces `REVIEW`, not a lower-confidence
update.

## REVIEW Rules

Review is used for scores between 65 and 79, related memories between the
candidate and update thresholds, protected targets, missing categories,
generic-only tag overlap, disabled updates, or other ambiguous matches.

No review queue is created in V2.1. The decision is logged and shown in dry-run
output only.

## SKIP Rules

Candidates are skipped for low scores, casual chat, one-off questions,
assistant-only unsupported claims, invalid fields, and explicit user requests
such as `不要记住`, `别保存`, or `这只是临时的`.

## SKIP_DUPLICATE Rules

An existing same-category memory is considered a duplicate when overall
similarity is at least 98% and title or summary similarity is at least 95%.
Duplicates are neither added nor updated.

## P0 Protection

Memories with `importance: P0` cannot be automatically updated. Related
candidates produce `REVIEW` with `TARGET_P0_PROTECTED`, unless they are near
identical and safely skipped as duplicates.

## Permanent Memory Protection

Memories with `ttl: permanent` cannot be automatically updated. Related
candidates produce `REVIEW` with `TARGET_PERMANENT_PROTECTED`, unless they are
near-identical duplicates.

## Auto Update Switch

Automatic updates are riskier than automatic additions because they can
overwrite important historical facts. They therefore use a separate switch and
are disabled by default.

```yaml
memory:
  auto_write:
    enabled: false
    allow_updates: false
```

Environment overrides:

```bash
HERMES_MEMORY_AUTO_WRITE=true
HERMES_MEMORY_AUTO_UPDATE=true
```

Enabling auto-write alone does not enable updates.

## Category Creation Guard

Automatic category creation is disabled by default:

```yaml
memory:
  auto_write:
    auto_create_categories: false
```

```bash
HERMES_MEMORY_AUTO_CREATE_CATEGORIES=true
```

When a category is missing and creation is disabled, the decision is `REVIEW`.

## Similarity Breakdown

Text is normalized by lowercasing English, removing common punctuation, and
collapsing whitespace while preserving Chinese text. `SequenceMatcher`
calculates:

- title similarity
- summary similarity
- combined title and summary similarity

Similarity values are stored as ratios from 0 to 1 and displayed as
percentages.

## Core Tag Overlap

Tag comparison reports all overlap and core overlap. Generic tags such as
`hermes`, `project`, `status`, `memory`, and `system` do not independently
authorize updates. At least one specific tag such as `wechat`, `gateway`,
`runtime`, `scan-login`, `auth`, or `context-loader` must overlap.

## Dry-run Examples

```bash
./scripts/run-dev-hermes.sh memory-auto-test "Hermes 微信 Gateway 已接入"
./scripts/run-dev-hermes.sh memory-auto-test "谢谢哈哈"
./scripts/run-dev-hermes.sh memory-auto-test "Hermes 微信 Gateway 已接入" --format json
```

Dry-run output includes score breakdown, match details, similarity breakdown,
tag overlap, protection status, configuration switches, decision reasons, and
whether files would be modified.

## Runtime Failure Isolation

The runtime integration remains best-effort. Evaluation and persistence are
wrapped in exception handling after `post_llm_call`. Any failure records a
warning and cannot fail the user reply, session history, Agent Runtime, or
Gateway.

## Why Auto Update Is Disabled by Default

Adding a new record preserves existing history. Updating an old record can
silently replace a high-value or permanent fact. V2.1 therefore requires a
higher similarity threshold, core tag overlap, protection checks, and a
separate explicit update switch.
