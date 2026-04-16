"""Tests for response formatting and truncation."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from mcp_server_reducto.response import (
    format_classify_response,
    format_edit_response,
    format_extract_response,
    format_parse_response,
    format_split_response,
    format_upload_response,
)


class TestFormatParseResponse:
    def test_basic_formatting(self) -> None:
        block = SimpleNamespace(type="text", content="Hello world")
        chunk = SimpleNamespace(blocks=[block])
        result = SimpleNamespace(type="full", chunks=[chunk])
        usage = SimpleNamespace(num_pages=1, credits=0.5)
        response = SimpleNamespace(
            job_id="job123",
            duration=1.5,
            studio_link="https://studio.reducto.ai/job123",
            usage=usage,
            result=result,
        )

        text = format_parse_response(response)
        data = json.loads(text)

        assert data["job_id"] == "job123"
        assert data["duration_seconds"] == 1.5
        assert data["studio_link"] == "https://studio.reducto.ai/job123"
        assert data["usage"]["num_pages"] == 1
        assert data["num_blocks"] == 1
        assert data["blocks"][0]["type"] == "text"
        assert data["blocks"][0]["content"] == "Hello world"

    def test_url_result_type(self) -> None:
        result = SimpleNamespace(type="url", url="https://s3.example.com/result.json")
        usage = SimpleNamespace(num_pages=50, credits=10.0)
        response = SimpleNamespace(
            job_id="job456",
            duration=30.0,
            studio_link=None,
            usage=usage,
            result=result,
        )

        text = format_parse_response(response)
        data = json.loads(text)

        assert data["result_type"] == "url"
        assert data["result_url"] == "https://s3.example.com/result.json"

    def test_block_type_counts(self) -> None:
        blocks = [
            SimpleNamespace(type="text", content="a"),
            SimpleNamespace(type="text", content="b"),
            SimpleNamespace(type="table", content="<table></table>"),
        ]
        chunk = SimpleNamespace(blocks=blocks)
        result = SimpleNamespace(type="full", chunks=[chunk])
        usage = SimpleNamespace(num_pages=1, credits=0.5)
        response = SimpleNamespace(job_id="j", duration=0.5, studio_link=None, usage=usage, result=result)

        text = format_parse_response(response)
        data = json.loads(text)
        assert data["block_type_counts"]["text"] == 2
        assert data["block_type_counts"]["table"] == 1

    def test_truncation(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("REDUCTO_MCP_MAX_RESPONSE_SIZE", "500")

        # Create a response that exceeds 500 chars
        blocks = [SimpleNamespace(type="text", content="x" * 100) for _ in range(20)]
        chunk = SimpleNamespace(blocks=blocks)
        result = SimpleNamespace(type="full", chunks=[chunk])
        usage = SimpleNamespace(num_pages=1, credits=0.5)
        response = SimpleNamespace(job_id="j_trunc", duration=0.5, studio_link=None, usage=usage, result=result)

        text = format_parse_response(response)
        data = json.loads(text)

        assert data["truncated"] is True
        assert len(data["blocks"]) < 20
        assert "truncation_note" in data
        assert "j_trunc" in data["truncation_note"]


class TestFormatExtractResponse:
    def test_basic_formatting(self) -> None:
        usage = SimpleNamespace(num_pages=2, num_fields=3, credits=2.0)
        response = SimpleNamespace(
            job_id="ext123",
            studio_link="https://studio.reducto.ai/ext123",
            usage=usage,
            result={"name": "Acme", "amount": 100},
        )

        text = format_extract_response(response)
        data = json.loads(text)

        assert data["job_id"] == "ext123"
        assert data["result"]["name"] == "Acme"
        assert data["usage"]["num_fields"] == 3


class TestFormatSplitResponse:
    def test_basic_formatting(self) -> None:
        s1 = SimpleNamespace(name="Intro", pages=[1, 2], conf="high")
        s2 = SimpleNamespace(name="Body", pages=[3, 4, 5], conf="low")
        result = SimpleNamespace(splits=[s1, s2])
        usage = SimpleNamespace(num_pages=5, credits=2.0)
        response = SimpleNamespace(usage=usage, result=result)

        text = format_split_response(response)
        data = json.loads(text)

        assert len(data["splits"]) == 2
        assert data["splits"][0]["name"] == "Intro"
        assert data["splits"][0]["pages"] == [1, 2]
        assert data["splits"][0]["confidence"] == "high"


class TestFormatClassifyResponse:
    def test_basic_formatting(self) -> None:
        result = SimpleNamespace(category="invoice")
        cat_conf = [
            SimpleNamespace(category="invoice", confidence=0.9),
            SimpleNamespace(category="receipt", confidence=0.1),
        ]
        confidence = SimpleNamespace(categories=cat_conf)
        response = SimpleNamespace(
            job_id="cls123", duration=1.0, result=result, response_confidence=confidence
        )

        text = format_classify_response(response)
        data = json.loads(text)

        assert data["category"] == "invoice"
        assert data["category_confidences"][0]["confidence"] == 0.9


class TestFormatEditResponse:
    def test_basic_formatting(self) -> None:
        usage = SimpleNamespace(num_pages=1)
        response = SimpleNamespace(
            document_url="https://storage.reducto.ai/edited.pdf", usage=usage
        )

        text = format_edit_response(response)
        data = json.loads(text)

        assert data["document_url"] == "https://storage.reducto.ai/edited.pdf"
        assert data["usage"]["num_pages"] == 1


class TestFormatUploadResponse:
    def test_basic_formatting(self) -> None:
        response = SimpleNamespace(file_id="reducto://abc123", presigned_url=None)

        text = format_upload_response(response)
        data = json.loads(text)

        assert data["file_id"] == "reducto://abc123"
