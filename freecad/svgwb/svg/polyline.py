# SPDX-License: LGPL-3.0-or-later
# (c) 2025 Frank David Martínez Muñoz. <mnesarco at gmail.com>

from __future__ import annotations

from dataclasses import dataclass

from DraftVecUtils import equals  # type: ignore
from FreeCAD import Vector  # type: ignore
from Part import Face, LineSegment, Shape, Wire  # type: ignore

from .shape import SvgShape
from .cache import cached_copy


@dataclass
class SvgPolyLine(SvgShape):
    """Polygon Edge"""

    points: list[float]
    close: bool = False

    @cached_copy
    def to_shape(self) -> Shape | None:
        # A simpler implementation would be
        # _p = zip(points[0::2], points[1::2])
        # sh = Part.makePolygon([Vector(svg_x,
        #                               -svg_y,
        #                               0) for svg_x, svg_y in _p])
        #
        # but it would be more difficult to search for duplicate
        # points beforehand.
        points = self.points
        n = len(points)
        if not (n >= 4 and n % 2 == 0):
            return None

        last_v = Vector(points[0], -points[1], 0)
        path = []
        if self.close:
            points = points + points[:2]  # emulate closed path

        for svg_x, svg_y in zip(points[2::2], points[3::2], strict=False):
            current_v = Vector(svg_x, -svg_y, 0)
            if not equals(last_v, current_v):
                seg = LineSegment(last_v, current_v).toShape()
                last_v = current_v
                path.append(seg)

        if path:
            sh = Wire(path)
            if self.style.fill_color and sh.isClosed():
                sh = Face(sh)
            return sh.transformGeometry(self.transform)

        return None
