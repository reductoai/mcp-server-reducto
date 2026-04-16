"""Map Reducto SDK exceptions to MCP-friendly error responses.

Following the Sentry pattern: tool errors are returned as formatted text
with isError=True, never thrown as exceptions. This ensures the LLM always
gets actionable guidance.
"""

from __future__ import annotations

import logging

from mcp.types import CallToolResult, TextContent
from reducto import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    UnprocessableEntityError,
)

logger = logging.getLogger("reducto-mcp")


def mcp_error(message: str, *, guidance: str) -> CallToolResult:
    """Create an MCP error response with actionable guidance for the LLM."""
    text = f"Error: {message}\n\nWhat to do: {guidance}"
    return CallToolResult(
        content=[TextContent(type="text", text=text)],
        isError=True,
    )


def _extract_detail(e: Exception) -> str:
    """Extract a user-safe detail message from an SDK exception."""
    body = getattr(e, "body", None)
    if isinstance(body, dict):
        detail = body.get("detail") or body.get("message") or body.get("error")
        if detail:
            return str(detail)
    return str(e.message) if hasattr(e, "message") else str(e)


def handle_sdk_error(e: Exception) -> CallToolResult:
    """Map a Reducto SDK exception to a user-friendly MCP error response.

    Never exposes stack traces, internal details, or PII.
    Always includes actionable guidance for the LLM.
    """
    logger.warning("Reducto SDK error: %s: %s", type(e).__name__, e)

    if isinstance(e, AuthenticationError):
        return mcp_error(
            "Authentication failed. The REDUCTO_API_KEY may be invalid or expired.",
            guidance="Ask the user to check their API key at https://app.reducto.ai",
        )

    if isinstance(e, PermissionDeniedError):
        return mcp_error(
            "Permission denied. The API key may lack required permissions.",
            guidance="Ask the user to check their API key permissions.",
        )

    if isinstance(e, RateLimitError):
        retry_after = ""
        if hasattr(e, "response") and e.response is not None:
            ra = e.response.headers.get("retry-after")
            if ra:
                retry_after = f" Retry after {ra} seconds."
        return mcp_error(
            f"Rate limited by Reducto API.{retry_after}",
            guidance="Wait a moment and retry the request.",
        )

    if isinstance(e, BadRequestError):
        detail = _extract_detail(e)
        return mcp_error(
            f"Invalid request: {detail}",
            guidance="Check the parameters and try again with corrected values.",
        )

    if isinstance(e, UnprocessableEntityError):
        detail = _extract_detail(e)
        return mcp_error(
            f"Validation error: {detail}",
            guidance="Check that all parameters match expected types and formats.",
        )

    if isinstance(e, NotFoundError):
        return mcp_error(
            "Resource not found. The job ID or document URL may be invalid.",
            guidance="Verify the job_id or document_url is correct.",
        )

    if isinstance(e, APITimeoutError):
        return mcp_error(
            "Request timed out. The document may be very large or complex.",
            guidance=(
                "Try again with a smaller page_range, or use a simpler document. "
                "The job may still be processing — check with get_job if a job_id was returned."
            ),
        )

    if isinstance(e, APIConnectionError):
        return mcp_error(
            "Cannot connect to Reducto API.",
            guidance="Check network connectivity. If using REDUCTO_BASE_URL, verify it's correct.",
        )

    if isinstance(e, InternalServerError):
        return mcp_error(
            "Reducto service error (transient). The document may still be processing.",
            guidance="Try again in a few seconds. If the error persists, try a smaller page_range.",
        )

    # Fallback for unexpected errors
    return mcp_error(
        f"Unexpected error: {type(e).__name__}",
        guidance="This may be a transient issue. Try again.",
    )
