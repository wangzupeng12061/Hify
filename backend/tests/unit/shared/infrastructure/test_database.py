from __future__ import annotations

from contextlib import AbstractAsyncContextManager

from hify.shared.infrastructure.database import session_scope


def test_session_scope_is_async_context_manager() -> None:
    scope = session_scope(None)  # type: ignore[arg-type]

    assert isinstance(scope, AbstractAsyncContextManager)
