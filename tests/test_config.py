"""Tests for config module."""

from __future__ import annotations

from pathlib import Path

import pytest

from mcp_server_reducto.config import (
    get_api_key,
    get_base_url,
    get_max_response_size,
    get_port,
    get_timeout,
    get_transport,
    read_saved_api_key,
    write_api_key,
)


class TestGetApiKey:
    def test_returns_key_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("REDUCTO_API_KEY", "test-key-123")
        assert get_api_key() == "test-key-123"

    def test_strips_whitespace_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("REDUCTO_API_KEY", "  test-key-123  ")
        assert get_api_key() == "test-key-123"

    def test_falls_back_to_config_yaml(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.delenv("REDUCTO_API_KEY", raising=False)
        config_path = tmp_path / "config.yaml"
        config_path.write_text("api_key: saved-key-456\n")
        monkeypatch.setattr("mcp_server_reducto.config.CONFIG_PATH", config_path)

        assert get_api_key() == "saved-key-456"

    def test_env_takes_priority_over_config(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setenv("REDUCTO_API_KEY", "env-key")
        config_path = tmp_path / "config.yaml"
        config_path.write_text("api_key: saved-key\n")
        monkeypatch.setattr("mcp_server_reducto.config.CONFIG_PATH", config_path)

        assert get_api_key() == "env-key"

    def test_raises_when_no_key_anywhere(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.delenv("REDUCTO_API_KEY", raising=False)
        config_path = tmp_path / "nonexistent" / "config.yaml"
        monkeypatch.setattr("mcp_server_reducto.config.CONFIG_PATH", config_path)

        with pytest.raises(RuntimeError, match="No Reducto API key found"):
            get_api_key()

    def test_raises_when_env_empty(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setenv("REDUCTO_API_KEY", "")
        config_path = tmp_path / "nonexistent" / "config.yaml"
        monkeypatch.setattr("mcp_server_reducto.config.CONFIG_PATH", config_path)

        with pytest.raises(RuntimeError, match="No Reducto API key found"):
            get_api_key()

    def test_error_message_mentions_login(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.delenv("REDUCTO_API_KEY", raising=False)
        config_path = tmp_path / "nonexistent" / "config.yaml"
        monkeypatch.setattr("mcp_server_reducto.config.CONFIG_PATH", config_path)

        with pytest.raises(RuntimeError, match="mcp-server-reducto --login"):
            get_api_key()


class TestReadSavedApiKey:
    def test_reads_from_yaml(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        config_path = tmp_path / "config.yaml"
        config_path.write_text("api_key: my-saved-key\n")
        monkeypatch.setattr("mcp_server_reducto.config.CONFIG_PATH", config_path)

        assert read_saved_api_key() == "my-saved-key"

    def test_handles_quoted_values(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        config_path = tmp_path / "config.yaml"
        config_path.write_text('api_key: "quoted-key"\n')
        monkeypatch.setattr("mcp_server_reducto.config.CONFIG_PATH", config_path)

        assert read_saved_api_key() == "quoted-key"

    def test_handles_single_quoted(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        config_path = tmp_path / "config.yaml"
        config_path.write_text("api_key: 'single-quoted'\n")
        monkeypatch.setattr("mcp_server_reducto.config.CONFIG_PATH", config_path)

        assert read_saved_api_key() == "single-quoted"

    def test_returns_none_when_missing(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        config_path = tmp_path / "nonexistent" / "config.yaml"
        monkeypatch.setattr("mcp_server_reducto.config.CONFIG_PATH", config_path)

        assert read_saved_api_key() is None

    def test_returns_none_when_empty_file(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        config_path = tmp_path / "config.yaml"
        config_path.write_text("")
        monkeypatch.setattr("mcp_server_reducto.config.CONFIG_PATH", config_path)

        assert read_saved_api_key() is None

    def test_returns_none_when_no_api_key_line(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        config_path = tmp_path / "config.yaml"
        config_path.write_text("other_setting: value\n")
        monkeypatch.setattr("mcp_server_reducto.config.CONFIG_PATH", config_path)

        assert read_saved_api_key() is None

    def test_returns_none_for_empty_value(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        config_path = tmp_path / "config.yaml"
        config_path.write_text("api_key: \n")
        monkeypatch.setattr("mcp_server_reducto.config.CONFIG_PATH", config_path)

        assert read_saved_api_key() is None


class TestWriteApiKey:
    def test_writes_per_client_format(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        config_path = tmp_path / "config.yaml"
        monkeypatch.setattr("mcp_server_reducto.config.CONFIG_PATH", config_path)

        write_api_key("new-key-789")

        content = config_path.read_text()
        assert "credentials:" in content
        assert "mcp-server-reducto:" in content
        assert "api_key: new-key-789" in content

    def test_creates_parent_directory(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        config_path = tmp_path / "subdir" / "config.yaml"
        monkeypatch.setattr("mcp_server_reducto.config.CONFIG_PATH", config_path)

        write_api_key("key")

        assert config_path.exists()
        content = config_path.read_text()
        assert "api_key: key" in content

    def test_strips_whitespace(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        config_path = tmp_path / "config.yaml"
        monkeypatch.setattr("mcp_server_reducto.config.CONFIG_PATH", config_path)

        write_api_key("  padded-key  ")

        content = config_path.read_text()
        assert "api_key: padded-key" in content

    def test_roundtrip(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        config_path = tmp_path / "config.yaml"
        monkeypatch.setattr("mcp_server_reducto.config.CONFIG_PATH", config_path)

        write_api_key("roundtrip-key")
        assert read_saved_api_key() == "roundtrip-key"

    def test_preserves_other_clients(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        config_path = tmp_path / "config.yaml"
        config_path.write_text(
            "credentials:\n  reducto-cli:\n    api_key: cli-key\n"
        )
        monkeypatch.setattr("mcp_server_reducto.config.CONFIG_PATH", config_path)

        write_api_key("mcp-key")

        content = config_path.read_text()
        assert "reducto-cli:" in content
        assert "cli-key" in content
        assert "mcp-server-reducto:" in content
        assert "mcp-key" in content


class TestReadApiKeyFallback:
    def test_reads_legacy_flat_format(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        config_path = tmp_path / "config.yaml"
        config_path.write_text("api_key: legacy-key\n")
        monkeypatch.setattr("mcp_server_reducto.config.CONFIG_PATH", config_path)

        assert read_saved_api_key() == "legacy-key"

    def test_own_client_takes_priority(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        config_path = tmp_path / "config.yaml"
        config_path.write_text(
            "credentials:\n"
            "  mcp-server-reducto:\n"
            "    api_key: mcp-key\n"
            "  reducto-cli:\n"
            "    api_key: cli-key\n"
        )
        monkeypatch.setattr("mcp_server_reducto.config.CONFIG_PATH", config_path)

        assert read_saved_api_key() == "mcp-key"

    def test_falls_back_to_other_client(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        config_path = tmp_path / "config.yaml"
        config_path.write_text(
            "credentials:\n  reducto-cli:\n    api_key: cli-key\n"
        )
        monkeypatch.setattr("mcp_server_reducto.config.CONFIG_PATH", config_path)

        assert read_saved_api_key() == "cli-key"


class TestGetBaseUrl:
    def test_returns_none_when_not_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("REDUCTO_BASE_URL", raising=False)
        assert get_base_url() is None

    def test_returns_url_when_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("REDUCTO_BASE_URL", "https://eu.reducto.ai")
        assert get_base_url() == "https://eu.reducto.ai"


class TestGetTimeout:
    def test_default_is_300(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("REDUCTO_MCP_TIMEOUT", raising=False)
        assert get_timeout() == 300.0

    def test_custom_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("REDUCTO_MCP_TIMEOUT", "600")
        assert get_timeout() == 600.0


class TestGetMaxResponseSize:
    def test_default_is_50000(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("REDUCTO_MCP_MAX_RESPONSE_SIZE", raising=False)
        assert get_max_response_size() == 50000

    def test_custom_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("REDUCTO_MCP_MAX_RESPONSE_SIZE", "100000")
        assert get_max_response_size() == 100000


class TestGetTransport:
    def test_default_is_stdio(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("REDUCTO_MCP_TRANSPORT", raising=False)
        assert get_transport() == "stdio"

    def test_http(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("REDUCTO_MCP_TRANSPORT", "http")
        assert get_transport() == "http"


class TestGetPort:
    def test_default_is_8000(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("REDUCTO_MCP_PORT", raising=False)
        assert get_port() == 8000

    def test_custom_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("REDUCTO_MCP_PORT", "9090")
        assert get_port() == 9090
