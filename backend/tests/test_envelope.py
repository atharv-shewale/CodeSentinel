"""
CodeSentinel Response Envelope Tests.

Verifies that success, error, and paginated responses conform to the universal
APIResponse[T] envelope specification.
"""

from fastapi import status
from shared.schemas.common import APIResponse, APIError, PaginationMeta
from app.core.envelope import success_response, error_response


def test_success_response_envelope():
    """Verify standard success response formatting."""
    res = success_response(data={"key": "value"}, message="Success message")
    assert isinstance(res, APIResponse)
    assert res.success is True
    assert res.message == "Success message"
    assert res.data == {"key": "value"}
    assert res.error is None
    assert res.timestamp is not None


def test_paginated_response_envelope():
    """Verify pagination metadata embedding."""
    pagination = PaginationMeta(
        total=100,
        page=2,
        page_size=20,
        total_pages=5,
        has_next=True,
        has_prev=True,
    )
    res = success_response(data=[1, 2, 3], pagination=pagination)
    assert res.pagination is not None
    assert res.pagination.total == 100
    assert res.pagination.page == 2
    assert res.pagination.has_next is True


def test_error_response_envelope():
    """Verify standard error JSONResponse formatting."""
    err_json = error_response(
        code="NOT_FOUND",
        message="Item could not be located",
        details={"entity_id": "123"},
        trace_id="trace-abc-123",
        status_code=status.HTTP_404_NOT_FOUND,
    )
    assert err_json.status_code == 404
    import json
    body = json.loads(err_json.body.decode("utf-8"))
    assert body["success"] is False
    assert body["data"] is None
    assert body["error"]["code"] == "NOT_FOUND"
    assert body["error"]["message"] == "Item could not be located"
    assert body["error"]["details"] == {"entity_id": "123"}
    assert body["error"]["trace_id"] == "trace-abc-123"
