from __future__ import annotations

from hify.shared.domain.errors import ConflictError, HifyError


def test_hify_error_exports_stable_detail() -> None:
    error = HifyError("failed", metadata={"field": "name"})

    detail = error.to_detail()

    assert detail.code == "HIFY_ERROR"
    assert detail.message == "failed"
    assert detail.metadata == {"field": "name"}


def test_specific_error_overrides_code() -> None:
    error = ConflictError("duplicate")

    assert error.to_detail().code == "CONFLICT"
