# SPDX-License: LGPL-3.0-or-later
# (c) 2025 Frank David Martínez Muñoz. <mnesarco at gmail.com>

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Iterator

from DraftVecUtils import equals, rotate2D  # type: ignore
from FreeCAD import Vector  # type: ignore
from Part import (  # type: ignore
    Arc,
    BezierCurve,
    BSplineCurve,
    Ellipse,
    Face,
    LineSegment,
    OCCError,
    Shape,
)
from Part import makeCompound as make_compound  # type: ignore

from .cache import cached_copy, cached_copy_list
from .geom import DraftPrecision, precision_step, arc_end_to_center, make_wire
from .parsers import parse_floats
from .shape import SvgShape


class PathCommands:
    _op = "([mMlLhHvVaAcCqQsStTzZ])"
    _args = "([^mMlLhHvVaAcCqQsStTzZ]*)"
    _command = "\\s*?" + _op + "\\s*?" + _args + "\\s*?"
    regex = re.compile(_command, re.DOTALL)

    def __init__(self, d: str):
        regex = self.regex
        self.commands = [(cmd, parse_floats(args)) for cmd, args in regex.findall(d)]

    def __iter__(self):
        return iter(self.commands)


@dataclass
class PathBreak(Exception):
    point: Vector
    end: bool


class SvgSubPath:
    """Disconnected subpath."""

    def __init__(self, discretization: int) -> None:
        self.path = []
        self.last_v = None
        self.first_v = None
        self.last_pole = None
        self.discretization = discretization

    def add_line(self, d: str, args: list[float], *, relative: bool) -> None:
        path = self.path
        if d in "Mm":
            x = args.pop(0)
            y = args.pop(0)
            if relative and self.last_v:
                self.last_v = self.last_v.add(Vector(x, -y, 0))
            else:
                self.last_v = Vector(x, -y, 0)
            self.first_v = self.last_v

        for x, y in zip(args[0::2], args[1::2]):
            if relative:
                current_v = self.last_v.add(Vector(x, -y, 0))
            else:
                current_v = Vector(x, -y, 0)

            if not equals(self.last_v, current_v):
                seg = LineSegment(self.last_v, current_v).toShape()
                path.append(seg)
            self.last_v = current_v

        self.last_pole = None

    def add_horizontal(self, args: list[float], relative: bool):
        path = self.path
        for x in args:
            if relative:
                current_v = self.last_v.add(Vector(x, 0, 0))
            else:
                current_v = Vector(x, self.last_v.y, 0)
            if not equals(self.last_v, current_v):
                seg = LineSegment(self.last_v, current_v).toShape()
                path.append(seg)
            self.last_v = current_v
            self.last_pole = None

    def add_vertical(self, args: list[float], relative: bool):
        path = self.path
        for y in args:
            if relative:
                current_v = self.last_v.add(Vector(0, -y, 0))
            else:
                current_v = Vector(self.last_v.x, -y, 0)
            if not equals(self.last_v, current_v):
                seg = LineSegment(self.last_v, current_v).toShape()
                path.append(seg)
            self.last_v = current_v
            self.last_pole = None

    def add_arc(self, args: list[float], relative: bool):
        path = self.path
        p_iter = zip(
            args[0::7],
            args[1::7],
            args[2::7],
            args[3::7],
            args[4::7],
            args[5::7],
            args[6::7],
        )
        for rx, ry, x_rotation, large_flag, sweep_flag, x, y in p_iter:
            # support for large-arc and x-rotation is missing
            if relative:
                current_v = self.last_v.add(Vector(x, -y, 0))
            else:
                current_v = Vector(x, -y, 0)
            chord = current_v.sub(self.last_v)
            # small circular arc
            _precision = precision_step(DraftPrecision)
            if (not large_flag) and abs(rx - ry) < _precision:
                # perp = chord.cross(Vector(0, 0, -1))
                # here is a better way to find the perpendicular
                if sweep_flag == 1:
                    # clockwise
                    perp = rotate2D(chord, -math.pi / 2)
                else:
                    # anticlockwise
                    perp = rotate2D(chord, math.pi / 2)
                chord.multiply(0.5)
                if chord.Length > rx:
                    a = 0
                else:
                    a = math.sqrt(rx**2 - chord.Length**2)
                s = rx - a
                perp.multiply(s / perp.Length)
                midpoint = self.last_v.add(chord.add(perp))
                _seg = Arc(self.last_v, midpoint, current_v)
                seg = _seg.toShape()
            # big arc or elliptical arc
            else:
                # Calculate the possible centers for an arc
                # in 'endpoint parameterization'.
                _x_rot = math.radians(-x_rotation)
                (solution, (rx, ry)) = arc_end_to_center(
                    self.last_v, current_v, rx, ry, x_rotation=_x_rot, correction=True
                )
                # Chose one of the two solutions
                neg_sol = large_flag != sweep_flag
                v_center, angle1, angle_delta = solution[neg_sol]
                # print(angle1)
                # print(angle_delta)
                if ry > rx:
                    rx, ry = ry, rx
                    swap_axis = True
                else:
                    swap_axis = False
                # print('Elliptical arc %s rx=%f ry=%f'
                #       % (v_center, rx, ry))
                e1 = Ellipse(v_center, rx, ry)
                if sweep_flag:
                    # Step4
                    # angle_delta = -(-angle_delta % (2*math.pi))
                    # angle_delta = (-angle_delta % (2*math.pi))
                    angle1 = angle1 + angle_delta
                    angle_delta = -angle_delta
                    # angle1 = math.pi - angle1

                d90 = math.radians(90)
                e1a = Arc(e1, angle1 - swap_axis * d90, angle1 + angle_delta - swap_axis * d90)
                # e1a = Arc(e1,
                #                angle1 - 0 * swap_axis * d90,
                #                angle1 + angle_delta
                #                       - 0 * swap_axis * d90)
                seg = e1a.toShape()
                if swap_axis:
                    seg.rotate(v_center, Vector(0, 0, 1), 90)
                _precision = precision_step(DraftPrecision)
                if abs(x_rotation) > _precision:
                    seg.rotate(v_center, Vector(0, 0, 1), -x_rotation)
                if sweep_flag:
                    seg.reverse()
                    # DEBUG
                    # obj = self.doc.addObject("Part::Feature",
                    #                       'DEBUG %s' % pathname)
                    # obj.Shape = seg
                    # _seg = LineSegment(last_v, current_v)
                    # seg = _seg.toShape()
            self.last_v = current_v
            path.append(seg)
            self.last_pole = None

    def add_cubic_bezier(self, args: list[float], relative: bool, smooth: bool):
        path = self.path
        if smooth:
            p_iter = list(
                zip(
                    args[2::4],
                    args[3::4],
                    args[0::4],
                    args[1::4],
                    args[2::4],
                    args[3::4],
                )
            )
        else:
            p_iter = list(
                zip(
                    args[0::6],
                    args[1::6],
                    args[2::6],
                    args[3::6],
                    args[4::6],
                    args[5::6],
                )
            )
        for p1x, p1y, p2x, p2y, x, y in p_iter:
            if smooth:
                if self.last_pole is not None and self.last_pole[0] == "cubic":
                    pole1 = self.last_v.sub(self.last_pole[1]).add(self.last_v)
                else:
                    pole1 = self.last_v
            else:
                if relative:
                    pole1 = self.last_v.add(Vector(p1x, -p1y, 0))
                else:
                    pole1 = Vector(p1x, -p1y, 0)
            if relative:
                current_v = self.last_v.add(Vector(x, -y, 0))
                pole2 = self.last_v.add(Vector(p2x, -p2y, 0))
            else:
                current_v = Vector(x, -y, 0)
                pole2 = Vector(p2x, -p2y, 0)

            if not equals(current_v, self.last_v):
                # mainv = current_v.sub(last_v)
                # pole1v = last_v.add(pole1)
                # pole2v = current_v.add(pole2)
                # print("cubic curve data:",
                #       mainv.normalize(),
                #       pole1v.normalize(),
                #       pole2v.normalize())
                _precision = precision_step(DraftPrecision + 2)
                _d1 = pole1.distanceToLine(self.last_v, current_v)
                _d2 = pole2.distanceToLine(self.last_v, current_v)
                if True and _d1 < _precision and _d2 < _precision:
                    # print("straight segment")
                    _seg = LineSegment(self.last_v, current_v)
                    seg = _seg.toShape()
                else:
                    # print("cubic bezier segment")
                    b = BezierCurve()
                    b.setPoles([self.last_v, pole1, pole2, current_v])
                    seg = approx_bspline(b, self.discretization).toShape()
                # print("connect ", last_v, current_v)
                path.append(seg)
            self.last_v = current_v
            self.last_pole = ("cubic", pole2)

    def add_quadratic_bezier(self, args: list[float], relative: bool, smooth: bool):
        path = self.path
        if smooth:
            p_iter = list(
                zip(
                    args[1::2],
                    args[1::2],
                    args[0::2],
                    args[1::2],
                )
            )
        else:
            p_iter = list(
                zip(
                    args[0::4],
                    args[1::4],
                    args[2::4],
                    args[3::4],
                )
            )
        for px, py, x, y in p_iter:
            if smooth:
                if self.last_pole is not None and self.last_pole[0] == "quadratic":
                    pole = self.last_v.sub(self.last_pole[1]).add(self.last_v)
                else:
                    pole = self.last_v
            else:
                if relative:
                    pole = self.last_v.add(Vector(px, -py, 0))
                else:
                    pole = Vector(px, -py, 0)
            if relative:
                current_v = self.last_v.add(Vector(x, -y, 0))
            else:
                current_v = Vector(x, -y, 0)

            if not equals(current_v, self.last_v):
                _precision = 20 ** (-1 * (2 + DraftPrecision))
                _distance = pole.distanceToLine(self.last_v, current_v)
                if _distance < _precision:
                    _seg = LineSegment(self.last_v, current_v)
                    seg = _seg.toShape()
                else:
                    b = BezierCurve()
                    b.setPoles([self.last_v, pole, current_v])
                    seg = approx_bspline(b, self.discretization).toShape()
                path.append(seg)
            self.last_v = current_v
            self.last_pole = ("quadratic", pole)

    def add_close(self):
        path = self.path
        if not equals(self.last_v, self.first_v):
            try:
                path.append(LineSegment(self.last_v, self.first_v).toShape())
            except OCCError:
                pass
            if self.first_v:
                # Move relative to recent draw command
                self.last_v = self.first_v
        if self.first_v:
            raise PathBreak(self.first_v, False)

    def start(self, commands: Iterator[tuple[str, list[float]]]):
        for d, args in commands:
            relative = d.islower()
            smooth = d in "sStT"

            if d in "LlMm" and args:
                self.add_line(d, args, relative=relative)

            elif d in "Hh":
                self.add_horizontal(args, relative)

            elif d in "Vv":
                self.add_vertical(args, relative)

            elif d in "Aa":
                self.add_arc(args, relative)

            elif d in "CcSs":
                self.add_cubic_bezier(args, relative, smooth)

            elif d in "QqTt":
                self.add_quadratic_bezier(args, relative, smooth)

            elif d in "Zz":
                self.add_close()
                raise PathBreak(self.first_v, False)

        raise PathBreak(self.last_v, True)


@dataclass
class SvgPath(SvgShape):
    d: str
    discretization: int

    @cached_copy
    def to_shape(self) -> Shape | None:
        paths = [s for s in self.shapes()]
        if paths:
            return make_compound(paths)

    @cached_copy_list
    def shapes(self) -> list[Shape]:
        paths: list[SvgSubPath] = []
        commands = iter(PathCommands(self.d))
        path = None
        while True:
            if path is None:
                path = SvgSubPath(self.discretization)
                paths.append(path)
            try:
                path.start(commands)
            except PathBreak as ex:
                if ex.end:
                    break
                path = SvgSubPath(self.discretization)
                path.last_v = ex.point
                path.first_v = ex.point
                paths.append(path)

        shapes = []
        for sub_path in paths:
            if sub_path.path:
                sh = make_wire(sub_path.path, check_closed=False)
                if self.style.fill_color and sh.isClosed():
                    sh = Face(sh)
                    if not sh.isValid():
                        sh.fix(1e-6, 0, 1)
                sh = sh.transformGeometry(self.transform)
                shapes.append(sh)

        return shapes


def approx_bspline(
    curve: BezierCurve,
    num: int = 10,
    tol: float = 1e-7,
) -> BSplineCurve | BezierCurve:
    _p0, d0 = curve.getD1(curve.FirstParameter)
    _p1, d1 = curve.getD1(curve.LastParameter)
    if (d0.Length < tol) or (d1.Length < tol):
        tan1 = curve.tangent(curve.FirstParameter)[0]
        tan2 = curve.tangent(curve.LastParameter)[0]
        pts = curve.discretize(num)
        bs = BSplineCurve()
        bs.interpolate(Points=pts, InitialTangent=tan1, FinalTangent=tan2)
        return bs
    return curve
