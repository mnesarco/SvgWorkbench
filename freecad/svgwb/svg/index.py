# SPDX-License: LGPL-3.0-or-later
# (c) 2025 Frank David Martínez Muñoz. <mnesarco at gmail.com>

from typing import Iterator
from .shape import SvgShape

class SvgIndex:
    _data: dict[str, SvgShape]

    def __init__(self):
        self._data = {}

    def add(self, shape: SvgShape):
        self._data[shape.id] = shape

    def find(self, id: str) -> SvgShape | None:
        return self._data.get(id)

    def __repr__(self):
        return str(list(self._data.keys()))

    def items(self) -> Iterator[tuple[str, SvgShape]]:
        return self._data.items()