"""Reducto MCP server entrypoint.

Creates a FastMCP instance with lifespan-managed Reducto client,
registers all tools, and provides transport selection.
"""

from __future__ import annotations

import logging
import os
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP

from mcp_server_reducto.config import get_api_key

# Server-side logging to stderr (stdout is the MCP transport for stdio mode)
logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("mcp-server-reducto")


@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[dict]:
    """Initialize the Reducto client for local (single-tenant) mode.

    In hosted mode (mcp.reducto.ai), there's no server-wide API key —
    each request brings its own key via Authorization header. The lifespan
    gracefully skips client creation in that case.
    """
    hosted_mode = os.environ.get("REDUCTO_MCP_HOSTED") == "1"

    if hosted_mode:
        logger.info("Reducto MCP server initialized (hosted mode — per-request auth)")
        yield {}
        logger.info("Reducto MCP server shutting down")
        return

    from mcp_server_reducto.tools.helpers import _make_client

    api_key = get_api_key()
    client = _make_client(api_key)
    logger.info("Reducto MCP server initialized")
    yield {"reducto_client": client}
    logger.info("Reducto MCP server shutting down")


INSTRUCTIONS = """\
Use these tools for all Reducto operations -- they handle auth, uploads, and response parsing.
Reducto processes documents (PDFs, images, spreadsheets, DOCX, PPTX, and 30+ formats) into structured data.

## Which tool to use

| Need | Tool |
|------|------|
| Upload a local file or public URL before processing | upload_file |
| Get all text, tables, and figures from a document | parse_document |
| Extract specific fields into JSON with a schema | extract_data |
| Divide a document into named page sections | split_document |
| Categorize a document into provided types | classify_document |
| Fill forms or modify a PDF/DOCX | edit_document |
| Fetch a full, URL-backed, truncated, or async result | get_job |
| Inspect recent jobs | list_jobs |

## Key patterns

- Prefer MCP tools over hand-written HTTP or direct SDK calls while solving tasks in this session.
- **Chain operations with jobid:// URLs**: parse_document returns a job_id. \
Pass "jobid://<job_id>" as document_url to extract_data, split_document, \
or classify_document to reuse prior work and avoid re-uploading or re-parsing.
- **Responses may be truncated**: Large results are auto-truncated at 50KB. \
Use get_job(job_id=...) to retrieve full results, or narrow with page_range.
- **All tools return job_id**: Every processing tool returns a job_id you can \
reference later.

## Common gotchas

- **Node SDK uploads from bytes require toFile()**: when writing Node integrations, \
wrap in-memory bytes with toFile(bytes, filename) from the Reducto SDK before \
client.upload({ file }). Passing raw bytes can return a file_id without actually \
storing the file.
- extract_data runs parse internally — if the parser doesn't see a value \
(e.g., handwritten text without agentic mode), extract can't find it either. \
Use agentic=["text"] in parse_document for difficult documents.
- Large documents may return result_type="url" instead of inline content. \
Use get_job to fetch the full result.
- Build extraction schemas as standard JSON Schema objects: \
{"type":"object","properties":{...},"required":[...]}. Use array_extract=True \
for repeating rows or line items.
- page_range uses 1-based indexing: "1-5" means pages 1 through 5.

## Related tools

- For batch processing of local files: Reducto CLI (`pip install reducto-cli`)
- For spreadsheet-like extraction workflows: Reducto Workflows (workflows.reducto.ai)
- For direct API access: Python SDK (`pip install reductoai`)
"""

_hosted = os.environ.get("REDUCTO_MCP_HOSTED") == "1"

# In hosted mode, disable DNS rebinding protection (we do our own auth)
# and allow the mcp.reducto.ai host header
_transport_security = None
if _hosted:
    from mcp.server.transport_security import TransportSecuritySettings

    _transport_security = TransportSecuritySettings(enable_dns_rebinding_protection=False)

mcp = FastMCP(
    name="Reducto",
    instructions=INSTRUCTIONS,
    lifespan=lifespan,
    transport_security=_transport_security,
)

# Register all tools by importing the modules (they use @mcp.tool())
from mcp_server_reducto.tools import classify, edit, extract, jobs, parse, split, upload  # noqa: E402, F401


def create_server(*, client=None) -> FastMCP:
    """Create a server instance, optionally with a pre-configured client (for testing)."""
    if client is not None:
        # For testing: inject a mock client into the server's context
        mcp._test_client = client  # type: ignore[attr-defined]
    return mcp


def _run_login(force: bool = False) -> None:
    """Run the device auth login flow (blocking)."""
    import asyncio

    from mcp_server_reducto.auth import AuthError, device_auth_login

    try:
        asyncio.run(device_auth_login(force=force))
    except AuthError as e:
        logger.error("Login failed: %s", e)
        sys.exit(1)


def main() -> None:
    """CLI entrypoint: run the MCP server with configured transport.

    Supports --login / --login --force to authenticate before starting,
    or as a standalone command to save credentials for later use.
    """
    import argparse

    from mcp_server_reducto.config import get_port, get_transport

    parser = argparse.ArgumentParser(
        prog="mcp-server-reducto",
        description="MCP server for the Reducto document processing API",
    )
    parser.add_argument(
        "--login",
        action="store_true",
        help="Authenticate via browser (device code flow). Saves API key to ~/.reducto/config.yaml.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="With --login, replace an existing saved API key.",
    )
    args = parser.parse_args()

    if args.login:
        _run_login(force=args.force)
        return

    transport = get_transport()
    if transport == "http":
        port = get_port()
        logger.info("Starting Reducto MCP server on HTTP port %d", port)
        mcp.settings.port = port
        mcp.run(transport="streamable-http")
    else:
        logger.info("Starting Reducto MCP server on stdio")
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
