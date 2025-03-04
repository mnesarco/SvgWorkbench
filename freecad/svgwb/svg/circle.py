# SPDX-License: LGPL-3.0-or-later
# (c) 2025 Frank David Martínez Muñoz. <mnesarco at gmail.com>

from __future__ import annotations

from dataclasses import dataclass

from FreeCAD import Vector  # type: ignore
from Part import Shape, Wire, Face, makeCircle as make_circle  # type: ignore

from .shape import SvgShape
from .cache import cached_copy


@dataclass
class SvgCircle(SvgShape):
    """
    Circle Edge.
    """

    cx: float
    cy: float
    r: float

    @cached_copy
    def to_shape(self) -> Shape | None:
        sh = make_circle(self.r)
        if self.style.fill_color:
            sh = Face(Wire([sh]))
        sh.translate(Vector(self.cx, -self.cy, 0))
        return sh.transformGeometry(self.transform)
