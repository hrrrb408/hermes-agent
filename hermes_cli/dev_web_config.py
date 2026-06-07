"""Dev Web API configuration and environment validation.

This module provides the configuration object and environment validation
for the Hermes Dev Web API server. It enforces strict isolation from
the production Hermes instance.

Importing this module has no side effects — no files are read, no
environment variables are checked, no processes are started.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_DEV_WEB_API_HOST = "127.0.0.1"
DEFAULT_DEV_WEB_API_PORT = 5181
DEFAULT_DEV_WEB_API_PREFIX = "/api/dev/v1"
DEFAULT_DEV_WEB_API_CORS_ORIGINS: tuple[str, ...] = ("http://127.0.0.1:5180",)
ALLOWED_HOSTS: frozenset[str] = frozenset({"127.0.0.1"})

# Production home that must never be used by the Dev API.
_PRODUCTION_HERMES_HOME = Path.home() / ".hermes"


class DevApiConfigurationError(RuntimeError):
    """Raised when the Dev API configuration is unsafe."""


@dataclass(frozen=True)
class DevWebApiConfig:
    """Immutable configuration for the Dev Web API server."""

    host: str = DEFAULT_DEV_WEB_API_HOST
    port: int = DEFAULT_DEV_WEB_API_PORT
    api_prefix: str = DEFAULT_DEV_WEB_API_PREFIX
    cors_origins: tuple[str, ...] = field(
        default_factory=lambda: DEFAULT_DEV_WEB_API_CORS_ORIGINS,
    )
    hermes_home: Path | None = None
    environment: str = "development"

    def __post_init__(self) -> None:
        _validate_host(self.host)
        _validate_port(self.port)


def _validate_host(host: str) -> None:
    """Reject any host that is not strictly 127.0.0.1."""
    if host not in ALLOWED_HOSTS:
        raise DevApiConfigurationError(
            f"Refusing to bind Dev Web API to '{host}'. "
            f"Only {', '.join(sorted(ALLOWED_HOSTS))} is allowed."
        )


def _validate_port(port: int) -> None:
    """Reject invalid port numbers."""
    if not isinstance(port, int) or port <= 0 or port > 65535:
        raise DevApiConfigurationError(
            f"Invalid port {port!r}. Must be an integer in [1, 65535]."
        )


def validate_development_hermes_home(path: Path) -> Path:
    """Validate that *path* is a safe development HERMES_HOME.

    Returns the resolved Path on success. Raises
    ``DevApiConfigurationError`` on any unsafe condition.
    """
    if path is None:
        raise DevApiConfigurationError(
            "HERMES_HOME is not set. The Dev Web API requires an explicit "
            "development HERMES_HOME."
        )

    path = Path(path)

    # Resolve symlinks and normalise.
    try:
        resolved = path.resolve()
    except Exception as exc:
        raise DevApiConfigurationError(
            f"Cannot resolve HERMES_HOME '{path}': {exc}"
        ) from exc

    # Must actually exist and be a directory.
    if not resolved.exists():
        raise DevApiConfigurationError(
            f"HERMES_HOME does not exist: {resolved}"
        )
    if not resolved.is_dir():
        raise DevApiConfigurationError(
            f"HERMES_HOME is not a directory: {resolved}"
        )

    # Resolve the canonical production home for comparison.
    try:
        prod_resolved = _PRODUCTION_HERMES_HOME.resolve()
    except Exception:
        # If we can't resolve the production path, conservatively
        # compare as strings.
        prod_resolved = _PRODUCTION_HERMES_HOME

    # Must not be the production home.
    if resolved == prod_resolved:
        raise DevApiConfigurationError(
            "HERMES_HOME points to the production instance. "
            "The Dev Web API must not use the production home."
        )

    # Must not be inside the production home.
    try:
        resolved.relative_to(prod_resolved)
    except ValueError:
        pass  # Not inside production home — good.
    else:
        raise DevApiConfigurationError(
            "HERMES_HOME is inside the production instance directory. "
            "The Dev Web API must use a separate development home."
        )

    return resolved


def build_config(
    *,
    host: str | None = None,
    port: int | None = None,
    hermes_home: Path | str | None = None,
) -> DevWebApiConfig:
    """Build a ``DevWebApiConfig`` from explicit params or env vars.

    Priority: explicit params > env vars > safe defaults.
    """
    # Host: only accept 127.0.0.1
    resolved_host = host or os.environ.get(
        "HERMES_DEV_WEB_API_HOST", DEFAULT_DEV_WEB_API_HOST
    )

    # Port
    if port is not None:
        resolved_port = port
    else:
        env_port = os.environ.get("HERMES_DEV_WEB_API_PORT")
        if env_port is not None:
            try:
                resolved_port = int(env_port)
            except ValueError:
                raise DevApiConfigurationError(
                    f"HERMES_DEV_WEB_API_PORT is not a valid integer: {env_port!r}"
                )
        else:
            resolved_port = DEFAULT_DEV_WEB_API_PORT

    # HERMES_HOME
    if hermes_home is not None:
        raw_home = Path(hermes_home)
    else:
        env_home = os.environ.get("HERMES_HOME")
        if env_home:
            raw_home = Path(env_home)
        else:
            raise DevApiConfigurationError(
                "HERMES_HOME is not set. The Dev Web API requires an explicit "
                "development HERMES_HOME. "
                "Set HERMES_HOME or pass --hermes-home."
            )

    validated_home = validate_development_hermes_home(raw_home)

    return DevWebApiConfig(
        host=resolved_host,
        port=resolved_port,
        hermes_home=validated_home,
    )
