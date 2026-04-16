"""Tests for input validation module."""

from __future__ import annotations

import pytest

from mcp_server_reducto.validation import (
    ValidationError,
    parse_options_dict,
    validate_categories,
    validate_document_url,
    validate_enum,
    validate_schema,
)


class TestValidateDocumentUrl:
    def test_valid_https_url(self) -> None:
        validate_document_url("https://example.com/doc.pdf")

    def test_valid_http_url(self) -> None:
        validate_document_url("http://example.com/doc.pdf")

    def test_valid_reducto_url(self) -> None:
        validate_document_url("reducto://abc123")

    def test_valid_jobid_url(self) -> None:
        validate_document_url("jobid://job_123")

    def test_invalid_scheme(self) -> None:
        with pytest.raises(ValidationError, match="Invalid URL scheme"):
            validate_document_url("ftp://example.com/doc.pdf")

    def test_invalid_scheme_file(self) -> None:
        with pytest.raises(ValidationError, match="Invalid URL scheme"):
            validate_document_url("file:///etc/passwd")

    def test_list_of_urls_valid(self) -> None:
        validate_document_url(["https://a.com/1.pdf", "https://b.com/2.pdf"])

    def test_list_with_invalid_url(self) -> None:
        with pytest.raises(ValidationError, match="Invalid URL scheme"):
            validate_document_url(["https://a.com/1.pdf", "ftp://bad.com"])

    def test_non_string_in_list(self) -> None:
        with pytest.raises(ValidationError, match="must be a string"):
            validate_document_url([123])  # type: ignore[list-item]


class TestValidateEnum:
    def test_valid_value(self) -> None:
        validate_enum("html", ("html", "json", "md"), "table_output_format")

    def test_invalid_value(self) -> None:
        with pytest.raises(ValidationError, match="Invalid table_output_format"):
            validate_enum("xml", ("html", "json", "md"), "table_output_format")


class TestValidateSchema:
    def test_dict_passthrough(self) -> None:
        schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        result = validate_schema(schema)
        assert result == schema

    def test_json_string(self) -> None:
        result = validate_schema('{"type": "object"}')
        assert result == {"type": "object"}

    def test_invalid_json_string(self) -> None:
        with pytest.raises(ValidationError, match="Invalid JSON"):
            validate_schema("{bad json}")

    def test_non_dict_result(self) -> None:
        with pytest.raises(ValidationError, match="must be a JSON object"):
            validate_schema("[1, 2, 3]")

    def test_non_dict_input(self) -> None:
        with pytest.raises(ValidationError, match="must be a JSON object"):
            validate_schema(42)  # type: ignore[arg-type]


class TestValidateCategories:
    def test_list_passthrough(self) -> None:
        cats = [{"name": "intro", "description": "Introduction"}]
        assert validate_categories(cats) == cats

    def test_json_string(self) -> None:
        result = validate_categories('[{"name": "a"}]')
        assert result == [{"name": "a"}]

    def test_invalid_json(self) -> None:
        with pytest.raises(ValidationError, match="Invalid JSON"):
            validate_categories("[bad]")

    def test_not_a_list(self) -> None:
        with pytest.raises(ValidationError, match="must be a list"):
            validate_categories('{"name": "a"}')

    def test_empty_list(self) -> None:
        with pytest.raises(ValidationError, match="must not be empty"):
            validate_categories([])


class TestParseOptionsDict:
    def test_none_returns_none(self) -> None:
        assert parse_options_dict(None) is None

    def test_dict_passthrough(self) -> None:
        opts = {"key": "value"}
        assert parse_options_dict(opts) == opts

    def test_empty_dict_returns_none(self) -> None:
        assert parse_options_dict({}) is None

    def test_json_string(self) -> None:
        result = parse_options_dict('{"key": "value"}')
        assert result == {"key": "value"}

    def test_empty_string_returns_none(self) -> None:
        assert parse_options_dict("") is None
        assert parse_options_dict("   ") is None

    def test_invalid_json(self) -> None:
        with pytest.raises(ValidationError, match="Invalid JSON"):
            parse_options_dict("{bad}")

    def test_non_dict_json(self) -> None:
        with pytest.raises(ValidationError, match="must be a JSON object"):
            parse_options_dict("[1, 2]")
