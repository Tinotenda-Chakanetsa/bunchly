"""Per-request context store.

Holds the current request id, tenant, user and client metadata so that
services far from the view layer (audit logging, model save hooks,
structured log records) can access them without threading the request
object through every call.

Backed by a thread-local; the middleware populates it at the start of a
request and clears it at the end.
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from typing import Any

_state = threading.local()


@dataclass
class RequestContext:
    request_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    tenant: Any | None = None
    user: Any | None = None
    ip_address: str | None = None
    user_agent: str = ""

    @property
    def tenant_id(self) -> Any | None:
        return getattr(self.tenant, "id", None)

    @property
    def user_id(self) -> Any | None:
        user = self.user
        if user is not None and getattr(user, "is_authenticated", False):
            return user.pk
        return None


def get_context() -> RequestContext:
    """Return the current request context, creating an empty one if needed."""
    ctx = getattr(_state, "context", None)
    if ctx is None:
        ctx = RequestContext()
        _state.context = ctx
    return ctx


def set_context(ctx: RequestContext) -> None:
    _state.context = ctx


def clear_context() -> None:
    if hasattr(_state, "context"):
        del _state.context


def get_current_tenant() -> Any | None:
    return get_context().tenant


def get_current_user() -> Any | None:
    return get_context().user
