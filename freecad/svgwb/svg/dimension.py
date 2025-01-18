# SPDX-License: LGPL-3.0-or-later
# (c) 2025 Frank David Martínez Muñoz. <mnesarco at gmail.com>

from __future__ import annotations

from dataclasses import dataclass

from FreeCAD import Vector  # type: ignore
from Draft import make_dimension  # type: ignore

from .shape import SvgShape


@dataclass
class SvgDimension(SvgShape):
    x1: float
    y1: float
    x2: float
    y2: float
    x3: float
    y3: float

    def to_dimension(self):
        points = [
            Vector(self.x1, -self.y1, 0),
            Vector(self.x2, -self.y2, 0),
            Vector(self.x3, -self.y3, 0),
        ]
        return make_dimension([self.transform.multiply(p) for p in points])
