# SPDX-License: LGPL-3.0-or-later
# (c) 2025 Frank David Martínez Muñoz. <mnesarco at gmail.com>

from __future__ import annotations

from dataclasses import dataclass

from FreeCAD import Vector, Matrix  # type: ignore
from Part import Shape, LineSegment, Wire, Ellipse, Arc, Face  # type: ignore
from DraftVecUtils import equals  # type: ignore

from .shape import SvgShape
from .geom import precision_step
from .cache import cached_copy
import math


@dataclass
class SvgRect(SvgShape):
    x: float
    y: float
    width: float
    height: float
    rx: float
    ry: float
    precision : int

    def rounded_edges(self) -> list[Shape]:
        max_rx = self.width / 2.0
        max_ry = self.height / 2.0
        rx = self.rx
        ry = self.ry or rx
        rx = rx or ry
        if rx > max_rx:
            rx = max_rx
        if ry > max_ry:
            ry = max_ry

        _precision = precision_step(self.precision)
        if rx < _precision or ry < _precision:
            return self.straight_edges()

        x, y, w, h = self.x, -self.y, self.width, self.height

        # fmt: off
        p1 = Vector(x + rx,     y - h + ry, 0)
        p2 = Vector(x + w - rx, y - h + ry, 0)
        p3 = Vector(x + w - rx,     y - ry, 0)
        p4 = Vector(x + rx,         y - ry, 0)
        # fmt: on

        if rx >= ry:
            e = Ellipse(Vector(), rx, ry)
            e1a = Arc(e, math.radians(180), math.radians(270))
            e2a = Arc(e, math.radians(270), math.radians(360))
            e3a = Arc(e, math.radians(0), math.radians(90))
            e4a = Arc(e, math.radians(90), math.radians(180))
            m = Matrix()
        else:
            e = Ellipse(Vector(), ry, rx)
            e1a = Arc(e, math.radians(90), math.radians(180))
            e2a = Arc(e, math.radians(180), math.radians(270))
            e3a = Arc(e, math.radians(270), math.radians(360))
            e4a = Arc(e, math.radians(0), math.radians(90))
            # rotate +90 degrees
            m = Matrix(0, -1, 0, 0, 1, 0)
        esh = []
        for arc, point in ((e1a, p1), (e2a, p2), (e3a, p3), (e4a, p4)):
            m1 = Matrix(m)
            m1.move(point)
            arc.transform(m1)
            esh.append(arc.toShape())
        edges = []
        for esh1, esh2 in zip(esh[-1:] + esh[:-1], esh):
            p1 = esh1.Vertexes[-1].Point
            p2 = esh2.Vertexes[0].Point
            if not equals(p1, p2):
                # straight segments
                _sh = LineSegment(p1, p2).toShape()
                edges.append(_sh)
            # elliptical segments
            edges.append(esh2)
        return edges

    def straight_edges(self) -> list[Shape]:
        x, y, w, h = self.x, -self.y, self.width, self.height
        # fmt: off
        p1 = Vector(x,         y, 0)
        p2 = Vector(x + w,     y, 0)
        p3 = Vector(x + w, y - h, 0)
        p4 = Vector(x,     y - h, 0)
        # fmt: on
        edges = [
            LineSegment(p1, p2).toShape(),
            LineSegment(p2, p3).toShape(),
            LineSegment(p3, p4).toShape(),
            LineSegment(p4, p1).toShape(),
        ]
        return edges

    @cached_copy
    def to_shape(self) -> Shape | None:
        edges = self.rounded_edges()
        sh = Wire(edges)
        if self.style.fill_color:
            sh = Face(sh)
        sh = sh.transformGeometry(self.transform)
        return sh
