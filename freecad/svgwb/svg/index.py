# SPDX-License: LGPL-3.0-or-later
# (c) 2025 Frank David Martínez Muñoz. <mnesarco at gmail.com>

from collections.abc import Iterator
from .shape import SvgShape


class SvgIndex:
    """In Memory index of all shapes parsed from an svg."""

    _data: dict[str, SvgShape]

    def __init__(self) -> None:
        self._data = {}

    def add(self, shape: SvgShape) -> None:
        self._data[shape.id] = shape

    def find(self, id: str) -> SvgShape | None:  # noqa: A002
        return self._data.get(id)

    def __repr__(self) -> str:
        return str(list(self._data.keys()))

    def items(self) -> Iterator[tuple[str, SvgShape]]:
        return self._data.items()
