"""Dev-only WeChat message adapter.

This adapter simulates a WeChat text message entering Hermes runtime. It does
not connect to WeChat, does not start the gateway, and does not send replies.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
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
