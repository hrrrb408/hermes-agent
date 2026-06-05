# Hermes WeChat Integration

## Production Gateway Safety

Do not use development commands to stop, restart, replace, or otherwise manage
an already deployed Hermes Gateway. A production or global gateway may be
serving real users and may be running from the global `hermes` command with
`~/.hermes` as its data directory.

Development work in this repository must use the isolated launcher:

```bash
./scripts/run-dev-hermes.sh ...
```

That script points Hermes at:

```text
Source root:  /Users/huangruibang/Code/hermes-agent-dev
HERMES_HOME:  /Users/huangruibang/Code/hermes-home-dev
```

The development environment must not modify `~/.hermes`, must not use the
global `hermes` command, and must not run `gateway run --replace`.

## Production vs Development Gateway

Production Gateway:

- Uses the deployed Hermes installation.
- Uses the production Hermes home, usually `~/.hermes`.
- Owns the production `gateway.pid`, runtime state, platform credentials, and
  real messaging callbacks.
- Must not be stopped or replaced during development dry-runs.

Development Gateway:

- Uses the development source tree and `hermes-home-dev`.
- Uses dev-only gateway metadata such as `gateway-dev.pid`.
- Defaults to local-only host `127.0.0.1`.
- Defaults to port `18080`.
- Does not connect to real WeChat by default.
- Is currently exposed through safe status and dry-run commands, not a long
  running service.

## Dev WeChat Message Dry-Run

Use `dev-wechat-message` to simulate an inbound WeChat text message:

```bash
./scripts/run-dev-hermes.sh dev-wechat-message "Hermes 记忆系统现在做到哪了" --no-llm
```

The dry-run flow is:

```text
Simulated WeChat text
→ Dev WeChat adapter
→ Agent Runtime context builder
→ Runtime memory injection
→ Prompt preview
```

The command does not start the gateway, does not connect to WeChat, does not
send a message, and does not call the model when `--no-llm` is used.

The WeChat adapter does not operate on `memory_router` directly. Long-term
memory is loaded only through the Agent Runtime memory injection layer.

## Dev Gateway Isolation

The development gateway isolation defaults are:

```text
Host:      127.0.0.1
Port:      18080
PID file:  <HERMES_HOME>/gateway-dev.pid
Log file:  <HERMES_HOME>/gateway-dev.log
```

Check status with:

```bash
./scripts/run-dev-hermes.sh gateway-dev status
```

The current safe implementation is status-only. It intentionally does not start
or stop any gateway process. Use `dev-wechat-message` for runtime validation
until a local callback server is added.

## Recommended Real WeChat Path

Do not start by wiring a personal WeChat hook into production. Personal hooks
are fragile and create unnecessary account and privacy risk.

Recommended progression:

1. Keep using `dev-wechat-message` for dry-run validation.
2. Add a local-only HTTP callback on `127.0.0.1:18080`.
3. Test `GET /wechat/callback` and `POST /wechat/callback` locally with `curl`.
4. Use a WeChat official account test account or a WeCom self-built app.
5. Only after isolated testing, plan a controlled production Gateway migration.

## Architecture Boundary

Messaging platforms should remain transport adapters:

```text
WeChat / Gateway / CLI / Web / API
= receive and send messages

Agent Runtime / Prompt Builder
= build context, load memory, call the model

Memory Context Loader
= select and load relevant long-term memory
```

Do not put memory routing logic directly in the WeChat layer.
