"""Development gateway isolation helpers."""

from __future__ import annotations

from dataclasses import dataclass
import os
import time
from pathlib import Path

from hermes_constants import get_hermes_home


DEV_GATEWAY_HOST = "127.0.0.1"
DEV_GATEWAY_PORT = 18080
DEV_GATEWAY_PID_FILE = "gateway-dev.pid"
DEV_GATEWAY_STATE_FILE = "gateway-dev-state.json"
DEV_GATEWAY_LOG_FILE = "logs/gateway-dev.log"
DEV_GATEWAY_STATE_DIR = "gateway/dev"
DEV_WECHAT_STATE_DIR = "gateway/dev/wechat"
EXPECTED_DEV_HOME = Path("/Users/huangruibang/Code/hermes-home-dev")
EXPECTED_SOURCE_ROOT = Path("/Users/huangruibang/Code/hermes-agent-dev")
ORIGINAL_HERMES_HOME = Path("/Users/huangruibang/.hermes")
PRODUCTION_GATEWAY_PID = 1717


@dataclass
class DevGatewayStatus:
    home: Path
    source_root: Path
    host: str
    port: int
    pid_file: Path
    runtime_status_file: Path
    log_file: Path
    production_pid_file: Path
    state_dir: Path
    wechat_state_dir: Path
    state: str
    pid: int | None
    isolation: str
    scan_runner: str
    reason: str = ""


def _resolve(path: Path) -> Path:
    try:
        return path.resolve()
    except Exception:
        return path


def _inside(child: Path, parent: Path) -> bool:
    try:
        _resolve(child).relative_to(_resolve(parent))
        return True
    except Exception:
        return False


def _dev_paths(home: Path | None = None) -> dict[str, Path]:
    home = home or get_hermes_home()
    return {
        "home": home,
        "source_root": EXPECTED_SOURCE_ROOT,
        "pid_file": home / DEV_GATEWAY_PID_FILE,
        "runtime_status_file": home / DEV_GATEWAY_STATE_FILE,
        "log_file": home / DEV_GATEWAY_LOG_FILE,
        "production_pid_file": home / "gateway.pid",
        "state_dir": home / DEV_GATEWAY_STATE_DIR,
        "wechat_state_dir": home / DEV_WECHAT_STATE_DIR,
    }


def configure_dev_gateway_environment(home: Path | None = None) -> dict[str, Path]:
    paths = _dev_paths(home)
    os.environ["HERMES_GATEWAY_PID_FILE"] = str(paths["pid_file"])
    os.environ["HERMES_GATEWAY_STATE_FILE"] = str(paths["runtime_status_file"])
    os.environ["HERMES_GATEWAY_LOG_FILE"] = str(paths["log_file"])
    return paths


def assert_dev_gateway_safe(home: Path | None = None) -> dict[str, Path]:
    paths = _dev_paths(home)
    resolved_home = _resolve(paths["home"])
    if resolved_home != _resolve(EXPECTED_DEV_HOME):
        raise RuntimeError(f"HERMES_HOME must be {EXPECTED_DEV_HOME}, got {paths['home']}")
    if resolved_home == _resolve(ORIGINAL_HERMES_HOME):
        raise RuntimeError("Refusing to use /Users/huangruibang/.hermes for dev gateway")
    for key in ("pid_file", "runtime_status_file", "log_file", "state_dir", "wechat_state_dir"):
        if not _inside(paths[key], paths["home"]):
            raise RuntimeError(f"{key} is outside dev HERMES_HOME: {paths[key]}")
    if paths["pid_file"] == paths["production_pid_file"]:
        raise RuntimeError("Dev gateway pid file must not be gateway.pid")
    return paths


def _read_pid(path: Path) -> int | None:
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except Exception:
        return None
    if not raw:
        return None
    try:
        import json

        payload = json.loads(raw)
        if isinstance(payload, dict):
            return int(payload.get("pid"))
        if isinstance(payload, int):
            return payload
    except Exception:
        pass
    try:
        return int(raw)
    except Exception:
        return None


def _pid_running(pid: int) -> bool:
    try:
        from gateway.status import _pid_exists

        return _pid_exists(pid)
    except Exception:
        return False


def _pid_cmdline(pid: int) -> str:
    try:
        from gateway.status import _read_process_cmdline

        return _read_process_cmdline(pid) or ""
    except Exception:
        return ""


def _looks_like_dev_gateway(pid: int, home: Path) -> bool:
    if pid == PRODUCTION_GATEWAY_PID:
        return False
    cmdline = _pid_cmdline(pid)
    if not cmdline:
        return False
    return str(EXPECTED_SOURCE_ROOT) in cmdline or str(home) in cmdline or "gateway-dev" in cmdline


def get_dev_gateway_status(home: Path | None = None) -> DevGatewayStatus:
    paths = _dev_paths(home)
    home = paths["home"]
    pid_file = paths["pid_file"]
    pid: int | None = None
    state = "stopped"
    if pid_file.exists():
        pid = _read_pid(pid_file)
        if pid is None:
            state = "pid file unreadable"
        elif _pid_running(pid):
            state = "running" if _looks_like_dev_gateway(pid, home) else "foreign pid"
        else:
            state = "stale pid file"
    try:
        assert_dev_gateway_safe(home)
        isolation = "PASS"
        reason = ""
    except Exception as exc:
        isolation = "FAIL"
        reason = str(exc)
    return DevGatewayStatus(
        home=home,
        source_root=paths["source_root"],
        host=DEV_GATEWAY_HOST,
        port=DEV_GATEWAY_PORT,
        pid_file=pid_file,
        runtime_status_file=paths["runtime_status_file"],
        log_file=paths["log_file"],
        production_pid_file=paths["production_pid_file"],
        state_dir=paths["state_dir"],
        wechat_state_dir=paths["wechat_state_dir"],
        state=state,
        pid=pid,
        isolation=isolation,
        scan_runner="available",
        reason=reason,
    )


def format_dev_gateway_status(status: DevGatewayStatus) -> str:
    pid_value = str(status.pid) if status.pid is not None else "-"
    return "\n".join(
        [
            "Hermes Dev Gateway",
            "────────────────────────────────────────",
            f"Status:          {status.state}",
            f"PID:             {pid_value}",
            f"Source root:     {status.source_root}",
            f"HERMES_HOME:     {status.home}",
            f"Host:            {status.host}",
            f"Port:            {status.port}",
            f"PID file:        {status.pid_file}",
            f"State file:      {status.runtime_status_file}",
            f"State dir:       {status.state_dir}",
            f"Wechat state:    {status.wechat_state_dir}",
            f"Log file:        {status.log_file}",
            "Production PID:  not managed by dev gateway",
            f"Scan runner:     {status.scan_runner}",
            "Wechat dry-run:  available via dev-wechat-message",
            f"Isolation:       {status.isolation}",
            *([f"Reason:          {status.reason}"] if status.reason else []),
        ]
    ) + "\n"


def stop_dev_gateway(home: Path | None = None, *, timeout_seconds: float = 10.0) -> str:
    paths = assert_dev_gateway_safe(home)
    status = get_dev_gateway_status(paths["home"])
    if status.pid is None:
        return "Dev gateway is not running."
    if status.pid == PRODUCTION_GATEWAY_PID:
        raise RuntimeError("Refusing to stop production gateway PID 1717")
    if status.state not in {"running", "stale pid file"}:
        raise RuntimeError(f"Refusing to stop unverified dev gateway pid: {status.state}")
    if status.state == "stale pid file":
        return "Dev gateway pid file is stale; no process was stopped."
    if not _looks_like_dev_gateway(status.pid, paths["home"]):
        raise RuntimeError(f"Refusing to stop PID {status.pid}; command line is not a dev gateway")

    configure_dev_gateway_environment(paths["home"])
    try:
        from gateway.status import terminate_pid, write_planned_stop_marker

        write_planned_stop_marker(status.pid)
        terminate_pid(status.pid, force=False)
    except ProcessLookupError:
        return "Dev gateway process already exited."

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if not _pid_running(status.pid):
            return f"Stopped dev gateway PID {status.pid}."
        time.sleep(0.25)
    return f"Stop signal sent to dev gateway PID {status.pid}; it is still shutting down."
