# SPDX-License: LGPL-3.0-or-later
# (c) 2025 Frank David Martínez Muñoz. <mnesarco at gmail.com>

from __future__ import annotations

from dataclasses import dataclass

from FreeCAD import Vector  # type: ignore
from Part import Shape, Wire, Face, Ellipse  # type: ignore

from .shape import SvgShape
from .cache import cached_copy


@dataclass
class SvgEllipse(SvgShape):
    cx: float
    cy: float
    rx: float
    ry: float

    @cached_copy
    def to_shape(self) -> Shape | None:
        c = Vector(self.cx, -self.cy, 0)
        rx = self.rx
        ry = self.ry

        if rx < 0 or ry < 0:
            return None

        if rx > ry:
            sh = Ellipse(c, rx, ry).toShape()
        else:
            sh = Ellipse(c, ry, rx).toShape()
            sh.rotate(c, Vector(0, 0, 1), 90)
        if self.style.fill_color:
            sh = Face(Wire([sh]))
        sh = sh.transformGeometry(self.transform)
        return sh
