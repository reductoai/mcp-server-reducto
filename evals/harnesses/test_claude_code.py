"""Normalizer tests — shapes taken from real stream-json probes."""
from evals.harnesses.claude_code import _normalize_event


def test_system_init_yields_nothing():
    sj = {"type": "system", "subtype": "init", "session_id": "abc", "model": "claude-sonnet-4-6"}
    assert _normalize_event(sj) == []


def test_assistant_text_yields_assistant_event():
    sj = {
        "type": "assistant",
        "message": {
            "role": "assistant",
            "content": [{"type": "text", "text": "hello world"}],
        },
    }
    out = _normalize_event(sj)
    assert out == [{"type": "assistant", "text": "hello world"}]


def test_assistant_tool_use_yields_tool_use_event():
    sj = {
        "type": "assistant",
        "message": {
            "content": [
                {"type": "text", "text": "calling tool"},
                {
                    "type": "tool_use",
                    "id": "toolu_1",
                    "name": "mcp__reducto__upload_file",
                    "input": {"path": "/tmp/x.pdf"},
                },
            ]
        },
    }
    out = _normalize_event(sj)
    assert out[0] == {"type": "assistant", "text": "calling tool"}
    assert out[1] == {
        "type": "tool_use",
        "id": "toolu_1",
        "name": "mcp__reducto__upload_file",
        "input": {"path": "/tmp/x.pdf"},
    }


def test_user_tool_result_yields_tool_result_event():
    sj = {
        "type": "user",
        "message": {
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "toolu_1",
                    "content": "ok",
                }
            ]
        },
    }
    out = _normalize_event(sj)
    assert out == [{"type": "tool_result", "tool_use_id": "toolu_1", "content": "ok"}]


def test_tool_result_list_content_joined():
    sj = {
        "type": "user",
        "message": {
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "toolu_2",
                    "content": [{"type": "text", "text": "line1"}, {"type": "text", "text": "line2"}],
                }
            ]
        },
    }
    out = _normalize_event(sj)
    assert out[0]["content"] == "line1\nline2"


def test_result_event_yields_nothing():
    sj = {"type": "result", "total_cost_usd": 0.123, "is_error": False}
    assert _normalize_event(sj) == []


def test_auth_error_message_still_parses():
    # real shape captured from a --bare probe without ANTHROPIC_API_KEY
    sj = {
        "type": "assistant",
        "message": {
            "content": [{"type": "text", "text": "Not logged in · Please run /login"}]
        },
        "error": "authentication_failed",
    }
    out = _normalize_event(sj)
    assert out == [{"type": "assistant", "text": "Not logged in · Please run /login"}]
