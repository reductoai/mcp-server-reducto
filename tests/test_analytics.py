"""Tests for analytics (PostHog telemetry) module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from mcp.types import CallToolResult, TextContent

from mcp_server_reducto import analytics


@pytest.fixture(autouse=True)
def _reset_caches():
    analytics._get_client.cache_clear()
    analytics._machine_id.cache_clear()
    yield
    analytics._get_client.cache_clear()
    analytics._machine_id.cache_clear()


@pytest.fixture
def fake_posthog(monkeypatch):
    """Install a mock PostHog client and enable telemetry."""
    monkeypatch.setenv("REDUCTO_TELEMETRY", "1")
    fake = MagicMock()
    monkeypatch.setattr(analytics, "_get_client", lambda: fake)
    return fake


class TestTelemetryToggle:
    def test_enabled_by_default(self, monkeypatch):
        monkeypatch.delenv("REDUCTO_TELEMETRY", raising=False)
        assert analytics.is_telemetry_enabled() is True

    @pytest.mark.parametrize("value", ["0", "false", "FALSE", "no", "off"])
    def test_disabled_via_env(self, monkeypatch, value):
        monkeypatch.setenv("REDUCTO_TELEMETRY", value)
        assert analytics.is_telemetry_enabled() is False

    def test_unknown_value_treated_as_enabled(self, monkeypatch):
        monkeypatch.setenv("REDUCTO_TELEMETRY", "yes-please")
        assert analytics.is_telemetry_enabled() is True


class TestHashIdentifier:
    def test_stable(self):
        assert analytics.hash_identifier("hello") == analytics.hash_identifier("hello")

    def test_different_inputs_different_outputs(self):
        assert analytics.hash_identifier("a") != analytics.hash_identifier("b")

    def test_format(self):
        out = analytics.hash_identifier("anything")
        assert out.startswith("sha256:")
        assert len(out) == len("sha256:") + 16

    def test_does_not_expose_plaintext(self):
        secret = "sk_live_supersecret"
        assert secret not in analytics.hash_identifier(secret)


class TestTrack:
    def test_no_op_when_disabled(self, monkeypatch):
        monkeypatch.setenv("REDUCTO_TELEMETRY", "0")
        analytics.track("some.event", "user_1", {"x": 1})

    def test_swallows_capture_exceptions(self, fake_posthog):
        fake_posthog.capture.side_effect = RuntimeError("ingest down")
        analytics.track("x.y", "u", {})


class TestTrackedDecorator:
    @pytest.mark.asyncio
    async def test_fires_event_on_success(self, fake_posthog):
        @analytics.tracked("toy_tool")
        async def toy(ctx=None):
            return CallToolResult(content=[TextContent(type="text", text="ok")])

        await toy()
        kwargs = fake_posthog.capture.call_args.kwargs
        assert kwargs["event"] == "tool.toy_tool.invoked"
        assert kwargs["properties"]["tool"] == "toy_tool"
        assert kwargs["properties"]["status"] == "ok"
        assert kwargs["properties"]["latency_ms"] >= 0
        assert kwargs["properties"]["client"] == "mcp-server-reducto"

    @pytest.mark.asyncio
    async def test_records_error_status_on_isError_result(self, fake_posthog):
        @analytics.tracked("toy_tool")
        async def toy(ctx=None):
            return CallToolResult(
                content=[TextContent(type="text", text="bad")],
                isError=True,
            )

        await toy()
        assert fake_posthog.capture.call_args.kwargs["properties"]["status"] == "error"

    @pytest.mark.asyncio
    async def test_records_exception_status_when_function_raises(self, fake_posthog):
        @analytics.tracked("toy_tool")
        async def toy(ctx=None):
            raise ValueError("boom")

        with pytest.raises(ValueError):
            await toy()
        assert fake_posthog.capture.call_args.kwargs["properties"]["status"] == "exception"

    @pytest.mark.asyncio
    async def test_no_op_when_disabled(self, monkeypatch):
        monkeypatch.setenv("REDUCTO_TELEMETRY", "0")

        @analytics.tracked("toy_tool")
        async def toy(ctx=None):
            return CallToolResult(content=[TextContent(type="text", text="ok")])

        result = await toy()
        assert result.content[0].text == "ok"


class TestLifespanStart:
    def test_first_run_writes_sentinel_and_fires_installed(self, tmp_path, monkeypatch):
        sentinel = tmp_path / "mcp_installed"
        monkeypatch.setattr(analytics, "_INSTALL_SENTINEL", sentinel)
        with patch.object(analytics, "track") as mock_track:
            analytics.track_lifespan_start("api-key-xyz", "stdio")

        assert sentinel.exists()
        events = [c.args[0] for c in mock_track.call_args_list]
        assert events == ["mcp.installed", "mcp.start"]

    def test_subsequent_run_only_fires_start(self, tmp_path, monkeypatch):
        sentinel = tmp_path / "mcp_installed"
        sentinel.write_text("0.1.0")
        monkeypatch.setattr(analytics, "_INSTALL_SENTINEL", sentinel)
        with patch.object(analytics, "track") as mock_track:
            analytics.track_lifespan_start("api-key-xyz", "stdio")

        events = [c.args[0] for c in mock_track.call_args_list]
        assert events == ["mcp.start"]

    def test_hosted_mode_uses_machine_id_when_no_api_key(self, tmp_path, monkeypatch):
        monkeypatch.setattr(analytics, "_INSTALL_SENTINEL", tmp_path / "mcp_installed")
        monkeypatch.setattr(analytics, "_MACHINE_ID_PATH", tmp_path / "machine_id")
        with patch.object(analytics, "track") as mock_track:
            analytics.track_lifespan_start(api_key=None, transport="hosted")

        # all events should use the same machine: id (no api_key available)
        distinct_ids = {c.args[1] for c in mock_track.call_args_list}
        assert len(distinct_ids) == 1
        only_id = distinct_ids.pop()
        assert only_id.startswith(("machine:", "anon:"))
