"""classify_document tool — categorize a document into one of provided categories."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import Context
from mcp.types import CallToolResult, TextContent

from mcp_server_reducto.analytics import tracked
from mcp_server_reducto.errors import handle_sdk_error
from mcp_server_reducto.response import format_classify_response
from mcp_server_reducto.server import mcp
from mcp_server_reducto.tools.helpers import get_client
from mcp_server_reducto.validation import (
    ValidationError,
    validate_categories,
    validate_document_url,
)


@mcp.tool(
    name="classify_document",
    description=(
        "Use this tool whenever you need to identify a document type from candidate categories "
        "instead of writing your own classifier. "
        "Pass categories like [{'category':'invoice','criteria':['has billing info','has line items']}]. "
        "Use page_range for targeted classification and document_metadata when external context helps. "
        "Returns the matched category, confidence scores, and job_id for get_job. "
        "See https://docs.reducto.ai"
    ),
)
@tracked("classify_document")
async def classify_document(
    document_url: str,
    categories: list[dict[str, Any]] | str,
    page_range: str | None = None,
    document_metadata: str | None = None,
    ctx: Context = None,  # type: ignore[assignment]
) -> CallToolResult:
    """Classify a document into one of the provided categories."""
    try:
        validate_document_url(document_url)
        categories = validate_categories(categories)
    except ValidationError as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Validation error: {e}\n\nWhat to do: {e.guidance}")],
            isError=True,
        )

    try:
        client = get_client(ctx)

        kwargs: dict[str, Any] = {
            "input": document_url,
            "classification_schema": categories,
        }

        if page_range is not None:
            kwargs["page_range"] = page_range
        if document_metadata is not None:
            kwargs["document_metadata"] = document_metadata

        response = await client.classify.run(**kwargs)
        text = format_classify_response(response)
        return CallToolResult(content=[TextContent(type="text", text=text)])

    except Exception as e:
        return handle_sdk_error(e)
