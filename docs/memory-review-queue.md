# Memory Review Queue V1

## Overview

The Memory Review Queue persists automatic memory candidates that require human
approval. Queue items are not formal long-term memories.

## Why Review Queue Exists

`REVIEW` decisions and blocked `WRITE` or `UPDATE` decisions would otherwise be
lost after runtime evaluation. The queue provides a human-controlled path to
inspect, approve, or reject them.

## Storage Layout

```text
HERMES_HOME/memory/reviews/
├── items/
│   └── MR-<timestamp>-<fingerprint>.json
├── events.jsonl
└── .queue.lock
```

This directory is separate from formal indexes, records, and
`memory/events.jsonl`.

## Review Item Schema

Each item stores a review ID, status, timestamps, occurrence count,
fingerprint, minimal source metadata, original decision, proposed action,
candidate fields, evaluation details, optional matched memory, approval or
rejection data, last error, and schema version.

Full user messages, assistant responses, prompts, credentials, cookies, and
tokens are not stored.

## Decisions That Enter Queue

- `REVIEW`
- blocked `WRITE` when automatic writes are disabled
- blocked `UPDATE` when updates are disabled or safety guards prevent update
- missing-category candidates when automatic category creation is disabled

## Decisions That Do Not Enter Queue

- `SKIP`
- `SKIP_DUPLICATE`
- explicit user requests not to remember
- empty candidates
- candidates rejected by queue capacity limits

## Runtime Enqueue Flow

Agent Runtime evaluates memory after `post_llm_call`. When the queue is enabled,
eligible evaluations are enqueued. Queue failures are warnings and cannot fail
the reply, session history, Agent Runtime, or Gateway.

## Exact Fingerprint Dedup

The fingerprint is SHA-256 over normalized category, title, summary, and sorted
tags. An identical pending fingerprint increments `occurrence_count` and
updates `last_seen_at` instead of creating another item.

## memory-review-list

```bash
hermes memory-review-list
hermes memory-review-list --all --format json
```

## memory-review-show

```bash
hermes memory-review-show MR-... --format json
```

## memory-review-enqueue

```bash
hermes memory-review-enqueue "Hermes 微信 Gateway 已接入"
hermes memory-review-enqueue "..." --dry-run
```

This command explicitly writes only to the review queue. It never writes formal
memory.

## memory-review-approve

```bash
hermes memory-review-approve MR-... --action write --dry-run
hermes memory-review-approve MR-... --action update --target MEM-... --dry-run
```

Real approval is supported but should only be used after inspecting the item.

## memory-review-reject

```bash
hermes memory-review-reject MR-... --reason "Not a durable fact"
```

Rejecting an item does not modify formal memory.

## Approval Revalidation

Approval reloads current categories and memory indexes, recalculates
similarities and tag overlap, checks duplicates, and applies current P0 and
permanent protection. Stored evaluation results are never blindly trusted.

## WRITE Approval

WRITE approval checks that the category exists and remains active and that no
98% duplicate now exists. It then reuses `allocate_memory_id` and
`create_memory_item`.

## UPDATE Approval

UPDATE approval requires an explicit target. It reuses
`update_memory_item` only after same-category, active-status, similarity, core
tag, and protection checks pass.

## P0 and Permanent Protection

P0 and permanent targets cannot be updated through Review Queue approval.
Explicit manual `memory-update` remains the separate operator-controlled path.

## Atomic Writes and Locking

Item JSON uses the repository's temp-file, fsync, and `os.replace` atomic JSON
writer. Queue mutations are serialized with `fcntl.flock` on POSIX, with a
best-effort fallback elsewhere.

## Review Events

`memory/reviews/events.jsonl` records create, duplicate-seen, approve, reject,
and approval-failed events. Formal memory events remain in the separate formal
event log.

## Configuration

```yaml
memory:
  review_queue:
    enabled: false
    path: memory/reviews
    enqueue_review: true
    enqueue_blocked_write: true
    enqueue_blocked_update: true
    max_pending: 500
    exact_dedup: true
```

## Environment Variables

```bash
HERMES_MEMORY_REVIEW_QUEUE=true
HERMES_MEMORY_REVIEW_MAX_PENDING=500
```

## Privacy and Redaction

Normal logs contain review ID, decision, action, category, title, score, reason
codes, matched ID, and occurrence count only. Queue items contain only the
candidate fields needed for review.

## Failure Isolation

Queue capacity, lock, serialization, and filesystem errors do not affect the
user-facing response. Runtime catches and logs failures as warnings.

## End-to-End Isolated Validation

`tests/test_memory_review_queue_e2e.py` exercises real approval writes and
updates against a pytest `tmp_path` Hermes home. It covers protected and
missing update targets, duplicate races, dry-run behavior, idempotency,
failure state preservation, event integrity, and concurrent approval.

The fixture sets `HERMES_HOME` to the temporary directory and asserts that it
is not the real development home. It never uses the production or persistent
development memory data.

Run it with:

```bash
.venv/bin/python -m pytest tests/test_memory_review_queue_e2e.py -v
```

## Dev WeChat Review Queue Pilot

The development WeChat pilot enables automatic candidate enqueue while keeping
all formal memory mutation disabled. It does not approve candidates, create
memory IDs, update records, or create categories.

Use a narrow sender allowlist:

```bash
./scripts/run-dev-hermes.sh gateway-dev run \
  --allowed-user "<test-wechat-user-id>" \
  --memory-review-queue \
  --memory-review-max-pending 20 \
  --verbose
```

`--allow-all-users` is available for short development sessions, but it grants
all senders access to that dev process. Prefer `--allowed-user`.

The pilot defaults to 20 pending candidates and accepts values from 1 through
500. It sets these values only in the current gateway-dev process:

```text
HERMES_MEMORY_REVIEW_QUEUE=true
HERMES_MEMORY_REVIEW_MAX_PENDING=20
HERMES_MEMORY_AUTO_WRITE=false
HERMES_MEMORY_AUTO_UPDATE=false
HERMES_MEMORY_AUTO_CREATE_CATEGORIES=false
```

It does not edit `.env`, `~/.hermes`, or persistent global configuration. If
any formal mutation variable is already truthy (`true`, `1`, `yes`, or `on`),
startup fails closed instead of silently overriding the unsafe environment.

Status and review inspection commands:

```bash
./scripts/run-dev-hermes.sh gateway-dev status
./scripts/run-dev-hermes.sh dev-info
./scripts/run-dev-hermes.sh memory-review-list
./scripts/run-dev-hermes.sh memory-review-show <review_id>
./scripts/run-dev-hermes.sh memory-review-approve \
  <review_id> --action write --dry-run
./scripts/run-dev-hermes.sh memory-review-reject \
  <review_id> --reason "Development WeChat review queue pilot completed"
```

Do not omit `--dry-run` for approval against the real development home.
Rejected pilot candidates remain auditable; there is intentionally no
review-delete or clear-all command.

### Manual Pilot Runbook

1. Confirm the development Gateway is stopped:

   ```bash
   ./scripts/run-dev-hermes.sh gateway-dev status
   ```

2. Remove inherited formal-write switches without editing any `.env` file:

   ```bash
   unset HERMES_MEMORY_AUTO_WRITE
   unset HERMES_MEMORY_AUTO_UPDATE
   unset HERMES_MEMORY_AUTO_CREATE_CATEGORIES
   ```

3. Start the pilot with `--allowed-user` as shown above. For a short test when
   the sender ID is unknown, replace it with `--allow-all-users`.

4. Send a durable project progress message from the test WeChat account, for
   example: `已完成 Hermes Memory Review Queue 端到端隔离测试，10 项测试全部通过。`

5. In another terminal, run `gateway-dev status`. Confirm the review queue is
   enabled, all three formal mutation modes are disabled, and pilot safety is
   `PASS`.

6. Run `memory-review-list`, then `memory-review-show <review_id>`.

7. Run approval only with `--dry-run`.

8. End the candidate with `memory-review-reject` and a clear audit reason.

9. Stop only the development Gateway:

   ```bash
   ./scripts/run-dev-hermes.sh gateway-dev stop
   ```

   Never use `hermes gateway stop` for this workflow.

10. Confirm the production Gateway remains running with a read-only process
    check such as `ps -p 1717 -f`.

Pilot logs contain decision, score, category, proposed action, review ID,
occurrence count, and reason codes. They do not contain complete messages,
assistant replies, candidate summaries, prompts, records, cookies, or secrets.

## Dev WeChat Read-only Review Commands

The first WeChat review command surface is intentionally read-only. It is
available only in `gateway-dev`, requires an active Review Queue pilot with
Safety `PASS`, and runs after Gateway user authorization.

Supported commands:

```text
/memory-review status
/memory-review list
/memory-review list 10
/memory-review show <review_id>
/memory-review help
```

`list` defaults to five pending candidates and accepts limits from 1 through
10. `show` uses a strict Review ID pattern and reads only the corresponding
queue item. Paths, shell syntax, subprocesses, and arbitrary JSON filenames
are not accepted.

The handler returns directly from the authorized gateway dispatch path. It
does not call the LLM, enter Agent Runtime, enqueue another candidate, update
occurrence counts, or write Review or formal memory events. Normal messages
continue through Agent Runtime unchanged.

WeChat does not support review `approve`, `reject`, `write`, `update`,
`delete`, `clear`, or `archive`. Formal review remains a terminal workflow.
For the real development home, start with:

```bash
./scripts/run-dev-hermes.sh memory-review-approve \
  <review_id> --action write --dry-run
```

Replies are limited to 2000 characters. Detail output is formatted from an
explicit field allowlist; prompts, original messages, assistant replies,
tokens, cookies, API keys, sessions, and complete formal records are never
returned. Titles, summaries, tags, and reason codes are individually bounded.

If the pilot is disabled, `/memory-review ...` is still intercepted by the
development Gateway and returns a pilot-disabled message without reaching the
LLM. Production Weixin configuration does not include this dev-only handler.

## Dry-run Examples

Approval dry-run reloads current memory and reports what would happen without
modifying the review item, review events, or formal memory.

## Why Review Queue Is Disabled by Default

Review items persist candidate information from conversations. Although they
are not formal memories, persistence has privacy and storage implications, so
runtime enqueue requires explicit opt-in.
