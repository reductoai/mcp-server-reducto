"""Tests for all MCP tool implementations."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server_reducto.tools.classify import classify_document
from mcp_server_reducto.tools.edit import edit_document
from mcp_server_reducto.tools.extract import extract_data
from mcp_server_reducto.tools.jobs import get_job, list_jobs
from mcp_server_reducto.tools.parse import parse_document
from mcp_server_reducto.tools.split import split_document
from mcp_server_reducto.tools.upload import upload_file

# ─── Parse ───────────────────────────────────────────────────────────


class TestParseDocument:
    @pytest.mark.asyncio
    async def test_basic_parse(self, mock_ctx: MagicMock, mock_client: AsyncMock) -> None:
        result = await parse_document(
            document_url="https://example.com/doc.pdf",
            ctx=mock_ctx,
        )
        assert result.isError is not True
        data = json.loads(result.content[0].text)
        assert data["job_id"] == "job_parse_123"
        assert data["num_blocks"] == 3

        mock_client.parse.run.assert_called_once()
        call_kwargs = mock_client.parse.run.call_args.kwargs
        assert call_kwargs["input"] == "https://example.com/doc.pdf"

    @pytest.mark.asyncio
    async def test_with_formatting_options(self, mock_ctx: MagicMock, mock_client: AsyncMock) -> None:
        result = await parse_document(
            document_url="https://example.com/doc.pdf",
            table_output_format="html",
            add_page_markers=True,
            ctx=mock_ctx,
        )
        assert result.isError is not True
        call_kwargs = mock_client.parse.run.call_args.kwargs
        assert call_kwargs["formatting"]["table_output_format"] == "html"
        assert call_kwargs["formatting"]["add_page_markers"] is True

    @pytest.mark.asyncio
    async def test_with_page_range(self, mock_ctx: MagicMock, mock_client: AsyncMock) -> None:
        result = await parse_document(
            document_url="https://example.com/doc.pdf",
            page_range="1-5",
            ctx=mock_ctx,
        )
        assert result.isError is not True
        call_kwargs = mock_client.parse.run.call_args.kwargs
        assert call_kwargs["settings"]["page_range"] == "1-5"

    @pytest.mark.asyncio
    async def test_with_chunk_mode(self, mock_ctx: MagicMock, mock_client: AsyncMock) -> None:
        await parse_document(
            document_url="https://example.com/doc.pdf",
            chunk_mode="variable",
            ctx=mock_ctx,
        )
        call_kwargs = mock_client.parse.run.call_args.kwargs
        assert call_kwargs["retrieval"]["chunking"]["chunk_mode"] == "variable"

    @pytest.mark.asyncio
    async def test_with_agentic(self, mock_ctx: MagicMock, mock_client: AsyncMock) -> None:
        await parse_document(
            document_url="https://example.com/doc.pdf",
            agentic=["table", "figure"],
            ctx=mock_ctx,
        )
        call_kwargs = mock_client.parse.run.call_args.kwargs
        assert call_kwargs["enhance"]["agentic"] == [
            {"scope": "table", "mode": "default"},
            {"scope": "figure", "mode": "default"},
        ]

    @pytest.mark.asyncio
    async def test_with_options_dict(self, mock_ctx: MagicMock, mock_client: AsyncMock) -> None:
        await parse_document(
            document_url="https://example.com/doc.pdf",
            options={"spreadsheet": {"clustering": "fast"}},
            ctx=mock_ctx,
        )
        call_kwargs = mock_client.parse.run.call_args.kwargs
        assert call_kwargs["spreadsheet"] == {"clustering": "fast"}

    @pytest.mark.asyncio
    async def test_with_options_json_string(self, mock_ctx: MagicMock, mock_client: AsyncMock) -> None:
        await parse_document(
            document_url="https://example.com/doc.pdf",
            options='{"spreadsheet": {"clustering": "fast"}}',
            ctx=mock_ctx,
        )
        call_kwargs = mock_client.parse.run.call_args.kwargs
        assert call_kwargs["spreadsheet"] == {"clustering": "fast"}

    @pytest.mark.asyncio
    async def test_invalid_url_scheme(self, mock_ctx: MagicMock) -> None:
        result = await parse_document(
            document_url="ftp://example.com/doc.pdf",
            ctx=mock_ctx,
        )
        assert result.isError is True
        assert "Invalid URL scheme" in result.content[0].text

    @pytest.mark.asyncio
    async def test_invalid_table_format(self, mock_ctx: MagicMock) -> None:
        result = await parse_document(
            document_url="https://example.com/doc.pdf",
            table_output_format="xml",
            ctx=mock_ctx,
        )
        assert result.isError is True
        assert "Invalid table_output_format" in result.content[0].text

    @pytest.mark.asyncio
    async def test_invalid_chunk_mode(self, mock_ctx: MagicMock) -> None:
        result = await parse_document(
            document_url="https://example.com/doc.pdf",
            chunk_mode="invalid",
            ctx=mock_ctx,
        )
        assert result.isError is True

    @pytest.mark.asyncio
    async def test_sdk_error_handled(self, mock_ctx: MagicMock, mock_client: AsyncMock) -> None:
        import httpx
        from reducto import BadRequestError

        mock_client.parse.run.side_effect = BadRequestError(
            message="Bad request",
            response=httpx.Response(400, request=httpx.Request("POST", "https://api.reducto.ai/parse")),
            body={"detail": "Invalid input"},
        )
        result = await parse_document(
            document_url="https://example.com/doc.pdf",
            ctx=mock_ctx,
        )
        assert result.isError is True
        assert "Invalid request" in result.content[0].text

    @pytest.mark.asyncio
    async def test_jobid_url(self, mock_ctx: MagicMock, mock_client: AsyncMock) -> None:
        result = await parse_document(
            document_url="jobid://previous_job_123",
            ctx=mock_ctx,
        )
        assert result.isError is not True
        call_kwargs = mock_client.parse.run.call_args.kwargs
        assert call_kwargs["input"] == "jobid://previous_job_123"


# ─── Extract ─────────────────────────────────────────────────────────


class TestExtractData:
    @pytest.mark.asyncio
    async def test_basic_extract(self, mock_ctx: MagicMock, mock_client: AsyncMock) -> None:
        result = await extract_data(
            document_url="https://example.com/invoice.pdf",
            schema={"type": "object", "properties": {"amount": {"type": "number"}}},
            ctx=mock_ctx,
        )
        assert result.isError is not True
        data = json.loads(result.content[0].text)
        assert data["job_id"] == "job_extract_456"
        assert data["result"]["name"] == "Acme Corp"

        call_kwargs = mock_client.extract.run.call_args.kwargs
        assert call_kwargs["input"] == "https://example.com/invoice.pdf"
        assert call_kwargs["instructions"]["schema"]["type"] == "object"

    @pytest.mark.asyncio
    async def test_with_system_prompt(self, mock_ctx: MagicMock, mock_client: AsyncMock) -> None:
        await extract_data(
            document_url="https://example.com/doc.pdf",
            schema={"type": "object"},
            system_prompt="Be precise about dates.",
            ctx=mock_ctx,
        )
        call_kwargs = mock_client.extract.run.call_args.kwargs
        assert call_kwargs["instructions"]["system_prompt"] == "Be precise about dates."

    @pytest.mark.asyncio
    async def test_with_citations_and_array_extract(self, mock_ctx: MagicMock, mock_client: AsyncMock) -> None:
        await extract_data(
            document_url="https://example.com/doc.pdf",
            schema={"type": "object"},
            citations=True,
            array_extract=True,
            ctx=mock_ctx,
        )
        call_kwargs = mock_client.extract.run.call_args.kwargs
        assert call_kwargs["settings"]["citations"]["enabled"] is True
        assert call_kwargs["settings"]["array_extract"] is True

    @pytest.mark.asyncio
    async def test_with_page_range(self, mock_ctx: MagicMock, mock_client: AsyncMock) -> None:
        await extract_data(
            document_url="https://example.com/doc.pdf",
            schema={"type": "object"},
            page_range="1-3",
            ctx=mock_ctx,
        )
        call_kwargs = mock_client.extract.run.call_args.kwargs
        assert call_kwargs["parsing"]["settings"]["page_range"] == "1-3"

    @pytest.mark.asyncio
    async def test_schema_as_json_string(self, mock_ctx: MagicMock, mock_client: AsyncMock) -> None:
        result = await extract_data(
            document_url="https://example.com/doc.pdf",
            schema='{"type": "object", "properties": {"name": {"type": "string"}}}',
            ctx=mock_ctx,
        )
        assert result.isError is not True
        call_kwargs = mock_client.extract.run.call_args.kwargs
        assert call_kwargs["instructions"]["schema"]["type"] == "object"

    @pytest.mark.asyncio
    async def test_invalid_schema(self, mock_ctx: MagicMock) -> None:
        result = await extract_data(
            document_url="https://example.com/doc.pdf",
            schema="{bad json}",
            ctx=mock_ctx,
        )
        assert result.isError is True
        assert "Invalid JSON" in result.content[0].text

    @pytest.mark.asyncio
    async def test_invalid_url(self, mock_ctx: MagicMock) -> None:
        result = await extract_data(
            document_url="file:///etc/passwd",
            schema={"type": "object"},
            ctx=mock_ctx,
        )
        assert result.isError is True


# ─── Split ───────────────────────────────────────────────────────────


class TestSplitDocument:
    @pytest.mark.asyncio
    async def test_basic_split(self, mock_ctx: MagicMock, mock_client: AsyncMock) -> None:
        result = await split_document(
            document_url="https://example.com/doc.pdf",
            categories=[
                {"name": "Introduction", "description": "Opening section"},
                {"name": "Financials", "description": "Financial data"},
            ],
            ctx=mock_ctx,
        )
        assert result.isError is not True
        data = json.loads(result.content[0].text)
        assert len(data["splits"]) == 3

        call_kwargs = mock_client.split.run.call_args.kwargs
        assert call_kwargs["input"] == "https://example.com/doc.pdf"
        assert len(call_kwargs["split_description"]) == 2

    @pytest.mark.asyncio
    async def test_with_split_rules(self, mock_ctx: MagicMock, mock_client: AsyncMock) -> None:
        await split_document(
            document_url="https://example.com/doc.pdf",
            categories=[{"name": "A", "description": "Section A"}],
            split_rules="Split at major topic changes",
            ctx=mock_ctx,
        )
        call_kwargs = mock_client.split.run.call_args.kwargs
        assert call_kwargs["split_rules"] == "Split at major topic changes"

    @pytest.mark.asyncio
    async def test_categories_as_json_string(self, mock_ctx: MagicMock, mock_client: AsyncMock) -> None:
        result = await split_document(
            document_url="https://example.com/doc.pdf",
            categories='[{"name": "A", "description": "Section A"}]',
            ctx=mock_ctx,
        )
        assert result.isError is not True

    @pytest.mark.asyncio
    async def test_empty_categories(self, mock_ctx: MagicMock) -> None:
        result = await split_document(
            document_url="https://example.com/doc.pdf",
            categories=[],
            ctx=mock_ctx,
        )
        assert result.isError is True
        assert "must not be empty" in result.content[0].text


# ─── Classify ────────────────────────────────────────────────────────


class TestClassifyDocument:
    @pytest.mark.asyncio
    async def test_basic_classify(self, mock_ctx: MagicMock, mock_client: AsyncMock) -> None:
        result = await classify_document(
            document_url="https://example.com/doc.pdf",
            categories=[
                {"category": "invoice", "criteria": ["has billing info"]},
                {"category": "contract", "criteria": ["has legal terms"]},
            ],
            ctx=mock_ctx,
        )
        assert result.isError is not True
        data = json.loads(result.content[0].text)
        assert data["category"] == "invoice"
        assert len(data["category_confidences"]) == 3

        call_kwargs = mock_client.classify.run.call_args.kwargs
        assert call_kwargs["input"] == "https://example.com/doc.pdf"
        assert len(call_kwargs["classification_schema"]) == 2

    @pytest.mark.asyncio
    async def test_with_metadata(self, mock_ctx: MagicMock, mock_client: AsyncMock) -> None:
        await classify_document(
            document_url="https://example.com/doc.pdf",
            categories=[{"category": "invoice", "criteria": ["billing"]}],
            document_metadata="This document was received from a vendor.",
            ctx=mock_ctx,
        )
        call_kwargs = mock_client.classify.run.call_args.kwargs
        assert call_kwargs["document_metadata"] == "This document was received from a vendor."

    @pytest.mark.asyncio
    async def test_invalid_url(self, mock_ctx: MagicMock) -> None:
        result = await classify_document(
            document_url="ftp://bad.com/doc",
            categories=[{"category": "x", "criteria": ["y"]}],
            ctx=mock_ctx,
        )
        assert result.isError is True


# ─── Edit ────────────────────────────────────────────────────────────


class TestEditDocument:
    @pytest.mark.asyncio
    async def test_basic_edit(self, mock_ctx: MagicMock, mock_client: AsyncMock) -> None:
        result = await edit_document(
            document_url="https://example.com/form.pdf",
            edit_instructions="Fill in the name field with 'John Doe'",
            ctx=mock_ctx,
        )
        assert result.isError is not True
        data = json.loads(result.content[0].text)
        assert "document_url" in data

        call_kwargs = mock_client.edit.run.call_args.kwargs
        assert call_kwargs["document_url"] == "https://example.com/form.pdf"
        assert "John Doe" in call_kwargs["edit_instructions"]

    @pytest.mark.asyncio
    async def test_with_options(self, mock_ctx: MagicMock, mock_client: AsyncMock) -> None:
        await edit_document(
            document_url="https://example.com/form.pdf",
            edit_instructions="Fill name",
            options={"edit_options": {"color": "#FF0000"}, "priority": True},
            ctx=mock_ctx,
        )
        call_kwargs = mock_client.edit.run.call_args.kwargs
        assert call_kwargs["edit_options"] == {"color": "#FF0000"}
        assert call_kwargs["priority"] is True

    @pytest.mark.asyncio
    async def test_invalid_url(self, mock_ctx: MagicMock) -> None:
        result = await edit_document(
            document_url="ftp://bad.com",
            edit_instructions="test",
            ctx=mock_ctx,
        )
        assert result.isError is True


# ─── Upload ──────────────────────────────────────────────────────────


class TestUploadFile:
    @pytest.mark.asyncio
    async def test_basic_upload(self, mock_ctx: MagicMock, mock_client: AsyncMock) -> None:
        # Mock the httpx download that upload_file does internally
        mock_response = MagicMock()
        mock_response.content = b"%PDF-1.4 fake content"
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=False)

        with patch("mcp_server_reducto.tools.upload.httpx.AsyncClient", return_value=mock_http_client):
            result = await upload_file(
                file_url="https://example.com/doc.pdf",
                ctx=mock_ctx,
            )
        assert result.isError is not True
        data = json.loads(result.content[0].text)
        assert data["file_id"] == "reducto://abc123"

        mock_client.upload.assert_called_once()
        call_kwargs = mock_client.upload.call_args.kwargs
        assert call_kwargs["file"] == b"%PDF-1.4 fake content"
        assert call_kwargs["extension"] == ".pdf"

    @pytest.mark.asyncio
    async def test_invalid_url(self, mock_ctx: MagicMock) -> None:
        result = await upload_file(
            file_url="ftp://bad.com/doc",
            ctx=mock_ctx,
        )
        assert result.isError is True


# ─── Jobs ────────────────────────────────────────────────────────────


class TestGetJob:
    @pytest.mark.asyncio
    async def test_basic_get_job(self, mock_ctx: MagicMock, mock_client: AsyncMock) -> None:
        result = await get_job(
            job_id="job_parse_123",
            ctx=mock_ctx,
        )
        assert result.isError is not True
        data = json.loads(result.content[0].text)
        assert data["job_id"] == "job_parse_123"
        assert data["status"] == "Completed"

        mock_client.job.get.assert_called_once_with("job_parse_123")

    @pytest.mark.asyncio
    async def test_empty_job_id(self, mock_ctx: MagicMock) -> None:
        result = await get_job(job_id="", ctx=mock_ctx)
        assert result.isError is True
        assert "required" in result.content[0].text

    @pytest.mark.asyncio
    async def test_whitespace_job_id(self, mock_ctx: MagicMock) -> None:
        result = await get_job(job_id="   ", ctx=mock_ctx)
        assert result.isError is True


class TestListJobs:
    @pytest.mark.asyncio
    async def test_basic_list(self, mock_ctx: MagicMock, mock_client: AsyncMock) -> None:
        result = await list_jobs(ctx=mock_ctx)
        assert result.isError is not True

        mock_client.job.get_all.assert_called_once_with(limit=10)

    @pytest.mark.asyncio
    async def test_custom_limit(self, mock_ctx: MagicMock, mock_client: AsyncMock) -> None:
        await list_jobs(limit=5, ctx=mock_ctx)
        mock_client.job.get_all.assert_called_once_with(limit=5)

    @pytest.mark.asyncio
    async def test_sdk_error_handled(self, mock_ctx: MagicMock, mock_client: AsyncMock) -> None:
        import httpx
        from reducto import AuthenticationError

        mock_client.job.get_all.side_effect = AuthenticationError(
            message="Invalid key",
            response=httpx.Response(401, request=httpx.Request("GET", "https://api.reducto.ai/job")),
            body=None,
        )
        result = await list_jobs(ctx=mock_ctx)
        assert result.isError is True
        assert "Authentication" in result.content[0].text
