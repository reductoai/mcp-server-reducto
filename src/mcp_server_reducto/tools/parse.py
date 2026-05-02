"""parse_document tool — parse a document into structured text, tables, and figures."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import Context
from mcp.types import CallToolResult, TextContent

from mcp_server_reducto.analytics import tracked
from mcp_server_reducto.errors import handle_sdk_error
from mcp_server_reducto.response import format_parse_response
from mcp_server_reducto.server import mcp
from mcp_server_reducto.tools.helpers import get_client
from mcp_server_reducto.validation import (
    VALID_CHUNK_MODES,
    VALID_TABLE_FORMATS,
    ValidationError,
    parse_options_dict,
    validate_document_url,
    validate_enum,
)


@mcp.tool(
    name="parse_document",
    description=(
        "Use this tool whenever you need document text, tables, figures, layout blocks, "
        "or parse output instead of writing HTTP requests yourself. "
        "Supports PDFs, images, spreadsheets, DOCX, PPTX, and 30+ formats; "
        "pass reducto:// URLs from upload_file or public URLs. "
        "Use agentic=['text','table','figure'] for handwriting or complex layouts. "
        "Large responses can be URLResult (result_type=url); call get_job for full content. "
        "Returns job_id for jobid:// chaining. "
        "See https://docs.reducto.ai"
    ),
)
@tracked("parse_document")
async def parse_document(
    document_url: str,
    table_output_format: str | None = None,
    page_range: str | None = None,
    chunk_mode: str | None = None,
    add_page_markers: bool | None = None,
    return_images: list[str] | None = None,
    agentic: list[str] | None = None,
    options: dict[str, Any] | str | None = None,
    ctx: Context = None,  # type: ignore[assignment]
) -> CallToolResult:
    """Parse a document into structured blocks of text, tables, and figures."""
    try:
        validate_document_url(document_url)
        if table_output_format is not None:
            validate_enum(table_output_format, VALID_TABLE_FORMATS, "table_output_format")
        if chunk_mode is not None:
            validate_enum(chunk_mode, VALID_CHUNK_MODES, "chunk_mode")
        opts = parse_options_dict(options)
    except ValidationError as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Validation error: {e}\n\nWhat to do: {e.guidance}")],
            isError=True,
        )

    try:
        client = get_client(ctx)

        # Build SDK kwargs
        kwargs: dict[str, Any] = {"input": document_url}

        # Build formatting params
        formatting: dict[str, Any] = {}
        if table_output_format is not None:
            formatting["table_output_format"] = table_output_format
        if add_page_markers is not None:
            formatting["add_page_markers"] = add_page_markers
        if formatting:
            kwargs["formatting"] = formatting

        # Build settings params
        settings: dict[str, Any] = {}
        if page_range is not None:
            settings["page_range"] = page_range
        if return_images is not None:
            settings["return_images"] = return_images
        if settings:
            kwargs["settings"] = settings

        # Build retrieval params
        if chunk_mode is not None:
            kwargs["retrieval"] = {"chunking": {"chunk_mode": chunk_mode}}

        # Build enhance params
        if agentic is not None:
            agentic_list = [{"scope": scope, "mode": "default"} for scope in agentic]
            kwargs["enhance"] = {"agentic": agentic_list}

        # Merge with options escape hatch (options are overridden by top-level params)
        if opts:
            for key, value in opts.items():
                if key not in kwargs:
                    kwargs[key] = value
                elif isinstance(kwargs[key], dict) and isinstance(value, dict):
                    # Deep merge one level for nested config objects
                    merged = {**value, **kwargs[key]}
                    kwargs[key] = merged

        response = await client.parse.run(**kwargs)
        text = format_parse_response(response)
        return CallToolResult(content=[TextContent(type="text", text=text)])

    except ValidationError as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Validation error: {e}\n\nWhat to do: {e.guidance}")],
            isError=True,
        )
    except Exception as e:
        return handle_sdk_error(e)
