# Automatic Memory Writer V2

## Architecture

Automatic memory writing runs after Agent Runtime has produced a reply:

```text
user message
-> assistant response
-> Memory Candidate Extractor
-> Memory Scorer
-> Dedup
-> Memory Writer
```

The first version is rule-based. It does not call an LLM, does not use
embeddings, and does not use a vector database. Runtime failures are logged as
warnings and must not fail the user-facing reply.

## MemoryCandidate

The runtime writer evaluates a lightweight structure:

```text
summary
category
tags
title
type
importance
ttl
```

Categories are inferred from message content. Hermes development terms such as
`gateway`, `wechat`, `memory`, `runtime`, and `agent` map to `hermes`. Travel
terms such as `travel`, `flight`, and `hotel` map to `travel`.

## Scoring

Candidates are scored from 0 to 100.

Positive signals:

- completion or implementation keywords: +20
- git commit hash: +20
- `已完成`, `已推送`, `验证通过`, or `PASS`: +15
- `修改文件`, `新增命令`, or `验收结果`: +15

Negative signals:

- casual chatter such as `你好`, `哈哈`, `谢谢`: -100
- one-off questions such as `天气` or `今天几点`: -100
- messages shorter than 20 characters: -20

The default write threshold is `score >= 70`.

## Dedup

Before writing, the candidate is compared with existing memory items in the
same category using `difflib.SequenceMatcher`. The writer checks titles,
summaries, tags, and a bounded prefix of record text.

If similarity is at least 80%, the decision is `UPDATE`; otherwise the decision
is `WRITE`.

## Auto Update

When enabled and a similar memory exists, the writer reuses the existing
`memory-update` path through `hermes_cli.memory_router.update_memory_item`.
New memories reuse the memory router writer path through
`create_memory_item` and `allocate_memory_id`.

Events are appended to `memory/events.jsonl` with:

```json
{"event":"memory_auto_add","source":"runtime"}
{"event":"memory_auto_update","source":"runtime"}
```

## Config

Automatic writes are disabled by default.

```yaml
memory:
  auto_write:
    enabled: false
```

The environment variable overrides config:

```bash
HERMES_MEMORY_AUTO_WRITE=true
```

When disabled, runtime evaluation can still log a candidate decision, but it
does not modify `MEMORY.md`, category indexes, records, snapshots, or events.

## Dry Run

Use `memory-auto-test` to evaluate extraction, scoring, and dedup without
writing:

```bash
./scripts/run-dev-hermes.sh memory-auto-test "已完成开发版微信 Gateway 并推送"
```

The output includes candidate summary, inferred category, score, decision,
auto-write enablement, and the nearest existing memory if any.
