from __future__ import annotations

import pytest

from hify.shared.domain.pagination import MAX_PAGE_SIZE, PageRequest, build_page


def test_page_request_exposes_limit_plus_one() -> None:
    request = PageRequest(limit=10, cursor="abc")

    assert request.limit_plus_one == 11


@pytest.mark.parametrize("limit", [0, MAX_PAGE_SIZE + 1])
def test_page_request_rejects_invalid_limit(limit: int) -> None:
    with pytest.raises(ValueError, match="limit must be"):
        PageRequest(limit=limit)


def test_build_page_trims_extra_item_and_sets_next_cursor() -> None:
    page = build_page([1, 2, 3], PageRequest(limit=2), "next")

    assert page.items == (1, 2)
    assert page.next_cursor == "next"
    assert page.has_more


def test_build_page_without_extra_item_has_no_next_cursor() -> None:
    page = build_page([1, 2], PageRequest(limit=2), "next")

    assert page.items == (1, 2)
    assert page.next_cursor is None
    assert not page.has_more
