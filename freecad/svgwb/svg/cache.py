# SPDX-License: LGPL-3.0-or-later
# (c) 2025 Frank David Martínez Muñoz. <mnesarco at gmail.com>

from __future__ import annotations

from functools import cached_property, wraps  # noqa: F401
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from Part import Shape  # type: ignore

CACHE_MISS = object()
T = TypeVar("T")


def cached_copy(fn: T) -> T:
    """Return a copy of the cached Shape."""
    attr = f"_cached_{fn.__name__}"

    @wraps(fn)
    def getter(self, *args, **kwargs) -> Shape | None:  # noqa: ANN001
        cache = getattr(self, attr, CACHE_MISS)
        if cache is None:
            return None
        if cache is not CACHE_MISS:
            return cache.copy()
        cache = fn(self, *args, **kwargs)
        setattr(self, attr, cache)
        return cache

    return getter


def cached_copy_list(fn: T) -> T:
    """Return a list of copies of the cached Shapes."""
    attr = f"_cached_{fn.__name__}"

    @wraps(fn)
    def getter(self, *args, **kwargs) -> list[Shape]:  # noqa: ANN001
        cache = getattr(self, attr, CACHE_MISS)
        if cache is None:
            return []
        if cache is not CACHE_MISS:
            return [s.copy() for s in cache]
        cache = fn(self, *args, **kwargs)
        setattr(self, attr, cache)
        return cache or []

    return getter
