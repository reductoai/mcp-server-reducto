"""upload_file tool — upload a document to Reducto's temporary storage."""

from __future__ import annotations

import httpx
from mcp.server.fastmcp import Context
from mcp.types import CallToolResult, TextContent

from mcp_server_reducto.errors import handle_sdk_error
from mcp_server_reducto.response import format_upload_response
from mcp_server_reducto.server import mcp
from mcp_server_reducto.tools.helpers import get_client
from mcp_server_reducto.validation import ValidationError, validate_document_url


@mcp.tool(
    name="upload_file",
    description=(
        "Upload a file to Reducto's temporary storage (24-hour TTL). "
        "Returns a reducto:// URL that can be used as document_url in other tools. "
        "Use this when you need to process a document multiple times."
    ),
)
async def upload_file(
    file_url: str,
    ctx: Context = None,  # type: ignore[assignment]
) -> CallToolResult:
    """Upload a file to Reducto temporary storage and get a reducto:// URL."""
    try:
        validate_document_url(file_url)
    except ValidationError as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Validation error: {e}\n\nWhat to do: {e.guidance}")],
            isError=True,
        )

    try:
        # Download the file first — the SDK expects bytes, not a URL
        async with httpx.AsyncClient() as http_client:
            download = await http_client.get(file_url, follow_redirects=True, timeout=60.0)
            download.raise_for_status()
            file_bytes = download.content

        # Determine extension from URL
        extension = None
        path = file_url.rsplit("?", 1)[0]  # strip query params
        if "." in path.rsplit("/", 1)[-1]:
            extension = "." + path.rsplit(".", 1)[-1].lower()

        client = get_client(ctx)
        response = await client.upload(file=file_bytes, extension=extension)
        text = format_upload_response(response)
        return CallToolResult(content=[TextContent(type="text", text=text)])

    except httpx.HTTPError as e:
        from mcp_server_reducto.errors import mcp_error
        return mcp_error(
            f"Failed to download file from {file_url}: {e}",
            guidance="Check that the URL is accessible and returns a valid file.",
        )
    except Exception as e:
        return handle_sdk_error(e)
