"""Fake Provider Agent Run Smoke Server.

A lightweight entry point that starts the Dev API with a Fake Provider
instead of a real LLM. Used exclusively by the Phase 1F enabled browser
smoke runner.

Safety:
    - Only starts when HERMES_AGENT_RUN_SMOKE=true
    - Refuses to use production HERMES_HOME
    - Refuses to use dev-home HERMES_HOME
    - Must use a temporary directory
    - Never connects to external providers
    - Never reads real API keys
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── Safety gate ──

_SMOKE_ENV = "HERMES_AGENT_RUN_SMOKE"


def _enforce_smoke_environment() -> None:
    """Verify we are in a safe smoke environment."""
    smoke = os.environ.get(_SMOKE_ENV, "").strip().lower()
    if smoke not in ("true", "1", "yes", "on"):
        print(f"FATAL: {_SMOKE_ENV} must be set to 'true'", file=sys.stderr)
        sys.exit(1)

    hermes_home = os.environ.get("HERMES_HOME", "")
    if not hermes_home:
        print("FATAL: HERMES_HOME must be set", file=sys.stderr)
        sys.exit(1)

    resolved = Path(hermes_home).resolve()

    # Must not be production
    prod_home = Path("/Users/huangruibang/.hermes").resolve()
    if resolved == prod_home:
        print("FATAL: HERMES_HOME must not be production", file=sys.stderr)
        sys.exit(1)

    # Must not be dev-home
    dev_home = Path("/Users/huangruibang/Code/hermes-home-dev").resolve()
    if resolved == dev_home:
        print("FATAL: HERMES_HOME must not be dev-home for smoke", file=sys.stderr)
        sys.exit(1)

    # Must be under /tmp (macOS resolves /tmp to /private/tmp)
    tmp_root = Path("/tmp").resolve()
    try:
        resolved.relative_to(tmp_root)
    except ValueError:
        print(f"FATAL: HERMES_HOME must be under {tmp_root}, got {resolved}", file=sys.stderr)
        sys.exit(1)

    print(f"Smoke environment OK: HERMES_HOME={resolved}")


# ── Fake Provider ──


class FakeProviderResult:
    """Simulated LLM provider result."""

    def __init__(
        self,
        deltas: Optional[List[str]] = None,
        final_text: Optional[str] = None,
        input_tokens: int = 10,
        output_tokens: int = 5,
        total_tokens: int = 15,
        initial_delay: float = 0.15,
        delay_per_delta: float = 0.08,
        block_forever: bool = False,
    ):
        self.deltas = deltas or ["Hello", " ", "from", " ", "Hermes"]
        self.final_text = final_text or "".join(self.deltas)
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.total_tokens = total_tokens
        self.initial_delay = initial_delay
        self.delay_per_delta = delay_per_delta
        self.block_forever = block_forever
        self._interrupted = threading.Event()

    def interrupt(self):
        self._interrupted.set()


class FakeAgent:
    """Minimal fake AIAgent that drives stream_delta_callback with deltas."""

    def __init__(self, result: FakeProviderResult, **kwargs):
        self._result = result
        self._kwargs = kwargs

    def run_conversation(self, message, stream_callback=None):
        """Simulate agent run_conversation with delta streaming.

        Persists user and assistant messages to SessionDB, matching
        the real AIAgent.run_conversation behavior.
        """
        result = self._result
        cb = self._kwargs.get("stream_delta_callback")
        session_id = self._kwargs.get("session_id")
        session_db = self._kwargs.get("session_db")

        if result.block_forever:
            # Block until interrupted or 60s timeout
            result._interrupted.wait(timeout=60)
            # Return a clean result when interrupted — the cancel handler
            # will transition the state to CANCELLED
            return {
                "text": "",
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "messages": [],
            }

        # Initial delay to give SSE time to connect and receive
        # run.created / run.started events before deltas start
        if result.initial_delay > 0:
            time.sleep(result.initial_delay)

        # Stream deltas with delay
        for delta in result.deltas:
            if result._interrupted.is_set():
                break
            if cb:
                cb(delta)
            time.sleep(result.delay_per_delta)

        # Persist messages like real AIAgent.run_conversation does
        if session_db is not None and session_id:
            try:
                session_db.append_message(
                    session_id=session_id,
                    role="user",
                    content=message,
                )
                session_db.append_message(
                    session_id=session_id,
                    role="assistant",
                    content=result.final_text,
                )
            except Exception:
                pass  # Persistence failures shouldn't fail the run

        return {
            "text": result.final_text,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            "total_tokens": result.total_tokens,
            "messages": [{"role": "assistant", "content": result.final_text}],
        }

    def interrupt(self):
        """Handle interrupt from cancel."""
        self._result.interrupt()

    def clear_interrupt(self):
        pass


# ── Singleton results ──

_SUCCESS_RESULT: Optional[FakeProviderResult] = None
_BLOCK_RESULT: Optional[FakeProviderResult] = None


def _get_success_result() -> FakeProviderResult:
    global _SUCCESS_RESULT
    if _SUCCESS_RESULT is None:
        _SUCCESS_RESULT = FakeProviderResult(
            deltas=["Hello", " ", "from", " ", "Hermes"],
            final_text="Hello from Hermes",
            input_tokens=10,
            output_tokens=5,
            total_tokens=15,
            initial_delay=0.15,
            delay_per_delta=0.08,
        )
    return _SUCCESS_RESULT


def _get_block_result() -> FakeProviderResult:
    global _BLOCK_RESULT
    if _BLOCK_RESULT is None:
        _BLOCK_RESULT = FakeProviderResult(
            block_forever=True,
        )
    return _BLOCK_RESULT


def _fake_create_agent(self, **kwargs):
    """Replacement for AgentRunService._create_agent.

    Returns a FakeAgent instead of a real AIAgent.
    Never connects to external providers.
    """
    from hermes_state import SessionDB

    # Determine if this should be a blocking (cancel test) or success run
    session_id = kwargs.get("session_id", "")

    if session_id.endswith("-cancel"):
        result = _get_block_result()
    else:
        result = _get_success_result()

    # Create a SessionDB for message persistence (like real _create_agent)
    session_db = SessionDB(db_path=self._hermes_home / "state.db")

    return FakeAgent(result, session_db=session_db, **kwargs)


# ── Fixture initialization ──


def _init_fixture(hermes_home: Path) -> str:
    """Create minimal fixture data in the temp HERMES_HOME."""
    home = Path(hermes_home)

    # Create directory structure
    (home / "memory" / "indexes").mkdir(parents=True, exist_ok=True)
    (home / "memory" / "records").mkdir(parents=True, exist_ok=True)
    (home / "memory" / "snapshots").mkdir(parents=True, exist_ok=True)
    (home / "memory" / "reviews").mkdir(parents=True, exist_ok=True)

    # Create minimal config.yaml
    config = {
        "model": "fake-model",
        "provider": "fake",
        "providers": {
            "fake": {
                "base_url": "",
            },
        },
    }
    (home / "config.yaml").write_text(
        json.dumps(config, indent=2), encoding="utf-8"
    )

    # Create minimal SOUL.md
    (home / "SOUL.md").write_text("# Hermes Smoke Test\n", encoding="utf-8")

    # Create minimal MEMORY.md
    (home / "MEMORY.md").write_text(
        "# Hermes Memory Root Router\n", encoding="utf-8"
    )

    # Create empty events.jsonl
    (home / "memory" / "events.jsonl").write_text("", encoding="utf-8")

    # Use SessionDB to create proper schema and sessions
    # (SessionDB._init_schema creates all required tables and columns)
    from hermes_state import SessionDB
    import time as _time

    db = SessionDB(db_path=home / "state.db")

    # Create predictable sessions for smoke tests
    now = _time.time()
    sessions = [
        ("session-phase-1f-smoke", "dev-webui", "fake-model"),
        ("session-phase-1f-cancel", "dev-webui", "fake-model"),
    ]
    for sid, source, model in sessions:
        db.create_session(
            session_id=sid,
            source=source,
            model=model,
        )

    return "session-phase-1f-smoke"


# ── Main ──


def main():
    """Start the Dev API server with Fake Provider injection."""
    _enforce_smoke_environment()

    # Ensure repo root is on sys.path for hermes_state, run_agent, etc.
    repo_root = str(Path(__file__).resolve().parents[1])
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    import uvicorn
    from hermes_cli.dev_web_api import create_dev_web_api_app
    from hermes_cli.dev_web_config import DevWebApiConfig

    hermes_home = Path(os.environ["HERMES_HOME"]).resolve()

    # Initialize fixture
    session_id = _init_fixture(hermes_home)
    print(f"Fixture initialized: session_id={session_id}")

    # Patch the environment
    os.environ["HERMES_AGENT_RUN_ENABLED"] = "true"

    # Patch AgentRunService._create_agent before creating the app
    import hermes_cli.dev_web_agent_run_service as svc
    svc.AgentRunService._create_agent = _fake_create_agent

    # Patch the dev guard to allow temp home
    import hermes_cli.dev_web_agent_run_config as cfg
    cfg.ALLOWED_HERMES_HOME = hermes_home
    cfg._PRODUCTION_HERMES_HOME = Path("/nonexistent/prod")

    # Also patch the source root check
    source_root = Path(__file__).resolve().parents[1]
    cfg.ALLOWED_SOURCE_ROOT = source_root

    # Patch _load_api_key to never read real keys
    def _fake_load_api_key(self, config, provider):
        return "fake-key-for-smoke"

    svc.AgentRunService._load_api_key = _fake_load_api_key

    # Patch _load_base_url to return empty
    def _fake_load_base_url(self, config, provider):
        return ""

    svc.AgentRunService._load_base_url = _fake_load_base_url

    # Patch _load_safe_config to return minimal config
    def _fake_load_safe_config(self):
        return {
            "model": "fake-model",
            "provider": "fake",
            "providers": {"fake": {"base_url": ""}},
        }

    svc.AgentRunService._load_safe_config = _fake_load_safe_config

    # Patch _verify_session_exists to use our temp db
    original_verify = svc.AgentRunService._verify_session_exists

    def _fake_verify_session(self, session_id):
        from hermes_state import SessionDB
        db = SessionDB(db_path=hermes_home / "state.db")
        session = db.get_session(session_id)
        if session is None:
            raise svc.SessionNotFoundError(f"Session {session_id} not found")

    svc.AgentRunService._verify_session_exists = _fake_verify_session

    print("Fake Provider patches applied")

    # Get server config
    host = os.environ.get("DEV_API_HOST", "127.0.0.1")
    port = int(os.environ.get("DEV_API_PORT", "5181"))

    config = DevWebApiConfig(hermes_home=hermes_home)
    app = create_dev_web_api_app(config)

    print(f"Starting Fake Provider Dev API on {host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    main()
