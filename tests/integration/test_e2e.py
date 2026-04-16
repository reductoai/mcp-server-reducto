"""End-to-end integration tests against the real Reducto API.

These tests require REDUCTO_API_KEY to be set. They are skipped otherwise.
Run with: REDUCTO_API_KEY=... pytest tests/integration/ -v
"""

from __future__ import annotations

import json
import os

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("REDUCTO_API_KEY"),
    reason="REDUCTO_API_KEY not set — skipping integration tests",
)

TEST_PDF_URL = "https://ci.reducto.ai/onepager.pdf"


@pytest.fixture
async def client():
    """Create a real AsyncReducto client."""
    from reducto import AsyncReducto

    return AsyncReducto(api_key=os.environ["REDUCTO_API_KEY"])


@pytest.fixture
def ctx(client):
    """Create a mock context that returns the real client."""
    from unittest.mock import MagicMock

    ctx = MagicMock()
    server = MagicMock()
    server._test_client = client
    ctx.fastmcp = server
    return ctx


class TestParseIntegration:
    @pytest.mark.asyncio
    async def test_parse_onepager(self, ctx) -> None:
        from mcp_server_reducto.tools.parse import parse_document

        result = await parse_document(
            document_url=TEST_PDF_URL,
            ctx=ctx,
        )
        assert result.isError is not True
        data = json.loads(result.content[0].text)
        assert "job_id" in data
        assert data["num_blocks"] > 0

    @pytest.mark.asyncio
    async def test_parse_with_html_tables(self, ctx) -> None:
        from mcp_server_reducto.tools.parse import parse_document

        result = await parse_document(
            document_url=TEST_PDF_URL,
            table_output_format="html",
            ctx=ctx,
        )
        assert result.isError is not True


class TestExtractIntegration:
    @pytest.mark.asyncio
    async def test_extract_simple_schema(self, ctx) -> None:
        from mcp_server_reducto.tools.extract import extract_data

        result = await extract_data(
            document_url=TEST_PDF_URL,
            schema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "The document title"},
                },
            },
            ctx=ctx,
        )
        assert result.isError is not True
        data = json.loads(result.content[0].text)
        assert "result" in data


class TestJobIdChaining:
    @pytest.mark.asyncio
    async def test_parse_then_extract_via_jobid(self, ctx) -> None:
        """Test the jobid:// chaining flow — parse once, extract without re-parsing."""
        from mcp_server_reducto.tools.extract import extract_data
        from mcp_server_reducto.tools.parse import parse_document

        # Step 1: Parse
        parse_result = await parse_document(document_url=TEST_PDF_URL, ctx=ctx)
        assert parse_result.isError is not True
        parse_data = json.loads(parse_result.content[0].text)
        job_id = parse_data["job_id"]

        # Step 2: Extract using jobid://
        extract_result = await extract_data(
            document_url=f"jobid://{job_id}",
            schema={"type": "object", "properties": {"title": {"type": "string"}}},
            ctx=ctx,
        )
        assert extract_result.isError is not True


class TestGetJobIntegration:
    @pytest.mark.asyncio
    async def test_get_job_after_parse(self, ctx) -> None:
        from mcp_server_reducto.tools.jobs import get_job
        from mcp_server_reducto.tools.parse import parse_document

        parse_result = await parse_document(document_url=TEST_PDF_URL, ctx=ctx)
        parse_data = json.loads(parse_result.content[0].text)
        job_id = parse_data["job_id"]

        job_result = await get_job(job_id=job_id, ctx=ctx)
        assert job_result.isError is not True
