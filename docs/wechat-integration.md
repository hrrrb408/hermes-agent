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
- Uses a dev-only WeChat state directory under `gateway/dev/wechat`.
- Can be run in the foreground as a scan-login development gateway.
- Can use another WeChat account for isolated testing.

The production Gateway currently running as PID `1717` is the user's active
Hermes Gateway. Do not stop, restart, replace, or otherwise manage it from
development commands.

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
Host:              127.0.0.1
Port:              18080
PID file:          <HERMES_HOME>/gateway-dev.pid
Runtime state:     <HERMES_HOME>/gateway-dev-state.json
State dir:         <HERMES_HOME>/gateway/dev
Wechat state dir:  <HERMES_HOME>/gateway/dev/wechat
Log file:          <HERMES_HOME>/logs/gateway-dev.log
```

Check status with:

```bash
./scripts/run-dev-hermes.sh gateway-dev status
```

Start the development scan-login Gateway in the foreground with:

```bash
./scripts/run-dev-hermes.sh gateway-dev run
```

This command uses the development source tree, `hermes-home-dev`, the
dev-only PID file, and the dev-only WeChat state directory. It does not use
`--replace`. If no dev Weixin credentials are present, it displays the QR login
flow so a test WeChat account can scan it.

Stop only the development Gateway with:

```bash
./scripts/run-dev-hermes.sh gateway-dev stop
```

`gateway-dev stop` reads only `gateway-dev.pid` and refuses to stop PID `1717`
or any process whose command line cannot be verified as the dev gateway.

Do not use these commands for development testing:

```bash
hermes gateway stop
hermes gateway restart
hermes gateway run --replace
```

Those commands manage the normal Gateway surface and can affect the production
Gateway when pointed at the production environment.

## Dev Gateway User Access

`gateway-dev` defaults to safe local testing behavior: it does not open access
to every sender unless explicitly requested.

For quick local testing, run:

```bash
./scripts/run-dev-hermes.sh gateway-dev run --allow-all-users
```

This sets the existing Gateway allow-all environment only inside the
development Gateway process. It does not write `~/.hermes/.env`, does not
modify production config, and does not affect the production Gateway.

The safer option is to allow only known Weixin sender IDs:

```bash
./scripts/run-dev-hermes.sh gateway-dev run --allowed-user "sender-id"
```

`--allowed-user` is repeatable. The equivalent development-only environment
variables are:

```bash
HERMES_DEV_GATEWAY_ALLOW_ALL_USERS=true
HERMES_DEV_GATEWAY_ALLOWED_USERS="user1,user2"
```

Do not modify `~/.hermes/.env` to test the development Gateway, and do not use
allow-all for the production Gateway.

`gateway-dev run` also forces secret redaction on for the dev process by
default. Only the dev-specific `HERMES_DEV_GATEWAY_REDACT_SECRETS=false`
override disables it.

## Terminal QR Rendering

The Weixin scan-login flow always prints the QR URL. If terminal QR rendering
fails because the optional `qrcode` package is missing, open the printed URL in
a browser or scan it directly.

To enable terminal QR rendering in the development virtual environment:

```bash
.venv/bin/pip install "qrcode[pil]"
```

## Dev Gateway Runtime Status

`gateway-dev run` writes development runtime metadata to:

```text
<HERMES_HOME>/gateway-dev-state.json
```

The state file records the dev scan-login mode, platform, pid, Hermes home,
dev state directories, auth mode, secret-redaction setting, and memory runtime
settings. `gateway-dev status` is read-only and, when a dev gateway is running,
prefers this runtime state over the current shell environment so it can show
the actual process mode, for example:

```text
Dev user access: allow all users (dev only, running process)
```

`--allow-all-users` only applies to the current development gateway process.
Use `--allowed-user` for a narrower test allowlist.

## Dev Gateway Memory Logs

The development Gateway can emit a runtime memory injection summary. Use:

```bash
./scripts/run-dev-hermes.sh gateway-dev run --allow-all-users --verbose
```

The summary logs only operational metadata:

```text
Runtime memory injection: enabled
Selected categories: hermes
Loaded memories: MEM-HERMES-002(category=hermes, status=active), MEM-HERMES-001(category=hermes, status=active)
Skipped memories: MEM-HERMES-003(status=archived)
Memory context chars: 1234
```

It does not print full memory records, full prompts, tokens, API keys, or
Weixin credentials.

## Recommended Real WeChat Path

Do not start by wiring a personal WeChat hook into production. Personal hooks
are fragile and create unnecessary account and privacy risk.

Recommended progression:

1. Keep using `dev-wechat-message` for dry-run validation.
2. Use `gateway-dev run` for isolated scan-login testing with a test WeChat
   account.
3. Confirm messages enter Agent Runtime and receive runtime memory injection.
4. Only after isolated testing, plan a controlled production Gateway migration.

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
