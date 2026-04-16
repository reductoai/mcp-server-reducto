"""Response formatting and truncation for MCP tool outputs.

Inspired by GitHub MCP's minimal type conversion pattern — strip unused fields
to reduce LLM context consumption by 60-80%.
"""

from __future__ import annotations

import json
from typing import Any

from mcp_server_reducto.config import get_max_response_size


def _simplify_block(block: Any) -> dict[str, Any]:
    """Convert a ParseBlock to a minimal dict with only LLM-useful fields."""
    result: dict[str, Any] = {}
    if hasattr(block, "type"):
        result["type"] = str(block.type)
    if hasattr(block, "content"):
        result["content"] = block.content
    return result


def format_parse_response(response: Any) -> str:
    """Format a ParseResponse into a minimal, LLM-friendly string."""
    result: dict[str, Any] = {}

    if hasattr(response, "job_id"):
        result["job_id"] = response.job_id
    if hasattr(response, "duration"):
        result["duration_seconds"] = response.duration
    if hasattr(response, "studio_link") and response.studio_link:
        result["studio_link"] = response.studio_link

    # Usage summary
    if hasattr(response, "usage") and response.usage:
        usage = response.usage
        result["usage"] = {}
        if hasattr(usage, "num_pages"):
            result["usage"]["num_pages"] = usage.num_pages
        if hasattr(usage, "credits"):
            result["usage"]["credits"] = usage.credits

    # Process result blocks
    if hasattr(response, "result") and response.result:
        resp_result = response.result
        # Handle FullResult vs UrlResult
        if hasattr(resp_result, "type") and resp_result.type == "url":
            result["result_type"] = "url"
            result["result_url"] = resp_result.url
        elif hasattr(resp_result, "chunks"):
            blocks = []
            for chunk in resp_result.chunks:
                if hasattr(chunk, "blocks"):
                    for block in chunk.blocks:
                        blocks.append(_simplify_block(block))
            result["num_blocks"] = len(blocks)

            # Count block types
            type_counts: dict[str, int] = {}
            for b in blocks:
                t = b.get("type", "unknown")
                type_counts[t] = type_counts.get(t, 0) + 1
            result["block_type_counts"] = type_counts
            result["blocks"] = blocks

    return _truncate_response(result)


def format_extract_response(response: Any) -> str:
    """Format an ExtractResponse into a minimal string."""
    result: dict[str, Any] = {}

    if hasattr(response, "job_id"):
        result["job_id"] = response.job_id
    if hasattr(response, "studio_link") and response.studio_link:
        result["studio_link"] = response.studio_link

    if hasattr(response, "usage") and response.usage:
        usage = response.usage
        result["usage"] = {}
        if hasattr(usage, "num_pages"):
            result["usage"]["num_pages"] = usage.num_pages
        if hasattr(usage, "num_fields"):
            result["usage"]["num_fields"] = usage.num_fields
        if hasattr(usage, "credits"):
            result["usage"]["credits"] = usage.credits

    if hasattr(response, "result"):
        result["result"] = response.result

    return _truncate_response(result)


def format_split_response(response: Any) -> str:
    """Format a SplitResponse into a minimal string."""
    result: dict[str, Any] = {}

    if hasattr(response, "job_id"):
        result["job_id"] = response.job_id

    if hasattr(response, "usage") and response.usage:
        usage = response.usage
        result["usage"] = {}
        if hasattr(usage, "num_pages"):
            result["usage"]["num_pages"] = usage.num_pages
        if hasattr(usage, "credits"):
            result["usage"]["credits"] = usage.credits

    if hasattr(response, "result") and response.result:
        resp_result = response.result
        if hasattr(resp_result, "splits"):
            splits = []
            for s in resp_result.splits:
                split_data: dict[str, Any] = {}
                if hasattr(s, "name"):
                    split_data["name"] = s.name
                if hasattr(s, "pages"):
                    split_data["pages"] = s.pages
                if hasattr(s, "conf"):
                    split_data["confidence"] = s.conf
                splits.append(split_data)
            result["splits"] = splits

    return _truncate_response(result)


def format_classify_response(response: Any) -> str:
    """Format a ClassifyResponse into a minimal string."""
    result: dict[str, Any] = {}

    if hasattr(response, "job_id"):
        result["job_id"] = response.job_id
    if hasattr(response, "duration"):
        result["duration_seconds"] = response.duration

    if hasattr(response, "result") and response.result and hasattr(response.result, "category"):
        result["category"] = response.result.category

    if hasattr(response, "response_confidence") and response.response_confidence:
        conf = response.response_confidence
        if hasattr(conf, "categories"):
            result["category_confidences"] = [
                {"category": c.category, "confidence": c.confidence} for c in conf.categories
            ]

    return _truncate_response(result)


def format_edit_response(response: Any) -> str:
    """Format an EditResponse into a minimal string."""
    result: dict[str, Any] = {}

    if hasattr(response, "document_url"):
        result["document_url"] = response.document_url

    if hasattr(response, "usage") and response.usage:
        usage = response.usage
        result["usage"] = {}
        if hasattr(usage, "num_pages"):
            result["usage"]["num_pages"] = usage.num_pages

    return _truncate_response(result)


def format_upload_response(response: Any) -> str:
    """Format an UploadResponse."""
    result: dict[str, Any] = {}
    if hasattr(response, "file_id"):
        result["file_id"] = response.file_id
    if hasattr(response, "url"):
        result["url"] = response.url
    # The upload response model_dump is small, just serialize it
    if not result:
        result = _safe_model_dump(response)
    return _truncate_response(result)


def format_job_response(response: Any) -> str:
    """Format a job retrieval response."""
    data = _safe_model_dump(response)
    return _truncate_response(data)


def format_job_list_response(response: Any) -> str:
    """Format a job list response."""
    data = _safe_model_dump(response)
    return _truncate_response(data)


def _safe_model_dump(obj: Any) -> Any:
    """Safely convert a Pydantic model or arbitrary object to a dict."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if isinstance(obj, (dict, list, str, int, float, bool, type(None))):
        return obj
    return str(obj)


def _truncate_response(data: Any) -> str:
    """Serialize to JSON and truncate if over the configured limit."""
    max_size = get_max_response_size()
    text = json.dumps(data, indent=2, default=str)

    if len(text) <= max_size:
        return text

    # Find the job_id for guidance
    job_id = data.get("job_id", "unknown") if isinstance(data, dict) else "unknown"

    # Truncate blocks if present
    if isinstance(data, dict) and "blocks" in data:
        blocks = data["blocks"]
        total_blocks = len(blocks)
        # Binary search for how many blocks fit
        lo, hi = 0, total_blocks
        while lo < hi:
            mid = (lo + hi + 1) // 2
            data["blocks"] = blocks[:mid]
            data["truncated"] = True
            trial = json.dumps(data, indent=2, default=str)
            if len(trial) <= max_size:
                lo = mid
            else:
                hi = mid - 1
        data["blocks"] = blocks[:lo]
        data["truncated"] = True
        data["truncation_note"] = (
            f"Response truncated (showing {lo} of {total_blocks} blocks). "
            f"Use get_job(job_id='{job_id}') for full results, "
            f"or narrow with page_range."
        )
        return json.dumps(data, indent=2, default=str)

    # Generic truncation for non-block responses
    truncated = text[:max_size]
    return (
        truncated
        + f"\n\n[TRUNCATED — response exceeded {max_size} chars. "
        + f"Use get_job(job_id='{job_id}') for full results.]"
    )
