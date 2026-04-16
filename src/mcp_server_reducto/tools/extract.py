"""extract_data tool — extract structured data from a document using a JSON schema."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import Context
from mcp.types import CallToolResult, TextContent

from mcp_server_reducto.errors import handle_sdk_error
from mcp_server_reducto.response import format_extract_response
from mcp_server_reducto.server import mcp
from mcp_server_reducto.tools.helpers import get_client
from mcp_server_reducto.validation import (
    ValidationError,
    parse_options_dict,
    validate_document_url,
    validate_schema,
)


@mcp.tool(
    name="extract_data",
    description=(
        "Extract structured data from a document using a JSON schema. "
        "Example: extract_data(document_url='https://example.com/invoice.pdf', "
        "schema={'type':'object','properties':{'total':{'type':'number'},'vendor':{'type':'string'}}}). "
        "Use array_extract=True for repeating items (line items, rows). "
        "Use citations=True to get source references for each extracted value. "
        "Use deep_extract=True for iterative agentic refinement on complex docs. "
        "Tip: pass jobid:// URLs from previous parse results to skip re-parsing and save time."
    ),
)
async def extract_data(
    document_url: str,
    schema: dict[str, Any] | str,
    system_prompt: str | None = None,
    citations: bool | None = None,
    array_extract: bool | None = None,
    deep_extract: bool | None = None,
    include_images: bool | None = None,
    page_range: str | None = None,
    options: dict[str, Any] | str | None = None,
    ctx: Context = None,  # type: ignore[assignment]
) -> CallToolResult:
    """Extract structured data from a document based on a provided JSON schema."""
    try:
        validate_document_url(document_url)
        schema = validate_schema(schema)
        opts = parse_options_dict(options)
    except ValidationError as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Validation error: {e}\n\nWhat to do: {e.guidance}")],
            isError=True,
        )

    try:
        client = get_client(ctx)

        kwargs: dict[str, Any] = {"input": document_url}

        # Build instructions
        instructions: dict[str, Any] = {"schema": schema}
        if system_prompt is not None:
            instructions["system_prompt"] = system_prompt
        kwargs["instructions"] = instructions

        # Build settings
        settings: dict[str, Any] = {}
        if citations is not None:
            settings["citations"] = {"enabled": citations}
        if array_extract is not None:
            settings["array_extract"] = array_extract
        if deep_extract is not None:
            settings["deep_extract"] = deep_extract
        if include_images is not None:
            settings["include_images"] = include_images
        if settings:
            kwargs["settings"] = settings

        # Build parsing config for page_range
        if page_range is not None:
            kwargs["parsing"] = {"settings": {"page_range": page_range}}

        # Merge options escape hatch
        if opts:
            for key, value in opts.items():
                if key not in kwargs:
                    kwargs[key] = value
                elif isinstance(kwargs[key], dict) and isinstance(value, dict):
                    merged = {**value, **kwargs[key]}
                    kwargs[key] = merged

        response = await client.extract.run(**kwargs)
        text = format_extract_response(response)
        return CallToolResult(content=[TextContent(type="text", text=text)])

    except Exception as e:
        return handle_sdk_error(e)
