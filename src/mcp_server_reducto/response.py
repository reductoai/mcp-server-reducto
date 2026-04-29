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
        if _add_url_result_fields(result, resp_result):
            result["result_type"] = "url"
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

    job_id = result.get("job_id")
    if job_id:
        result["next_steps"] = (
            f"Use jobid://{job_id} as document_url for extract_data, split_document, or classify_document."
        )
    else:
        result["next_steps"] = "Use the parsed blocks directly, or run extract_data with a schema for JSON fields."

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
        resp_result = response.result
        if not _add_url_result_fields(result, resp_result):
            result["result"] = resp_result

    if "job_id" in result:
        result["next_steps"] = (
            "Read result for extracted fields; if fields are missing, refine the schema/system_prompt "
            "or parse first with agentic=['text']."
        )
    else:
        result["next_steps"] = "Read result for extracted fields; refine the schema if values are missing."

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
            result["section_count"] = len(splits)
            result["splits"] = splits

    if "job_id" in result:
        result["next_steps"] = f"Use get_job(job_id='{result['job_id']}') to retrieve or audit the full split result."
    else:
        result["next_steps"] = "Use the splits page ranges to route each section to parse_document or extract_data."

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

    if "job_id" in result:
        result["next_steps"] = f"Use the category result, or call get_job(job_id='{result['job_id']}') for details."
    else:
        result["next_steps"] = "Use the category result to choose the next parse or extract schema."

    return _truncate_response(result)


def format_edit_response(response: Any) -> str:
    """Format an EditResponse into a minimal string."""
    result: dict[str, Any] = {}

    if hasattr(response, "document_url"):
        result["document_url"] = response.document_url
    if hasattr(response, "form_schema") and response.form_schema:
        result["form_schema"] = response.form_schema
        result["form_schema_note"] = "Cache this form_schema and pass it via options.form_schema for repeated edits."

    if hasattr(response, "usage") and response.usage:
        usage = response.usage
        result["usage"] = {}
        if hasattr(usage, "num_pages"):
            result["usage"]["num_pages"] = usage.num_pages

    result["next_steps"] = "Download or pass document_url to another Reducto tool for follow-up processing."

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
    document_url = result.get("file_id") or result.get("url") if isinstance(result, dict) else None
    if isinstance(result, dict):
        if document_url:
            result["next_steps"] = f"Pass {document_url} as document_url to parse_document or extract_data."
        else:
            result["next_steps"] = "Pass the returned reducto:// URL as document_url to parse_document or extract_data."
    return _truncate_response(result)


def format_job_response(response: Any) -> str:
    """Format a job retrieval response."""
    data = _safe_model_dump(response)
    if isinstance(data, dict):
        _add_nested_url_result_warning(data)
        raw_status = data.get("status")
        status = str(raw_status).lower() if raw_status else ""
        if status and status not in {"completed", "complete", "succeeded", "success"}:
            data["next_steps"] = "Job is not complete yet; call get_job again later before reading final results."
        else:
            data["next_steps"] = (
                "Use this result directly, or pass jobid://<job_id> as document_url for another Reducto tool."
            )
    return _truncate_response(data)


def format_job_list_response(response: Any) -> str:
    """Format a job list response."""
    data = _safe_model_dump(response)
    if isinstance(data, dict):
        data["next_steps"] = "Call get_job with a returned job_id to inspect status, results, or URL-backed output."
    return _truncate_response(data)


def _safe_model_dump(obj: Any) -> Any:
    """Safely convert a Pydantic model or arbitrary object to a dict."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if isinstance(obj, (dict, list, str, int, float, bool, type(None))):
        return obj
    return str(obj)


def _url_from_result(obj: Any) -> str | None:
    """Return the result URL if obj looks like a Reducto UrlResult."""
    if hasattr(obj, "type") and obj.type == "url" and getattr(obj, "url", None):
        return str(obj.url)
    if isinstance(obj, dict) and obj.get("type") == "url" and obj.get("url"):
        return str(obj["url"])
    return None


def _add_url_result_fields(result: dict[str, Any], resp_result: Any) -> bool:
    """Add consistent fields for URL-backed results."""
    url = _url_from_result(resp_result)
    if not url:
        return False
    result["result_type"] = "url"
    result["result_url"] = url
    if "job_id" in result:
        result["result_access_warning"] = (
            f"Result content is URL-backed; call get_job(job_id='{result['job_id']}') before reading it."
        )
    else:
        result["result_access_warning"] = "Result content is URL-backed; fetch the job result before reading it."
    return True


def _add_nested_url_result_warning(data: dict[str, Any]) -> None:
    """Surface URL-backed job results after model_dump conversion."""
    result_obj = data.get("result")
    url = _url_from_result(result_obj)
    if not url:
        return
    data["result_type"] = "url"
    data["result_url"] = url
    job_id = data.get("job_id")
    if job_id:
        data["result_access_warning"] = (
            f"Result content is URL-backed; call get_job(job_id='{job_id}') before reading it."
        )
    else:
        data["result_access_warning"] = "Result content is URL-backed; fetch the job result before reading it."


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
