"""Tests for error handling module."""

from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import pytest

from mcp_server_reducto.errors import handle_sdk_error, mcp_error


class TestMcpError:
    def test_creates_error_result(self) -> None:
        result = mcp_error("Something failed", guidance="Try again")
        assert result.isError is True
        assert len(result.content) == 1
        assert "Something failed" in result.content[0].text
        assert "Try again" in result.content[0].text


def _make_request() -> httpx.Request:
    return httpx.Request("POST", "https://platform.reducto.ai/parse")


def _make_response(status: int) -> httpx.Response:
    return httpx.Response(status, request=_make_request())


class TestHandleSdkError:
    def test_authentication_error(self) -> None:
        from reducto import AuthenticationError

        e = AuthenticationError(
            message="Invalid API key",
            response=_make_response(401),
            body={"detail": "Invalid API key"},
        )
        result = handle_sdk_error(e)
        assert result.isError is True
        assert "Authentication failed" in result.content[0].text
        assert "API key" in result.content[0].text

    def test_permission_denied_error(self) -> None:
        from reducto import PermissionDeniedError

        e = PermissionDeniedError(
            message="Forbidden",
            response=_make_response(403),
            body=None,
        )
        result = handle_sdk_error(e)
        assert result.isError is True
        assert "Permission denied" in result.content[0].text

    def test_rate_limit_error(self) -> None:
        from reducto import RateLimitError

        resp = _make_response(429)
        e = RateLimitError(
            message="Too many requests",
            response=resp,
            body=None,
        )
        result = handle_sdk_error(e)
        assert result.isError is True
        assert "Rate limited" in result.content[0].text

    def test_rate_limit_with_retry_after(self) -> None:
        from reducto import RateLimitError

        resp = httpx.Response(429, request=_make_request(), headers={"retry-after": "30"})
        e = RateLimitError(
            message="Too many requests",
            response=resp,
            body=None,
        )
        result = handle_sdk_error(e)
        assert "30 seconds" in result.content[0].text

    def test_bad_request_error(self) -> None:
        from reducto import BadRequestError

        e = BadRequestError(
            message="Invalid page_range",
            response=_make_response(400),
            body={"detail": "page_range must be 1-indexed"},
        )
        result = handle_sdk_error(e)
        assert result.isError is True
        assert "Invalid request" in result.content[0].text
        assert "page_range" in result.content[0].text

    def test_unprocessable_entity_error(self) -> None:
        from reducto import UnprocessableEntityError

        e = UnprocessableEntityError(
            message="Validation error",
            response=_make_response(422),
            body={"detail": "schema is required"},
        )
        result = handle_sdk_error(e)
        assert result.isError is True
        assert "Validation error" in result.content[0].text

    def test_not_found_error(self) -> None:
        from reducto import NotFoundError

        e = NotFoundError(
            message="Not found",
            response=_make_response(404),
            body=None,
        )
        result = handle_sdk_error(e)
        assert result.isError is True
        assert "not found" in result.content[0].text.lower()

    def test_timeout_error(self) -> None:
        from reducto import APITimeoutError

        e = APITimeoutError(request=_make_request())
        result = handle_sdk_error(e)
        assert result.isError is True
        assert "timed out" in result.content[0].text.lower()

    def test_connection_error(self) -> None:
        from reducto import APIConnectionError

        e = APIConnectionError(request=_make_request())
        result = handle_sdk_error(e)
        assert result.isError is True
        assert "Cannot connect" in result.content[0].text

    def test_internal_server_error(self) -> None:
        from reducto import InternalServerError

        e = InternalServerError(
            message="Internal error",
            response=_make_response(500),
            body=None,
        )
        result = handle_sdk_error(e)
        assert result.isError is True
        assert "service error" in result.content[0].text.lower()

    def test_unknown_error_fallback(self) -> None:
        result = handle_sdk_error(ValueError("something weird"))
        assert result.isError is True
        assert "Unexpected error" in result.content[0].text
        assert "ValueError" in result.content[0].text
