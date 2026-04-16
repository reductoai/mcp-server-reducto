"""Shared test fixtures for Reducto MCP server tests."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest


def _make_parse_response(
    *,
    job_id: str = "job_parse_123",
    duration: float = 2.5,
    num_pages: int = 3,
    studio_link: str = "https://studio.reducto.ai/job_parse_123",
) -> Any:
    """Create a mock ParseResponse."""
    block1 = SimpleNamespace(type="text", content="Hello world paragraph.")
    block2 = SimpleNamespace(type="table", content="<table><tr><td>A</td></tr></table>")
    block3 = SimpleNamespace(type="title", content="Document Title")

    chunk = SimpleNamespace(blocks=[block1, block2, block3])
    result = SimpleNamespace(type="full", chunks=[chunk])
    usage = SimpleNamespace(num_pages=num_pages, credits=1.5)

    return SimpleNamespace(
        job_id=job_id,
        duration=duration,
        studio_link=studio_link,
        usage=usage,
        result=result,
    )


def _make_extract_response(
    *,
    job_id: str = "job_extract_456",
    studio_link: str = "https://studio.reducto.ai/job_extract_456",
) -> Any:
    """Create a mock ExtractResponse."""
    usage = SimpleNamespace(num_pages=2, num_fields=3, credits=2.0)
    return SimpleNamespace(
        job_id=job_id,
        studio_link=studio_link,
        usage=usage,
        result={"name": "Acme Corp", "amount": 1500.00, "date": "2024-01-15"},
    )


def _make_split_response() -> Any:
    """Create a mock SplitResponse."""
    usage = SimpleNamespace(num_pages=10, credits=3.0)
    split1 = SimpleNamespace(name="Introduction", pages=[1, 2], conf="high")
    split2 = SimpleNamespace(name="Financial Data", pages=[3, 4, 5, 6], conf="high")
    split3 = SimpleNamespace(name="Appendix", pages=[7, 8, 9, 10], conf="low")
    result = SimpleNamespace(splits=[split1, split2, split3])
    return SimpleNamespace(usage=usage, result=result)


def _make_classify_response() -> Any:
    """Create a mock ClassifyResponse."""
    result = SimpleNamespace(category="invoice")
    cat_conf = [
        SimpleNamespace(category="invoice", confidence=0.92),
        SimpleNamespace(category="contract", confidence=0.05),
        SimpleNamespace(category="receipt", confidence=0.03),
    ]
    confidence = SimpleNamespace(categories=cat_conf)
    return SimpleNamespace(
        job_id="job_classify_789",
        duration=1.2,
        result=result,
        response_confidence=confidence,
    )


def _make_edit_response() -> Any:
    """Create a mock EditResponse."""
    usage = SimpleNamespace(num_pages=1)
    return SimpleNamespace(
        document_url="https://storage.reducto.ai/edited/doc123.pdf",
        usage=usage,
    )


def _make_upload_response() -> Any:
    """Create a mock UploadResponse."""
    return SimpleNamespace(file_id="reducto://abc123", presigned_url=None)


def _make_job_retrieve_response() -> Any:
    """Create a mock job retrieval response."""

    class FakeJobResponse:
        def __init__(self):
            self.job_id = "job_parse_123"
            self.status = "Completed"
            self.result = {"blocks": []}

        def model_dump(self, mode: str = "python") -> dict:
            return {"job_id": self.job_id, "status": self.status, "result": self.result}

    return FakeJobResponse()


def _make_job_list_response() -> Any:
    """Create a mock job list response."""

    class FakeJobList:
        def __init__(self):
            self.jobs = [
                {"job_id": "job1", "status": "Completed", "created_at": "2024-01-15T10:00:00Z"},
                {"job_id": "job2", "status": "Pending", "created_at": "2024-01-15T10:01:00Z"},
            ]

        def model_dump(self, mode: str = "python") -> dict:
            return {"jobs": self.jobs}

    return FakeJobList()


@pytest.fixture
def mock_client() -> AsyncMock:
    """Create a fully mocked AsyncReducto client with realistic responses."""
    client = AsyncMock()

    # Parse
    client.parse = AsyncMock()
    client.parse.run = AsyncMock(return_value=_make_parse_response())

    # Extract
    client.extract = AsyncMock()
    client.extract.run = AsyncMock(return_value=_make_extract_response())

    # Split
    client.split = AsyncMock()
    client.split.run = AsyncMock(return_value=_make_split_response())

    # Classify
    client.classify = AsyncMock()
    client.classify.run = AsyncMock(return_value=_make_classify_response())

    # Edit
    client.edit = AsyncMock()
    client.edit.run = AsyncMock(return_value=_make_edit_response())

    # Upload — upload() is a method on the client itself, not a resource
    client.upload = AsyncMock(return_value=_make_upload_response())

    # Jobs
    client.job = AsyncMock()
    client.job.get = AsyncMock(return_value=_make_job_retrieve_response())
    client.job.get_all = AsyncMock(return_value=_make_job_list_response())

    return client


@pytest.fixture
def mock_ctx(mock_client: AsyncMock) -> MagicMock:
    """Create a mock MCP Context that returns the mock client."""
    ctx = MagicMock()
    # Set up the fastmcp server mock with _test_client
    server = MagicMock()
    server._test_client = mock_client
    ctx.fastmcp = server
    return ctx
