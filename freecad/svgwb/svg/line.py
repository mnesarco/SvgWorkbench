# SPDX-License: LGPL-3.0-or-later
# (c) 2025 Frank David Martínez Muñoz. <mnesarco at gmail.com>

from __future__ import annotations

from dataclasses import dataclass

from FreeCAD import Vector  # type: ignore
from Part import Shape, LineSegment  # type: ignore

from .shape import SvgShape
from .cache import cached_copy


@dataclass
class SvgLine(SvgShape):
    """Line Edge"""

    x1: float
    y1: float
    x2: float
    y2: float

    @cached_copy
    def to_shape(self) -> Shape | None:
        p1 = Vector(self.x1, -self.y1, 0)
        p2 = Vector(self.x2, -self.y2, 0)
        sh = LineSegment(p1, p2).toShape()
        sh.transformGeometry(self.transform)
        return sh
