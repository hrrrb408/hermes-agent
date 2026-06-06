"""Development gateway isolation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import importlib.util
import json
import os
import time
from pathlib import Path
from typing import Mapping

from hermes_constants import get_hermes_home
from utils import atomic_json_write


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
DEV_REVIEW_PILOT_DEFAULT_MAX_PENDING = 20
DEV_REVIEW_PILOT_MAX_PENDING = 500
DEV_REVIEW_PILOT_UNSAFE_ENV = (
    "HERMES_MEMORY_AUTO_WRITE",
    "HERMES_MEMORY_AUTO_UPDATE",
    "HERMES_MEMORY_AUTO_CREATE_CATEGORIES",
)


@dataclass(frozen=True)
class DevReviewPilotConfig:
    enabled: bool
    max_pending: int
    pilot_safety: str = "disabled"


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
    dev_user_access: str
    secret_redaction: str
    qr_terminal: str
    auth_controls: str
    runtime_state: str
    memory_log_summary: str
    memory_review_queue_enabled: bool
    memory_review_queue_path: Path
    memory_review_queue_max: int
    pending_reviews: int
    pilot_auto_write: bool
    pilot_auto_update: bool
    pilot_auto_create_categories: bool
    review_pilot_safety: str
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


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def configure_dev_gateway_environment(home: Path | None = None) -> dict[str, Path]:
    paths = _dev_paths(home)
    os.environ["HERMES_GATEWAY_PID_FILE"] = str(paths["pid_file"])
    os.environ["HERMES_GATEWAY_STATE_FILE"] = str(paths["runtime_status_file"])
    os.environ["HERMES_GATEWAY_LOG_FILE"] = str(paths["log_file"])
    return paths


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def validate_dev_review_pilot_safety(
    *,
    enabled: bool,
    max_pending: int | str | None = None,
    environ: Mapping[str, str] | None = None,
) -> DevReviewPilotConfig:
    if not enabled:
        if max_pending is not None:
            raise ValueError(
                "REVIEW_PILOT_FLAG_REQUIRED: "
                "--memory-review-max-pending requires --memory-review-queue"
            )
        return DevReviewPilotConfig(
            enabled=False,
            max_pending=DEV_REVIEW_PILOT_DEFAULT_MAX_PENDING,
        )

    env = os.environ if environ is None else environ
    unsafe = [
        f"{name}={env.get(name)}"
        for name in DEV_REVIEW_PILOT_UNSAFE_ENV
        if _truthy(env.get(name))
    ]
    if unsafe:
        raise RuntimeError(
            "DEV_REVIEW_PILOT_UNSAFE_ENV: Dev memory review pilot refused "
            f"to start; unsafe environment detected: {', '.join(unsafe)}"
        )

    raw_max = (
        DEV_REVIEW_PILOT_DEFAULT_MAX_PENDING
        if max_pending is None
        else max_pending
    )
    try:
        parsed_max = int(raw_max)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "DEV_REVIEW_PILOT_INVALID_MAX_PENDING: "
            "memory review max pending must be an integer"
        ) from exc
    if not 1 <= parsed_max <= DEV_REVIEW_PILOT_MAX_PENDING:
        raise ValueError(
            "DEV_REVIEW_PILOT_INVALID_MAX_PENDING: "
            f"memory review max pending must be between 1 and "
            f"{DEV_REVIEW_PILOT_MAX_PENDING}"
        )
    return DevReviewPilotConfig(
        enabled=True,
        max_pending=parsed_max,
        pilot_safety="PASS",
    )


def build_dev_review_pilot_environment(
    config: DevReviewPilotConfig,
) -> dict[str, str]:
    if not config.enabled:
        return {"HERMES_MEMORY_REVIEW_QUEUE": "false"}
    return {
        "HERMES_MEMORY_REVIEW_QUEUE": "true",
        "HERMES_MEMORY_REVIEW_MAX_PENDING": str(config.max_pending),
        "HERMES_MEMORY_AUTO_WRITE": "false",
        "HERMES_MEMORY_AUTO_UPDATE": "false",
        "HERMES_MEMORY_AUTO_CREATE_CATEGORIES": "false",
    }


def apply_dev_review_pilot_environment(config: DevReviewPilotConfig) -> None:
    os.environ.update(build_dev_review_pilot_environment(config))


def get_review_queue_pending_count(home: Path) -> int:
    try:
        from agent.memory_review_queue import get_review_queue_summary

        return int(get_review_queue_summary(home=home, config={}).get("pending", 0))
    except Exception:
        return 0


def build_dev_review_pilot_state(
    paths: Mapping[str, Path],
    config: DevReviewPilotConfig,
) -> dict:
    return {
        "enabled": config.enabled,
        "path": str(paths["home"] / "memory" / "reviews"),
        "max_pending": config.max_pending,
        "pending_count_at_start": get_review_queue_pending_count(paths["home"]),
        "auto_write": False,
        "auto_update": False,
        "auto_create_categories": False,
        "pilot_safety": config.pilot_safety,
    }


def dev_gateway_secret_redaction_status() -> str:
    raw = os.getenv("HERMES_DEV_GATEWAY_REDACT_SECRETS")
    if raw is None or raw.strip() == "":
        return "enabled by default"
    return "enabled by dev env" if _truthy(raw) else "disabled by explicit dev env"


def dev_gateway_qr_status() -> str:
    if importlib.util.find_spec("qrcode") is not None:
        return "available"
    return "unavailable, optional dependency qrcode missing"


def dev_gateway_user_access_status() -> str:
    if _truthy(os.getenv("HERMES_DEV_GATEWAY_ALLOW_ALL_USERS")):
        return "allow all users (dev env)"
    allowed = os.getenv("HERMES_DEV_GATEWAY_ALLOWED_USERS", "").strip()
    if allowed:
        return f"allowed users configured ({allowed})"
    return "deny by default, no dev allowlist configured"


def _read_runtime_state(path: Path) -> tuple[dict, str]:
    if not path.exists():
        return {}, "missing"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {}, f"unreadable: {exc}"
    if not isinstance(payload, dict):
        return {}, "invalid"
    return payload, "available"


def _auth_status_from_state(payload: dict) -> str | None:
    auth = payload.get("auth")
    if not isinstance(auth, dict):
        return None
    source = "running process"
    if auth.get("allow_all_users") is True:
        return f"allow all users (dev only, {source})"
    allowed = auth.get("allowed_users")
    if isinstance(allowed, list) and allowed:
        return f"allowed users configured ({len(allowed)}, {source})"
    if auth.get("mode"):
        return f"{auth.get('mode')} ({source})"
    return None


def _secret_status_from_state(payload: dict) -> str | None:
    security = payload.get("security")
    if not isinstance(security, dict):
        return None
    if security.get("redact_secrets") is True:
        return "enabled (running process)"
    if security.get("redact_secrets") is False:
        return "disabled (running process)"
    return None


def _memory_log_status_from_state(payload: dict) -> str | None:
    memory = payload.get("memory")
    if not isinstance(memory, dict):
        return None
    if memory.get("log_summary") is True:
        return "available (verbose)"
    if memory.get("runtime_injection") is True:
        return "available"
    return None


def apply_dev_gateway_auth_environment(
    *,
    allow_all_users: bool = False,
    allowed_users: list[str] | None = None,
) -> tuple[str, dict]:
    env_allow_all = _truthy(os.getenv("HERMES_DEV_GATEWAY_ALLOW_ALL_USERS"))
    env_allowed = [
        item.strip()
        for item in os.getenv("HERMES_DEV_GATEWAY_ALLOWED_USERS", "").split(",")
        if item.strip()
    ]
    cli_allowed = [str(item).strip() for item in (allowed_users or []) if str(item).strip()]
    resolved_allowed = cli_allowed or env_allowed

    if allow_all_users or env_allow_all:
        os.environ["WEIXIN_ALLOW_ALL_USERS"] = "true"
        os.environ["GATEWAY_ALLOW_ALL_USERS"] = "true"
        return "allow all users (dev only)", {
            "allow_all_users": True,
            "allowed_users": [],
            "source": "gateway-dev run --allow-all-users" if allow_all_users else "HERMES_DEV_GATEWAY_ALLOW_ALL_USERS",
        }

    os.environ["WEIXIN_ALLOW_ALL_USERS"] = "false"
    os.environ["GATEWAY_ALLOW_ALL_USERS"] = "false"
    if resolved_allowed:
        allowed_value = ",".join(resolved_allowed)
        os.environ["WEIXIN_ALLOWED_USERS"] = allowed_value
        return f"allowed users: {allowed_value}", {
            "allow_all_users": False,
            "allowed_users": resolved_allowed,
            "source": "--allowed-user" if cli_allowed else "HERMES_DEV_GATEWAY_ALLOWED_USERS",
        }

    # Keep the gateway startup diagnostic from pointing developers at
    # ~/.hermes/.env while preserving default-deny behavior.
    os.environ["WEIXIN_ALLOWED_USERS"] = "__hermes_dev_gateway_no_users__"
    return "deny by default, no dev allowlist configured", {
        "allow_all_users": False,
        "allowed_users": [],
        "source": "default",
        "mode": "deny by default",
    }


def apply_dev_gateway_redaction_default() -> str:
    raw = os.getenv("HERMES_DEV_GATEWAY_REDACT_SECRETS")
    if raw is not None and raw.strip() and not _truthy(raw):
        os.environ["HERMES_REDACT_SECRETS"] = "false"
        return "disabled by explicit dev env"
    os.environ["HERMES_REDACT_SECRETS"] = "true"
    return "enabled"


def write_dev_gateway_runtime_state(
    paths: dict[str, Path],
    *,
    auth: dict,
    redact_secrets: bool,
    log_memory: bool,
    review_pilot: DevReviewPilotConfig | None = None,
) -> None:
    state_path = paths["runtime_status_file"]
    payload, _state = _read_runtime_state(state_path)
    payload.update(
        {
            "mode": "scan-login",
            "platform": "wechat-dev",
            "status": "starting",
            "gateway_state": payload.get("gateway_state", "starting"),
            "pid": os.getpid(),
            "started_at": payload.get("started_at") or _now_iso(),
            "hermes_home": str(paths["home"]),
            "pid_file": str(paths["pid_file"]),
            "state_dir": str(paths["state_dir"]),
            "wechat_state_dir": str(paths["wechat_state_dir"]),
            "auth": auth,
            "security": {"redact_secrets": redact_secrets},
            "memory": {
                "runtime_injection": True,
                "log_summary": log_memory,
            },
            "memory_review_queue": build_dev_review_pilot_state(
                paths,
                review_pilot
                or DevReviewPilotConfig(
                    enabled=False,
                    max_pending=DEV_REVIEW_PILOT_DEFAULT_MAX_PENDING,
                ),
            ),
        }
    )
    state_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_json_write(state_path, payload)


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
    runtime_payload, runtime_state = _read_runtime_state(paths["runtime_status_file"])
    runtime_auth_status = _auth_status_from_state(runtime_payload) if state == "running" else None
    runtime_secret_status = _secret_status_from_state(runtime_payload) if state == "running" else None
    runtime_memory_status = _memory_log_status_from_state(runtime_payload)
    pilot_payload = runtime_payload.get("memory_review_queue", {})
    if not isinstance(pilot_payload, dict):
        pilot_payload = {}
    pilot_running = state == "running" and pilot_payload.get("enabled") is True
    review_path = home / "memory" / "reviews"
    try:
        review_max = int(
            pilot_payload.get(
                "max_pending",
                DEV_REVIEW_PILOT_DEFAULT_MAX_PENDING,
            )
        )
    except (TypeError, ValueError):
        review_max = DEV_REVIEW_PILOT_DEFAULT_MAX_PENDING
    pilot_auto_write = bool(pilot_payload.get("auto_write", False))
    pilot_auto_update = bool(pilot_payload.get("auto_update", False))
    pilot_auto_create = bool(
        pilot_payload.get("auto_create_categories", False)
    )
    pilot_state_safe = not (
        pilot_auto_write or pilot_auto_update or pilot_auto_create
    )
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
        dev_user_access=runtime_auth_status or dev_gateway_user_access_status(),
        secret_redaction=runtime_secret_status or dev_gateway_secret_redaction_status(),
        qr_terminal=dev_gateway_qr_status(),
        auth_controls="available",
        runtime_state=runtime_state,
        memory_log_summary=runtime_memory_status or "available with --verbose",
        memory_review_queue_enabled=pilot_running,
        memory_review_queue_path=review_path,
        memory_review_queue_max=review_max,
        pending_reviews=get_review_queue_pending_count(home),
        pilot_auto_write=(
            pilot_auto_write if pilot_running else False
        ),
        pilot_auto_update=(
            pilot_auto_update if pilot_running else False
        ),
        pilot_auto_create_categories=(
            pilot_auto_create if pilot_running else False
        ),
        review_pilot_safety=(
            (
                str(pilot_payload.get("pilot_safety", "unknown"))
                if pilot_state_safe
                else "FAIL"
            )
            if pilot_running
            else "disabled"
        ),
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
            f"Runtime state:   {status.runtime_state}",
            f"State dir:       {status.state_dir}",
            f"Wechat state:    {status.wechat_state_dir}",
            f"Log file:        {status.log_file}",
            "Production PID:  not managed by dev gateway",
            f"Scan runner:     {status.scan_runner}",
            f"Dev user access: {status.dev_user_access}",
            f"Secret redaction: {status.secret_redaction}",
            f"QR terminal:     {status.qr_terminal}",
            f"Auth controls:   {status.auth_controls}",
            f"Memory logs:     {status.memory_log_summary}",
            (
                "Memory review queue: enabled"
                if status.memory_review_queue_enabled
                else "Memory review queue: disabled by default"
            ),
            f"Review queue path: {status.memory_review_queue_path}",
            f"Pending reviews: {status.pending_reviews}",
            f"Review queue max: {status.memory_review_queue_max}",
            f"Auto memory write: {'enabled' if status.pilot_auto_write else 'disabled'}",
            f"Auto memory update: {'enabled' if status.pilot_auto_update else 'disabled'}",
            (
                "Auto category creation: "
                f"{'enabled' if status.pilot_auto_create_categories else 'disabled'}"
            ),
            f"Review pilot safety: {status.review_pilot_safety}",
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
