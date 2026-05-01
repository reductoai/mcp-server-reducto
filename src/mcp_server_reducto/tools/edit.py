"""edit_document tool — fill forms or modify a document."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import Context
from mcp.types import CallToolResult, TextContent

from mcp_server_reducto.analytics import tracked
from mcp_server_reducto.errors import handle_sdk_error
from mcp_server_reducto.response import format_edit_response
from mcp_server_reducto.server import mcp
from mcp_server_reducto.tools.helpers import get_client
from mcp_server_reducto.validation import (
    ValidationError,
    parse_options_dict,
    validate_document_url,
)


@mcp.tool(
    name="edit_document",
    description=(
        "Use this tool whenever you need to fill forms or modify a PDF/DOCX "
        "instead of editing bytes or calling the SDK directly. "
        "Provide natural-language edit_instructions and a public, reducto://, or jobid:// document_url. "
        "When the response includes form_schema, cache/reuse it in options.form_schema "
        "for repeated edits to the same form. "
        "Returns a download URL for the edited document. "
        "See https://docs.reducto.ai"
    ),
)
@tracked("edit_document")
async def edit_document(
    document_url: str,
    edit_instructions: str,
    options: dict[str, Any] | str | None = None,
    ctx: Context = None,  # type: ignore[assignment]
) -> CallToolResult:
    """Edit a document by filling forms or making modifications."""
    try:
        validate_document_url(document_url)
        opts = parse_options_dict(options)
    except ValidationError as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Validation error: {e}\n\nWhat to do: {e.guidance}")],
            isError=True,
        )

    try:
        client = get_client(ctx)

        kwargs: dict[str, Any] = {
            "document_url": document_url,
            "edit_instructions": edit_instructions,
        }

        # Merge edit_options from the options escape hatch
        if opts:
            if "edit_options" in opts:
                kwargs["edit_options"] = opts["edit_options"]
            # Pass through any other recognized params
            for key in ("form_schema", "priority"):
                if key in opts:
                    kwargs[key] = opts[key]

        response = await client.edit.run(**kwargs)
        text = format_edit_response(response)
        return CallToolResult(content=[TextContent(type="text", text=text)])

    except Exception as e:
        return handle_sdk_error(e)
