#!/usr/bin/env bash
set -euo pipefail

export HERMES_HOME="/Users/huangruibang/Code/hermes-home-dev"
HERMES_BIN="/Users/huangruibang/Code/hermes-agent-dev/.venv/bin/hermes"

if [ "$#" -eq 0 ]; then
  exec "$HERMES_BIN" chat
fi

exec "$HERMES_BIN" "$@"
