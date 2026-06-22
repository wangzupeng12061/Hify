from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Sequence, TypeVar


T = TypeVar("T")

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


@dataclass(frozen=True, slots=True)
class PageRequest:
    limit: int = DEFAULT_PAGE_SIZE
    cursor: str | None = None

    def __post_init__(self) -> None:
        if self.limit < 1 or self.limit > MAX_PAGE_SIZE:
            raise ValueError(f"limit must be between 1 and {MAX_PAGE_SIZE}")

    @property
    def limit_plus_one(self) -> int:
        return self.limit + 1


@dataclass(frozen=True, slots=True)
class Page(Generic[T]):
    items: tuple[T, ...]
    next_cursor: str | None
    has_more: bool


def build_page(items: Sequence[T], request: PageRequest, next_cursor: str | None = None) -> Page[T]:
    if len(items) > request.limit:
        return Page(items=tuple(items[: request.limit]), next_cursor=next_cursor, has_more=True)
    return Page(items=tuple(items), next_cursor=None, has_more=False)
