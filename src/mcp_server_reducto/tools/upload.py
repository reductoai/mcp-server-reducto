"""upload_file tool — upload a document to Reducto's temporary storage."""

from __future__ import annotations

import os
from pathlib import Path

import httpx
from mcp.server.fastmcp import Context
from mcp.types import CallToolResult, TextContent

from mcp_server_reducto.errors import handle_sdk_error, mcp_error
from mcp_server_reducto.response import format_upload_response
from mcp_server_reducto.server import mcp
from mcp_server_reducto.tools.helpers import get_client


def _is_local_path(value: str) -> bool:
    """Check if the value looks like a local file path (not a URL)."""
    if value.startswith(("http://", "https://", "reducto://", "jobid://")):
        return False
    # Absolute paths, relative paths, home-dir paths
    return value.startswith(("/", "./", "../", "~")) or os.path.exists(value)


def _resolve_path(value: str) -> Path:
    """Resolve a file path, expanding ~ and making absolute."""
    return Path(value).expanduser().resolve()


@mcp.tool(
    name="upload_file",
    description=(
        "Upload a file to Reducto's temporary storage (24-hour TTL). "
        "Returns a reducto:// URL that can be used as document_url in other tools. "
        "Accepts a local file path (e.g. './report.pdf', '/tmp/doc.pdf', '~/Documents/file.pdf') "
        "or a public URL (e.g. 'https://example.com/report.pdf'). "
        "Use this to process local files: upload first, then pass the reducto:// URL to parse_document or extract_data."
    ),
)
async def upload_file(
    file_url: str,
    ctx: Context = None,  # type: ignore[assignment]
) -> CallToolResult:
    """Upload a file to Reducto temporary storage and get a reducto:// URL."""
    is_hosted = os.environ.get("REDUCTO_MCP_HOSTED") == "1"

    try:
        client = get_client(ctx)

        if _is_local_path(file_url):
            if is_hosted:
                return mcp_error(
                    "Local file paths are not supported on the hosted server (mcp.reducto.ai).",
                    guidance=(
                        "Upload the file directly to Reducto using curl, then pass the reducto:// URL:\n"
                        "  curl -X POST https://platform.reducto.ai/upload "
                        "-H 'Authorization: Bearer <your-api-key>' "
                        "-F 'file=@/path/to/file.pdf'\n"
                        "Then use the returned file_id as document_url in other tools."
                    ),
                )

            # Local file path — read from disk
            path = _resolve_path(file_url)
            if not path.exists():
                return mcp_error(
                    f"File not found: {path}",
                    guidance="Check the file path and try again.",
                )
            if not path.is_file():
                return mcp_error(
                    f"Not a file: {path}",
                    guidance="Provide a path to a file, not a directory.",
                )

            file_bytes = path.read_bytes()
            extension = path.suffix or None
            response = await client.upload(file=file_bytes, extension=extension)

        else:
            # URL — download then upload
            if not file_url.startswith(("http://", "https://")):
                return mcp_error(
                    f"Invalid input: '{file_url}'. Expected a local file path or http(s) URL.",
                    guidance="Provide a local file path (e.g. './doc.pdf') or a URL (e.g. 'https://example.com/doc.pdf').",
                )

            async with httpx.AsyncClient() as http_client:
                download = await http_client.get(file_url, follow_redirects=True, timeout=60.0)
                download.raise_for_status()
                file_bytes = download.content

            # Determine extension from URL
            extension = None
            url_path = file_url.rsplit("?", 1)[0]
            if "." in url_path.rsplit("/", 1)[-1]:
                extension = "." + url_path.rsplit(".", 1)[-1].lower()

            response = await client.upload(file=file_bytes, extension=extension)

        text = format_upload_response(response)
        return CallToolResult(content=[TextContent(type="text", text=text)])

    except httpx.HTTPError as e:
        return mcp_error(
            f"Failed to download file from {file_url}: {e}",
            guidance="Check that the URL is accessible and returns a valid file.",
        )
    except Exception as e:
        return handle_sdk_error(e)
