"""Job management tools — get_job, list_jobs, cancel_job."""

from __future__ import annotations

from mcp.server.fastmcp import Context
from mcp.types import CallToolResult, TextContent

from mcp_server_reducto.errors import handle_sdk_error
from mcp_server_reducto.response import format_job_list_response, format_job_response
from mcp_server_reducto.server import mcp
from mcp_server_reducto.tools.helpers import get_client


@mcp.tool(
    name="get_job",
    description=(
        "Get the status and result of a processing job by job_id. "
        "Use this to retrieve full results when a previous tool response was truncated, "
        "or to check the status of an async job."
    ),
)
async def get_job(
    job_id: str,
    ctx: Context = None,  # type: ignore[assignment]
) -> CallToolResult:
    """Retrieve the status and result of a processing job."""
    if not job_id or not job_id.strip():
        return CallToolResult(
            content=[TextContent(type="text", text="Error: job_id is required.\n\nWhat to do: Provide a valid job_id.")],
            isError=True,
        )

    try:
        client = get_client(ctx)
        response = await client.job.get(job_id)
        text = format_job_response(response)
        return CallToolResult(content=[TextContent(type="text", text=text)])

    except Exception as e:
        return handle_sdk_error(e)


@mcp.tool(
    name="list_jobs",
    description="List recent processing jobs. Returns job IDs, statuses, and creation times.",
)
async def list_jobs(
    limit: int = 10,
    ctx: Context = None,  # type: ignore[assignment]
) -> CallToolResult:
    """List recent processing jobs."""
    try:
        client = get_client(ctx)
        response = await client.job.get_all(limit=limit)
        text = format_job_list_response(response)
        return CallToolResult(content=[TextContent(type="text", text=text)])

    except Exception as e:
        return handle_sdk_error(e)
