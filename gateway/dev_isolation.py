"""Development gateway isolation helpers.

These helpers describe a dev-only gateway surface without starting or stopping
any real gateway process. They intentionally avoid the production
``gateway.pid`` path and never touch global Hermes state.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from hermes_constants import get_hermes_home


DEV_GATEWAY_HOST = "127.0.0.1"
DEV_GATEWAY_PORT = 18080
DEV_GATEWAY_PID_FILE = "gateway-dev.pid"
DEV_GATEWAY_LOG_FILE = "gateway-dev.log"


@dataclass
class DevGatewayStatus:
    home: Path
    host: str
    port: int
    pid_file: Path
    log_file: Path
    production_pid_file: Path
    state: str
    pid: int | None


def get_dev_gateway_status(home: Path | None = None) -> DevGatewayStatus:
    home = home or get_hermes_home()
    pid_file = home / DEV_GATEWAY_PID_FILE
    log_file = home / DEV_GATEWAY_LOG_FILE
    production_pid_file = home / "gateway.pid"
    pid: int | None = None
    state = "stopped"
    if pid_file.exists():
        try:
            raw = pid_file.read_text(encoding="utf-8").strip()
            pid = int(raw)
            state = "pid file present"
        except Exception:
            state = "pid file unreadable"
    return DevGatewayStatus(
        home=home,
        host=DEV_GATEWAY_HOST,
        port=DEV_GATEWAY_PORT,
        pid_file=pid_file,
        log_file=log_file,
        production_pid_file=production_pid_file,
        state=state,
        pid=pid,
    )


def format_dev_gateway_status(status: DevGatewayStatus) -> str:
    pid_value = str(status.pid) if status.pid is not None else "-"
    return "\n".join(
        [
            "Hermes dev gateway",
            "────────────────────────────────────────",
            f"State:                 {status.state}",
            f"PID:                   {pid_value}",
            f"Home:                  {status.home}",
            f"Host:                  {status.host}",
            f"Port:                  {status.port}",
            f"PID file:              {status.pid_file}",
            f"Production PID file:   {status.production_pid_file}",
            f"Log file:              {status.log_file}",
            "Run support:           not implemented in this safe dry-run step",
            "Wechat dry-run:        available via dev-wechat-message",
        ]
    ) + "\n"
