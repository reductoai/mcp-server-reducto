"""Tests for error handling module."""

from __future__ import annotations

import httpx
from mcp.types import TextContent

from mcp_server_reducto.errors import handle_sdk_error, mcp_error


class TestMcpError:
    def test_creates_error_result(self) -> None:
        result = mcp_error("Something failed", guidance="Try again")
        assert result.isError is True
        assert len(result.content) == 1
        content = result.content[0]
        assert isinstance(content, TextContent)
        assert "Something failed" in content.text
        assert "Try again" in content.text


def _make_request() -> httpx.Request:
    return httpx.Request("POST", "https://platform.reducto.ai/parse")


def _make_response(status: int) -> httpx.Response:
    return httpx.Response(status, request=_make_request())


class TestHandleSdkError:
    def _check(self, result, *substrings: str) -> None:
        """Assert result is an error with TextContent containing all substrings."""
        assert result.isError is True
        content = result.content[0]
        assert isinstance(content, TextContent)
        for s in substrings:
            assert s in content.text, f"Expected {s!r} in {content.text!r}"

    def test_authentication_error(self) -> None:
        from reducto import AuthenticationError

        e = AuthenticationError(
            message="Invalid API key",
            response=_make_response(401),
            body={"detail": "Invalid API key"},
        )
        self._check(handle_sdk_error(e), "Authentication failed", "API key")

    def test_permission_denied_error(self) -> None:
        from reducto import PermissionDeniedError

        e = PermissionDeniedError(
            message="Forbidden",
            response=_make_response(403),
            body=None,
        )
        self._check(handle_sdk_error(e), "Permission denied")

    def test_rate_limit_error(self) -> None:
        from reducto import RateLimitError

        e = RateLimitError(
            message="Too many requests",
            response=_make_response(429),
            body=None,
        )
        self._check(handle_sdk_error(e), "Rate limited")

    def test_rate_limit_with_retry_after(self) -> None:
        from reducto import RateLimitError

        resp = httpx.Response(429, request=_make_request(), headers={"retry-after": "30"})
        e = RateLimitError(
            message="Too many requests",
            response=resp,
            body=None,
        )
        self._check(handle_sdk_error(e), "30 seconds")

    def test_bad_request_error(self) -> None:
        from reducto import BadRequestError

        e = BadRequestError(
            message="Invalid page_range",
            response=_make_response(400),
            body={"detail": "page_range must be 1-indexed"},
        )
        self._check(handle_sdk_error(e), "Invalid request", "page_range")

    def test_unprocessable_entity_error(self) -> None:
        from reducto import UnprocessableEntityError

        e = UnprocessableEntityError(
            message="Validation error",
            response=_make_response(422),
            body={"detail": "schema is required"},
        )
        self._check(handle_sdk_error(e), "Validation error")

    def test_not_found_error(self) -> None:
        from reducto import NotFoundError

        e = NotFoundError(
            message="Not found",
            response=_make_response(404),
            body=None,
        )
        result = handle_sdk_error(e)
        assert result.isError is True
        content = result.content[0]
        assert isinstance(content, TextContent)
        assert "not found" in content.text.lower()

    def test_timeout_error(self) -> None:
        from reducto import APITimeoutError

        e = APITimeoutError(request=_make_request())
        result = handle_sdk_error(e)
        assert result.isError is True
        content = result.content[0]
        assert isinstance(content, TextContent)
        assert "timed out" in content.text.lower()

    def test_connection_error(self) -> None:
        from reducto import APIConnectionError

        e = APIConnectionError(request=_make_request())
        self._check(handle_sdk_error(e), "Cannot connect")

    def test_internal_server_error(self) -> None:
        from reducto import InternalServerError

        e = InternalServerError(
            message="Internal error",
            response=_make_response(500),
            body=None,
        )
        result = handle_sdk_error(e)
        assert result.isError is True
        content = result.content[0]
        assert isinstance(content, TextContent)
        assert "service error" in content.text.lower()

    def test_unknown_error_fallback(self) -> None:
        self._check(handle_sdk_error(ValueError("something weird")), "Unexpected error", "ValueError")
