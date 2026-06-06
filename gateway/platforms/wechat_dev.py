"""Dev-only WeChat message adapter.

This adapter simulates a WeChat text message entering Hermes runtime. It does
not connect to WeChat, does not start the gateway, and does not send replies.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from agent.runtime_memory import RuntimeMemoryContext, build_runtime_prompt_preview


@dataclass
class DevWechatTextMessage:
    text: str
    sender_id: str
    receiver_id: str = "dev-hermes"
    message_id: str = ""
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.message_id:
            self.message_id = f"dev-wechat-{uuid4().hex[:12]}"
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


@dataclass
class DevWechatRuntimeResult:
    message: DevWechatTextMessage
    memory_context: RuntimeMemoryContext
    prompt_preview: str
    reply_preview: str
    llm_call: str


def handle_dev_wechat_text_message(
    text: str,
    *,
    sender_id: str = "dev-wechat-user",
    config: dict | None = None,
    no_llm: bool = True,
) -> DevWechatRuntimeResult:
    message = DevWechatTextMessage(text=text, sender_id=sender_id)
    memory_context, prompt_preview = build_runtime_prompt_preview(
        text,
        config,
        system_prompt="<Agent Runtime System Prompt ...>",
    )
    # Dry-run only for this development command. The prompt preview proves the
    # same runtime memory injection path without calling the model.
    llm_call = "skipped" if no_llm else "skipped (dry-run)"
    reply_preview = (
        "[dry-run] LLM call skipped. The prompt preview below shows what would "
        "enter Agent Runtime before a real reply is generated."
    )
    return DevWechatRuntimeResult(
        message=message,
        memory_context=memory_context,
        prompt_preview=prompt_preview,
        reply_preview=reply_preview,
        llm_call=llm_call,
    )


def _load_first_weixin_account(state_home: Path) -> dict | None:
    account_dir = state_home / "weixin" / "accounts"
    if not account_dir.is_dir():
        return None
    for path in sorted(account_dir.glob("*.json")):
        if path.name.endswith(".context-tokens.json") or path.name.endswith(".sync.json"):
            continue
        try:
            import json

            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(payload, dict) and payload.get("token"):
            payload = dict(payload)
            payload.setdefault("account_id", path.stem)
            return payload
    return None


async def run_dev_wechat_gateway(
    *,
    allow_all_users: bool = False,
    allowed_users: list[str] | None = None,
    verbose: bool = False,
    memory_review_queue: bool = False,
    memory_review_max_pending: int | None = None,
) -> bool:
    """Run the foreground dev WeChat scan-login gateway.

    This reuses the production Weixin iLink adapter but points all runtime
    metadata at development-only paths. It intentionally does not use
    ``--replace`` and does not modify global Hermes state.
    """
    from gateway.config import GatewayConfig, Platform, PlatformConfig
    from gateway.dev_isolation import (
        apply_dev_gateway_auth_environment,
        apply_dev_gateway_redaction_default,
        apply_dev_review_pilot_environment,
        assert_dev_gateway_safe,
        configure_dev_gateway_environment,
        get_dev_gateway_status,
        validate_dev_review_pilot_safety,
        write_dev_gateway_runtime_state,
    )
    from gateway.platforms.weixin import qr_login
    from gateway.run import start_gateway
    from hermes_constants import get_hermes_home

    home = get_hermes_home()
    paths = assert_dev_gateway_safe(home)
    status = get_dev_gateway_status(home)
    if status.state == "running":
        raise RuntimeError(f"Dev gateway already running with PID {status.pid}")
    if status.state == "foreign pid":
        raise RuntimeError(f"Refusing to run with foreign PID in {status.pid_file}")
    review_pilot = validate_dev_review_pilot_safety(
        enabled=memory_review_queue,
        max_pending=memory_review_max_pending,
    )
    apply_dev_review_pilot_environment(review_pilot)

    for key in ("state_dir", "wechat_state_dir", "log_file"):
        paths[key].parent.mkdir(parents=True, exist_ok=True)
    paths["state_dir"].mkdir(parents=True, exist_ok=True)
    paths["wechat_state_dir"].mkdir(parents=True, exist_ok=True)
    configure_dev_gateway_environment(home)
    secret_redaction = apply_dev_gateway_redaction_default()
    dev_user_access, auth_state = apply_dev_gateway_auth_environment(
        allow_all_users=allow_all_users,
        allowed_users=allowed_users,
    )
    if verbose:
        import os

        os.environ["HERMES_DEV_GATEWAY_MEMORY_LOGS"] = "true"
    write_dev_gateway_runtime_state(
        paths,
        auth=auth_state,
        redact_secrets=secret_redaction == "enabled",
        log_memory=verbose,
        review_pilot=review_pilot,
    )

    account = _load_first_weixin_account(paths["wechat_state_dir"])
    if account is None:
        account = await qr_login(str(paths["wechat_state_dir"]))
    if not account:
        raise RuntimeError("Weixin QR login did not produce credentials")

    account_id = str(account.get("account_id") or "").strip()
    token = str(account.get("token") or "").strip()
    base_url = str(account.get("base_url") or "").strip()
    if not account_id or not token:
        raise RuntimeError("Weixin credentials are incomplete")

    config = GatewayConfig()
    config.platforms[Platform.WEIXIN] = PlatformConfig(
        enabled=True,
        token=token,
        extra={
            "account_id": account_id,
            "token": token,
            "base_url": base_url,
            "state_dir": str(paths["wechat_state_dir"]),
            "dm_policy": "open",
            "group_policy": "disabled",
        },
    )

    print()
    print("Hermes Dev WeChat Gateway Starting...")
    print("────────────────────────────────────────")
    print(f"Source root:       {paths['source_root']}")
    print(f"HERMES_HOME:       {home}")
    print("Mode:              scan-login")
    print("Platform:          wechat-dev")
    print(f"PID file:          {paths['pid_file']}")
    print(f"Wechat state dir:  {paths['wechat_state_dir']}")
    print("Production PID:    not touched")
    print("Memory injection:  enabled")
    print(f"Secret redaction:  {secret_redaction}")
    print(f"Dev user access:   {dev_user_access}")
    print(f"Memory logs:       {'enabled' if verbose else 'basic'}")
    print(
        "Memory review queue: "
        f"{'enabled' if review_pilot.enabled else 'disabled'}"
    )
    if review_pilot.enabled:
        print(f"Review queue path: {home / 'memory' / 'reviews'}")
        print(f"Review queue max:  {review_pilot.max_pending}")
        print("Auto memory write: disabled")
        print("Auto memory update: disabled")
        print("Auto category creation: disabled")
        print(f"Review pilot safety: {review_pilot.pilot_safety}")
        print()
        print("WARNING:")
        print("Memory Review Queue pilot only stores review candidates.")
        print("It does not automatically write or update formal long-term memories.")
    if allow_all_users:
        print()
        print("WARNING: gateway-dev is running with --allow-all-users.")
        print("This only applies to the dev gateway process.")
    elif dev_user_access.startswith("deny by default"):
        print("Hint: use --allow-all-users for local dev testing, or --allowed-user <id>.")
    print()
    print("Please scan QR code with a test WeChat account if prompted.")
    print("Press Ctrl+C to stop dev gateway.")
    print()

    return await start_gateway(config=config, replace=False, verbosity=1 if verbose else 0)


def run_dev_wechat_gateway_foreground(
    *,
    allow_all_users: bool = False,
    allowed_users: list[str] | None = None,
    verbose: bool = False,
    memory_review_queue: bool = False,
    memory_review_max_pending: int | None = None,
) -> bool:
    return asyncio.run(
        run_dev_wechat_gateway(
            allow_all_users=allow_all_users,
            allowed_users=allowed_users,
            verbose=verbose,
            memory_review_queue=memory_review_queue,
            memory_review_max_pending=memory_review_max_pending,
        )
    )
