"""Consistent API error envelope.

Every error response has the shape::

    {
      "error": {
        "type": "validation_error",
        "detail": ...,
        "request_id": "..."
      }
    }
"""
from __future__ import annotations

import logging

from rest_framework.views import exception_handler

from .context import get_context

logger = logging.getLogger("bunchly.api")


def bunchly_exception_handler(exc, context):
    response = exception_handler(exc, context)
    request_id = get_context().request_id

    if response is None:
        # Unhandled exception — log and return a generic 500 envelope.
        logger.exception("Unhandled API exception", extra={"request_id": request_id})
        from rest_framework.response import Response

        return Response(
            {
                "error": {
                    "type": "server_error",
                    "detail": "An unexpected error occurred.",
                    "request_id": request_id,
                }
            },
            status=500,
        )

    error_type = exc.__class__.__name__
    error_type = "".join(
        ["_" + c.lower() if c.isupper() else c for c in error_type]
    ).lstrip("_")

    response.data = {
        "error": {
            "type": error_type,
            "detail": response.data,
            "request_id": request_id,
        }
    }
    return response
