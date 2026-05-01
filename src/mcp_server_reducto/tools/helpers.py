"""Shared helpers for tool implementations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from mcp.server.fastmcp import Context

from mcp_server_reducto import __version__
from mcp_server_reducto.config import CLIENT_ID, TRANSPORT_HOSTED, TRANSPORT_STDIO

if TYPE_CHECKING:
    from reducto import AsyncReducto

ATTRIBUTION_HEADERS: dict[str, str] = {
    "X-Reducto-Client": CLIENT_ID,
    "X-Reducto-Client-Version": __version__,
}


def _make_client(api_key: str, *, transport: str | None = None) -> AsyncReducto:
    """Create an AsyncReducto client with attribution headers."""
    from reducto import AsyncReducto

    from mcp_server_reducto.config import get_base_url, get_timeout

    headers = dict(ATTRIBUTION_HEADERS)
    if transport:
        headers["X-Reducto-Transport"] = transport

    kwargs: dict[str, Any] = {
        "api_key": api_key,
        "timeout": get_timeout(),
        "default_headers": headers,
    }
    base_url = get_base_url()
    if base_url:
        kwargs["base_url"] = base_url
    return AsyncReducto(**kwargs)


def resolve_request_api_key(ctx: Context | None) -> tuple[str | None, str]:
    """Return (api_key_or_None, transport) for the current request.

    Resolution order matches get_client: hosted (per-request) → local (lifespan
    client). Returns None for the api_key if neither path produces one — callers
    decide whether that's an error (get_client) or fine (analytics).
    """
    from mcp_server_reducto.hosted import request_api_key

    per_request_key = request_api_key.get()
    if per_request_key is not None:
        return per_request_key, TRANSPORT_HOSTED

    request_context = getattr(ctx, "_request_context", None) if ctx is not None else None
    if request_context is not None:
        lc = getattr(request_context, "lifespan_context", None)
        if isinstance(lc, dict):
            client = lc.get("reducto_client")
            api_key = getattr(client, "api_key", None) if client else None
            if api_key:
                return api_key, TRANSPORT_STDIO

    return None, TRANSPORT_STDIO


def get_client(ctx: Context) -> AsyncReducto:
    """Get a Reducto client for the current request.

    Resolution order:
    1. Test mode: server._test_client (injected in tests)
    2. Hosted mode: per-request API key from contextvars (set by auth middleware)
    3. Local mode: shared client from lifespan context
    """
    server = ctx.fastmcp
    test_client = getattr(server, "_test_client", None)
    if test_client is not None:
        return test_client

    from mcp_server_reducto.hosted import request_api_key

    per_request_key = request_api_key.get()
    if per_request_key is not None:
        return _make_client(per_request_key, transport=TRANSPORT_HOSTED)

    request_context = getattr(ctx, "_request_context", None)
    if request_context is not None:
        lc = getattr(request_context, "lifespan_context", None)
        if isinstance(lc, dict) and "reducto_client" in lc:
            return lc["reducto_client"]

    raise RuntimeError(
        "Reducto client not found in context. "
        "Ensure the server was started with the correct lifespan, "
        "or pass an API key via Authorization header (hosted mode)."
    )


def merge_options(top_level: dict[str, Any], options: dict[str, Any] | None) -> dict[str, Any]:
    """Merge top-level params with options dict. Top-level params take precedence."""
    if not options:
        return top_level
    merged = {**options}
    for key, value in top_level.items():
        if value is not None:
            merged[key] = value
    return merged
