"""Input validation for MCP tool parameters.

Validates inputs client-side for fast, clear error feedback before
making API calls. Inspired by Sentry's constraint injection and
Notion's string fallback wrapping.
"""

from __future__ import annotations

import json
from typing import Any

ALLOWED_URL_SCHEMES = ("http://", "https://", "reducto://", "jobid://")

VALID_TABLE_FORMATS = ("html", "json", "md", "csv", "dynamic", "jsonbbox")
VALID_CHUNK_MODES = ("disabled", "variable", "section", "page")


class ValidationError(Exception):
    """Raised when input validation fails. Converted to MCP error text."""

    def __init__(self, message: str, *, guidance: str) -> None:
        super().__init__(message)
        self.guidance = guidance


def validate_document_url(url: str | list[str]) -> None:
    """Validate document URL(s) have allowed schemes."""
    urls = [url] if isinstance(url, str) else url
    for u in urls:
        if not isinstance(u, str):
            raise ValidationError(
                f"document_url must be a string, got {type(u).__name__}",
                guidance="Provide a URL string (http://, https://, reducto://, or jobid://).",
            )
        if not any(u.startswith(scheme) for scheme in ALLOWED_URL_SCHEMES):
            raise ValidationError(
                f"Invalid URL scheme in '{u}'. Allowed: {', '.join(ALLOWED_URL_SCHEMES)}",
                guidance="Use http://, https://, reducto://, or jobid:// URLs.",
            )


def validate_enum(value: str, valid_values: tuple[str, ...], param_name: str) -> None:
    """Validate a string parameter is one of the allowed values."""
    if value not in valid_values:
        raise ValidationError(
            f"Invalid {param_name}: '{value}'. Must be one of: {', '.join(valid_values)}",
            guidance=f"Use one of: {', '.join(valid_values)}",
        )


def validate_schema(schema: Any) -> dict[str, Any]:
    """Validate and normalize a JSON schema parameter.

    Accepts both dicts and JSON strings (Notion pattern for quirky MCP clients).
    """
    if isinstance(schema, str):
        try:
            schema = json.loads(schema)
        except json.JSONDecodeError as exc:
            raise ValidationError(
                "Invalid JSON in schema parameter.",
                guidance="Provide a valid JSON object for the schema.",
            ) from exc

    if not isinstance(schema, dict):
        raise ValidationError(
            f"schema must be a JSON object, got {type(schema).__name__}",
            guidance="Provide a JSON object with 'type', 'properties', etc.",
        )

    return schema


def validate_categories(categories: Any) -> list[dict[str, Any]]:
    """Validate and normalize categories parameter for split/classify.

    Accepts both lists and JSON strings.
    """
    if isinstance(categories, str):
        try:
            categories = json.loads(categories)
        except json.JSONDecodeError as exc:
            raise ValidationError(
                "Invalid JSON in categories parameter.",
                guidance="Provide a valid JSON array of category objects.",
            ) from exc

    if not isinstance(categories, list):
        raise ValidationError(
            f"categories must be a list, got {type(categories).__name__}",
            guidance="Provide a list of category objects.",
        )

    if len(categories) == 0:
        raise ValidationError(
            "categories must not be empty.",
            guidance="Provide at least one category.",
        )

    return categories


def parse_options_dict(options: Any) -> dict[str, Any] | None:
    """Parse and validate the options escape-hatch parameter.

    Accepts both dicts and JSON strings (Notion pattern).
    Returns None if options is None/empty.
    """
    if options is None:
        return None

    if isinstance(options, str):
        if not options.strip():
            return None
        try:
            options = json.loads(options)
        except json.JSONDecodeError as exc:
            raise ValidationError(
                "Invalid JSON in options parameter.",
                guidance="Provide a valid JSON object for options, or omit the parameter.",
            ) from exc

    if not isinstance(options, dict):
        raise ValidationError(
            f"options must be a JSON object, got {type(options).__name__}",
            guidance="Provide a JSON object for options, or omit the parameter.",
        )

    return options if options else None
