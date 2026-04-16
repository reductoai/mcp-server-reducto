"""Hosted multi-tenant MCP server for mcp.reducto.ai.

Wraps the FastMCP streamable-http app with auth middleware that
extracts the API key from the Authorization header. Each request
gets its own Reducto client — no shared API key needed on the server.
"""

from __future__ import annotations

import logging
import sys
from contextvars import ContextVar

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger("reducto-mcp")

# Per-request API key, set by auth middleware, read by get_client()
request_api_key: ContextVar[str | None] = ContextVar("request_api_key", default=None)


class BearerAuthMiddleware:
    """ASGI middleware that extracts Bearer token from Authorization header."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")

        # Health check bypasses auth
        if path == "/health":
            response = JSONResponse({"status": "ok", "server": "reducto-mcp"})
            await response(scope, receive, send)
            return

        # Extract Authorization header
        headers = dict(scope.get("headers", []))
        auth_header = headers.get(b"authorization", b"").decode()

        if not auth_header.startswith("Bearer "):
            response = JSONResponse(
                {"error": "Missing or invalid Authorization header. Use: Bearer <your-api-key>"},
                status_code=401,
            )
            await response(scope, receive, send)
            return

        api_key = auth_header[7:].strip()
        if not api_key:
            response = JSONResponse(
                {"error": "Empty API key in Authorization header."},
                status_code=401,
            )
            await response(scope, receive, send)
            return

        # Set the API key for this request, then forward to the MCP app
        token = request_api_key.set(api_key)
        try:
            await self.app(scope, receive, send)
        finally:
            request_api_key.reset(token)


def create_hosted_app() -> ASGIApp:
    """Create the hosted ASGI app: auth middleware wrapping the MCP Starlette app."""
    from mcp_server_reducto.server import mcp

    # Get the Starlette app from FastMCP (includes MCP routes + lifespan)
    mcp_starlette = mcp.streamable_http_app()

    # Wrap it with our auth middleware
    return BearerAuthMiddleware(mcp_starlette)


def main() -> None:
    """Run the hosted MCP server locally for testing."""
    import uvicorn

    logging.basicConfig(stream=sys.stderr, level=logging.INFO)
    logger.info("Starting hosted Reducto MCP server on port 8000")

    app = create_hosted_app()
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
