"""
CodeSentinel Backend: Response Envelope Helpers & Middleware.

Enforces the universal APIResponse envelope across all endpoints and exception handlers.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TypeVar
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from shared.schemas.common import APIError, APIResponse, PaginationMeta, utc_now

T = TypeVar("T")


def success_response(
    data: Optional[T] = None,
    message: str = "Operation completed successfully.",
    pagination: Optional[PaginationMeta] = None,
    status_code: int = status.HTTP_200_OK,
) -> APIResponse[T]:
    """
    Construct a standardized success APIResponse envelope.

    Args:
        data: The typed data payload.
        message: Informational message about the operation.
        pagination: Optional pagination metadata.
        status_code: Expected HTTP status code.

    Returns:
        An instance of APIResponse[T].
    """
    return APIResponse[T](
        success=True,
        message=message,
        data=data,
        error=None,
        pagination=pagination,
        timestamp=utc_now(),
    )


def error_response(
    code: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    trace_id: Optional[str] = None,
    status_code: int = status.HTTP_400_BAD_REQUEST,
) -> JSONResponse:
    """
    Construct a standardized error JSONResponse envelope.

    Args:
        code: Machine-readable error code.
        message: Human-readable error description.
        details: Optional diagnostic dictionary.
        trace_id: Optional trace ID.
        status_code: HTTP status code to return.

    Returns:
        JSONResponse containing serialized APIResponse envelope.
    """
    envelope = APIResponse[None](
        success=False,
        message=message,
        data=None,
        error=APIError(
            code=code,
            message=message,
            details=details,
            trace_id=trace_id,
        ),
        pagination=None,
        timestamp=utc_now(),
    )
    return JSONResponse(
        status_code=status_code,
        content=envelope.model_dump(mode="json"),
    )


def stub_not_implemented_response(feature_name: str) -> APIResponse[Dict[str, str]]:
    """
    Return a standardized stub response indicating the route contract is frozen
    and awaiting business logic implementation in subsequent phases.
    """
    return APIResponse[Dict[str, str]](
        success=True,
        message=f"Contract frozen for '{feature_name}'. Implementation pending in target build phase.",
        data={
            "module": feature_name,
            "status": "FROZEN_STUB",
            "phase": "PHASE_0_CONTRACT",
        },
        error=None,
        pagination=None,
        timestamp=utc_now(),
    )
