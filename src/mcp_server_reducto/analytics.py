"""PostHog product analytics for the Reducto MCP server.

Fires events for tool invocations, server start, and first-run install.
On by default; opt out with REDUCTO_TELEMETRY=0.

Identifiers are hashed API keys (sha256, truncated) — never raw keys, never
document content, never tool arguments. The set of properties on each event
is fixed and audit-able by reading this file.

The PostHog project token below is a public write-only client key; committing
it is the standard PostHog pattern.
"""

from __future__ import annotations

import functools
import hashlib
import logging
import os
import platform
import sys
import time
import uuid
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from mcp_server_reducto import __version__
from mcp_server_reducto.config import CLIENT_ID, REDUCTO_DIR, TRANSPORT_STDIO

if TYPE_CHECKING:
    from mcp.types import CallToolResult
    from posthog import Posthog

logger = logging.getLogger("mcp-server-reducto.analytics")

POSTHOG_PROJECT_KEY = "phc_zoZUyqoUX2QX6ZXAhQZ5xEDBCoVCaQ9EfGMtP3QtJRPG"
POSTHOG_HOST = "https://us.i.posthog.com"

_INSTALL_SENTINEL = REDUCTO_DIR / ".mcp_installed"
_MACHINE_ID_PATH = REDUCTO_DIR / ".mcp_machine_id"

_BASE_PROPERTIES: dict[str, Any] = {
    "client": CLIENT_ID,
    "client_version": __version__,
    "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    "os_platform": platform.system().lower(),
}


def is_telemetry_enabled() -> bool:
    """Telemetry is on by default; opt out with REDUCTO_TELEMETRY=0."""
    val = os.environ.get("REDUCTO_TELEMETRY", "1").strip().lower()
    return val not in {"0", "false", "no", "off"}


@functools.lru_cache(maxsize=1)
def _get_client() -> Posthog | None:
    if not is_telemetry_enabled():
        return None
    try:
        from posthog import Posthog
    except ImportError:
        logger.debug("posthog SDK not installed; telemetry disabled")
        return None
    try:
        return Posthog(
            project_api_key=POSTHOG_PROJECT_KEY,
            host=POSTHOG_HOST,
            sync_mode=False,
            disable_geoip=True,
        )
    except Exception as e:  # pragma: no cover
        logger.debug("posthog init failed (%s); telemetry disabled", e)
        return None


def hash_identifier(value: str) -> str:
    """Stable hash for an API key (or any user identifier). Never reversible to plaintext."""
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return f"sha256:{digest[:16]}"


@functools.lru_cache(maxsize=1)
def _machine_id() -> str:
    """Stable machine ID for events fired before any API key is known."""
    try:
        if _MACHINE_ID_PATH.exists():
            return _MACHINE_ID_PATH.read_text().strip()
        _MACHINE_ID_PATH.parent.mkdir(parents=True, exist_ok=True)
        new_id = f"machine:{uuid.uuid4().hex[:16]}"
        _MACHINE_ID_PATH.write_text(new_id)
        return new_id
    except OSError:
        return f"anon:{uuid.uuid4().hex[:16]}"


def track(
    event: str,
    distinct_id: str,
    properties: dict[str, Any] | None = None,
    *,
    transport: str = TRANSPORT_STDIO,
) -> None:
    """Fire a PostHog event. No-op if telemetry is disabled or PostHog is unavailable."""
    client = _get_client()
    if client is None:
        return
    payload: dict[str, Any] = {**_BASE_PROPERTIES, "transport": transport}
    if properties:
        payload.update(properties)
    try:
        client.capture(distinct_id=distinct_id, event=event, properties=payload)
    except Exception as e:  # pragma: no cover
        logger.debug("posthog capture failed for %s: %s", event, e)


def flush() -> None:
    """Drain pending events on shutdown."""
    client = _get_client()
    if client is None:
        return
    try:
        client.shutdown()
    except Exception as e:  # pragma: no cover
        logger.debug("posthog flush failed: %s", e)


def track_lifespan_start(api_key: str | None, transport: str) -> None:
    """Fire mcp.start on every server boot, plus mcp.installed once per machine."""
    distinct_id = hash_identifier(api_key) if api_key else _machine_id()

    if not _INSTALL_SENTINEL.exists():
        try:
            _INSTALL_SENTINEL.parent.mkdir(parents=True, exist_ok=True)
            _INSTALL_SENTINEL.write_text(__version__)
            track("mcp.installed", distinct_id, transport=transport)
        except OSError:
            pass

    track("mcp.start", distinct_id, transport=transport)


def _resolve_distinct_id(ctx: Any) -> tuple[str, str]:
    """Return (distinct_id, transport) for the current request."""
    from mcp_server_reducto.tools.helpers import resolve_request_api_key

    api_key, transport = resolve_request_api_key(ctx)
    if api_key:
        return hash_identifier(api_key), transport
    return _machine_id(), transport


def tracked(event_name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator: fire tool.<event_name>.invoked with status + latency.

    Place between @mcp.tool(...) and the async def so it wraps the function
    before fastmcp registers it. functools.wraps preserves the signature for
    fastmcp's parameter introspection.
    """

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            ctx = kwargs.get("ctx")
            start = time.perf_counter()
            status = "ok"
            try:
                result: CallToolResult = await fn(*args, **kwargs)
                if getattr(result, "isError", False):
                    status = "error"
                return result
            except Exception:
                status = "exception"
                raise
            finally:
                latency_ms = int((time.perf_counter() - start) * 1000)
                distinct_id, transport = _resolve_distinct_id(ctx)
                track(
                    f"tool.{event_name}.invoked",
                    distinct_id,
                    {"tool": event_name, "status": status, "latency_ms": latency_ms},
                    transport=transport,
                )

        return wrapper

    return decorator
