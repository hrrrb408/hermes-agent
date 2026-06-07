"""Dev Web API middleware: Request ID injection.

Importing this module has no side effects.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from hermes_cli.dev_web_schemas import sanitize_request_id


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Ensure every request/response carries a unique ``X-Request-ID``.

    - If the client sends ``X-Request-ID``, it is validated and sanitised.
    - If absent or invalid, a new UUID4 hex is generated.
    - The ID is stored on ``request.state.request_id`` for downstream use.
    - The ID is echoed in the ``X-Request-ID`` response header.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        raw_id = request.headers.get("x-request-id")
        request_id = sanitize_request_id(raw_id)
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
