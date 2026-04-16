"""Tests for device code authentication flow."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from mcp_server_reducto.auth import AuthError, device_auth_login


def _device_code_response() -> dict:
    return {
        "device_code": "test-device-code-abc",
        "user_code": "ABC-DEFGH",
        "verification_uri_complete": "https://studio.reducto.ai/cli-auth/verify?user_code=ABC-DEFGH",
        "interval": 1,
        "expires_in": 10,
    }


def _mock_httpx_response(data: dict, status: int = 200) -> httpx.Response:
    return httpx.Response(
        status,
        json=data,
        request=httpx.Request("POST", "https://example.com"),
    )


class TestDeviceAuthLogin:
    @pytest.mark.asyncio
    async def test_full_approval_flow(self, tmp_path, monkeypatch) -> None:
        """Test the happy path: request code → poll → approved → key saved."""
        config_path = tmp_path / "config.yaml"
        monkeypatch.setattr("mcp_server_reducto.config.CONFIG_PATH", config_path)
        monkeypatch.setattr("mcp_server_reducto.auth.read_saved_api_key", lambda: None)
        monkeypatch.setattr("mcp_server_reducto.auth.write_api_key", lambda key, client_id="mcp-server-reducto": config_path.write_text(f"api_key: {key}\n"))
        monkeypatch.setenv("REDUCTO_STUDIO_API_URL", "https://mock-studio.test")

        # Mock httpx.AsyncClient
        mock_client = AsyncMock()

        # First call: device code request
        mock_client.post = AsyncMock(side_effect=[
            _mock_httpx_response(_device_code_response()),
            _mock_httpx_response({"status": "pending"}),
            _mock_httpx_response({"status": "approved", "api_key": "sk-test-key-12345"}),
        ])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("mcp_server_reducto.auth.httpx.AsyncClient", return_value=mock_client):
            with patch("mcp_server_reducto.auth.webbrowser.open"):
                result = await device_auth_login(force=True)

        assert result == "sk-test-key-12345"
        assert "sk-test-key-12345" in config_path.read_text()

    @pytest.mark.asyncio
    async def test_existing_key_no_force(self, monkeypatch) -> None:
        """If a key exists and force=False, return the existing key without hitting the API."""
        monkeypatch.setattr("mcp_server_reducto.auth.read_saved_api_key", lambda: "existing-key")

        result = await device_auth_login(force=False)
        assert result == "existing-key"

    @pytest.mark.asyncio
    async def test_denied(self, tmp_path, monkeypatch) -> None:
        """Test that denial raises AuthError."""
        monkeypatch.setattr("mcp_server_reducto.auth.read_saved_api_key", lambda: None)
        monkeypatch.setenv("REDUCTO_STUDIO_API_URL", "https://mock-studio.test")

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=[
            _mock_httpx_response(_device_code_response()),
            _mock_httpx_response({"status": "denied"}),
        ])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("mcp_server_reducto.auth.httpx.AsyncClient", return_value=mock_client):
            with patch("mcp_server_reducto.auth.webbrowser.open"):
                with pytest.raises(AuthError, match="denied"):
                    await device_auth_login(force=True)

    @pytest.mark.asyncio
    async def test_expired(self, monkeypatch) -> None:
        """Test that expiration raises AuthError."""
        monkeypatch.setattr("mcp_server_reducto.auth.read_saved_api_key", lambda: None)
        monkeypatch.setenv("REDUCTO_STUDIO_API_URL", "https://mock-studio.test")

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=[
            _mock_httpx_response(_device_code_response()),
            _mock_httpx_response({"status": "expired"}),
        ])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("mcp_server_reducto.auth.httpx.AsyncClient", return_value=mock_client):
            with patch("mcp_server_reducto.auth.webbrowser.open"):
                with pytest.raises(AuthError, match="expired"):
                    await device_auth_login(force=True)

    @pytest.mark.asyncio
    async def test_device_code_request_failure(self, monkeypatch) -> None:
        """Test that a failed device code request raises AuthError."""
        monkeypatch.setattr("mcp_server_reducto.auth.read_saved_api_key", lambda: None)
        monkeypatch.setenv("REDUCTO_STUDIO_API_URL", "https://mock-studio.test")

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("mcp_server_reducto.auth.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(AuthError, match="Failed to request device code"):
                await device_auth_login(force=True)

    @pytest.mark.asyncio
    async def test_slow_down_handling(self, monkeypatch) -> None:
        """Test that 'slow_down' error is handled by waiting longer."""
        monkeypatch.setattr("mcp_server_reducto.auth.read_saved_api_key", lambda: None)
        monkeypatch.setattr("mcp_server_reducto.auth.write_api_key", lambda key: None)
        monkeypatch.setenv("REDUCTO_STUDIO_API_URL", "https://mock-studio.test")

        slow_down_response = httpx.Response(
            400,
            json={"error": "slow_down"},
            request=httpx.Request("POST", "https://example.com"),
        )

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=[
            _mock_httpx_response(_device_code_response()),
            httpx.HTTPStatusError("400", request=slow_down_response.request, response=slow_down_response),
            _mock_httpx_response({"status": "approved", "api_key": "sk-after-slowdown"}),
        ])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("mcp_server_reducto.auth.httpx.AsyncClient", return_value=mock_client):
            with patch("mcp_server_reducto.auth.webbrowser.open"):
                result = await device_auth_login(force=True)

        assert result == "sk-after-slowdown"
