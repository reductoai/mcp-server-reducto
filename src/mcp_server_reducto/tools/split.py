"""split_document tool — segment a document into labeled sections by topic."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import Context
from mcp.types import CallToolResult, TextContent

from mcp_server_reducto.errors import handle_sdk_error
from mcp_server_reducto.response import format_split_response
from mcp_server_reducto.server import mcp
from mcp_server_reducto.tools.helpers import get_client
from mcp_server_reducto.validation import (
    ValidationError,
    parse_options_dict,
    validate_categories,
    validate_document_url,
)


@mcp.tool(
    name="split_document",
    description=(
        "Segment a document into labeled sections by topic. "
        "Example: split_document(document_url='https://example.com/contract.pdf', "
        "categories=[{'name':'Terms','description':'Terms and conditions'},"
        "{'name':'Pricing','description':'Pricing tables'}]). "
        "Returns page ranges per category with confidence scores. "
        "Use split_rules for custom splitting guidance (e.g. 'Split at each new section heading'). "
        "Tip: pass jobid:// URLs from previous parse results to skip re-parsing."
    ),
)
async def split_document(
    document_url: str,
    categories: list[dict[str, Any]] | str,
    split_rules: str | None = None,
    page_range: str | None = None,
    options: dict[str, Any] | str | None = None,
    ctx: Context = None,  # type: ignore[assignment]
) -> CallToolResult:
    """Split a document into labeled sections based on provided categories."""
    try:
        validate_document_url(document_url)
        categories = validate_categories(categories)
        opts = parse_options_dict(options)
    except ValidationError as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Validation error: {e}\n\nWhat to do: {e.guidance}")],
            isError=True,
        )

    try:
        client = get_client(ctx)

        kwargs: dict[str, Any] = {
            "input": document_url,
            "split_description": categories,
        }

        if split_rules is not None:
            kwargs["split_rules"] = split_rules

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

        response = await client.split.run(**kwargs)
        text = format_split_response(response)
        return CallToolResult(content=[TextContent(type="text", text=text)])

    except Exception as e:
        return handle_sdk_error(e)
