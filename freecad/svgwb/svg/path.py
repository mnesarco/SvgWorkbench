# SPDX-License: LGPL-3.0-or-later
# (c) 2025 Frank David Martínez Muñoz. <mnesarco at gmail.com>

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Iterator

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
from .geom import DraftPrecision, precision_step, arc_end_to_center, make_wire, equals
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

    def __init__(self, discretization: int, precision: int, origin : Vector = Vector(0, 0, 0)) -> None:
        self.path = [{"type": "start", "last_v": origin}]
        self.discretization = discretization
        self.precision = precision

    def add_line(self, d: str, args: list[float], *, relative: bool) -> None:
        last_v = self.path[-1]["last_v"]
        if d in "Mm":
            x = args.pop(0)
            y = args.pop(0)
            if relative:
                last_v = last_v.add(Vector(x, -y, 0))
            else:
                last_v = Vector(x, -y, 0)
            # if we're at the beginning of a wire we overwrite the start vector
            if self.path[-1]["type"] == "start":
                self.path[-1]["last_v"] = last_v
            else:
                self.path.append({"type": "start", "last_v": last_v})    

        for x, y in zip(args[0::2], args[1::2]):
            if relative:
                last_v = last_v.add(Vector(x, -y, 0))
            else:
                last_v = Vector(x, -y, 0)
            self.path.append({"type": "line", "last_v": last_v})


    def add_horizontal(self, args: list[float], relative: bool):
        last_v = self.path[-1]["last_v"]
        for x in args:
            if relative:
                last_v = Vector(x + last_v.x, last_v.y, 0)
            else:
                last_v = Vector(x, last_v.y, 0)
            self.path.append({"type": "line", "last_v": last_v})

    def add_vertical(self, args: list[float], relative: bool):
        last_v = self.path[-1]["last_v"]
        for y in args:
            if relative:
                last_v = Vector(last_v.x, last_v.y - y, 0)
            else:
                last_v = Vector(last_v.x, - y, 0)
            self.path.append({"type": "line", "last_v": last_v})

    def add_arc(self, args: list[float], relative: bool):
        last_v = self.path[-1]["last_v"]
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
                last_v = last_v.add(Vector(x, -y, 0))
            else:
                last_v = Vector(x, -y, 0)
            self.path.append({"type": "arc", 
                              "rx": rx,
                              "ry": ry,
                              "x_rotation": x_rotation,
                              "large_flag": large_flag,
                              "sweep_flag": sweep_flag,
                              "last_v": last_v
                             })

    def add_cubic_bezier(self, args: list[float], relative: bool, smooth: bool):
        last_v = self.path[-1]["last_v"]
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
                if self.path[-1]["type"] == "cbezier":
                    pole1 = last_v.sub(self.path[-1]["pole2"]).add(last_v)
                else:
                    pole1 = last_v
            else:
                if relative:
                    pole1 = last_v.add(Vector(p1x, -p1y, 0))
                else:
                    pole1 = Vector(p1x, -p1y, 0)
            if relative:
                pole2 = last_v.add(Vector(p2x, -p2y, 0))
                last_v = last_v.add(Vector(x, -y, 0))
            else:
                pole2 = Vector(p2x, -p2y, 0)
                last_v = Vector(x, -y, 0)

            self.path.append({"type": "cbezier", 
                              "pole1": pole1,
                              "pole2": pole2,
                              "last_v": last_v
                             }) 

    def add_quadratic_bezier(self, args: list[float], relative: bool, smooth: bool):
        last_v = self.path[-1]["last_v"]
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
                if self.path[-1]["type"] == "qbezier":
                    pole = last_v.sub(self.path[-1]["pole"]).add(last_v)
                else:
                    pole = last_v
            else:
                if relative:
                    pole = last_v.add(Vector(px, -py, 0))
                else:
                    pole = Vector(px, -py, 0)
            if relative:
                last_v = last_v.add(Vector(x, -y, 0))
            else:
                last_v = Vector(x, -y, 0)
                
            self.path.append({"type": "qbezier", 
                              "pole": pole,
                              "last_v": last_v
                             }) 
            
    def get_last_start(self):
        """ Find the last Path data element of type 'start' """
        for dct in reversed(self.path):
            if dct["type"] == "start":
                return dct["last_v"]
        return Vector(0, 0, 0)

    def correct_last_v(self, path_data : dict, delta : Vector):
        """ Correct the endpoint of the given path dataset by
    	    the given delta and move possibly associated
    	    member accordingly.
    	"""
        if path_data["type"] == "cbezier":
                # for cbeziers we also relocate the second pole
                path_data["pole2"] = path_data["pole2"].sub(delta)
        elif path_data["type"] == "qbezier":
                # for qbeziers we also relocate the pole by half of the delta
                path_data["pole"] = path_data["pole"].sub(delta.scale(0.5, 0.5, 0))
        # all data types have last_v
        path_data["last_v"] = path_data["last_v"].sub(delta)

    def add_close(self):
        last_v  = self.path[-1]["last_v"]
        first_v = self.get_last_start()
        if equals(last_v, first_v, self.precision):
            # we assume identity of first and last at configured precision. 
            # So we have to make sure that they really are identical
            self.correct_last_v(self.path[-1], last_v.sub(first_v))
        else:
            self.path.append({"type": "line", "last_v": first_v})
        raise PathBreak(first_v, False)

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

        raise PathBreak(self.path[-1]["last_v"], True)
    
    def create_Edges(self):
        """ This Function creates shapes from path data sets and
            returns them in an ordered list.
        """
        if not type(self.path[0]) is dict:
            return None
        edges = []
        last_v = Vector(0, 0, 0)
        for pdset in self.path:
            next_v = pdset["last_v"];
            match (pdset["type"]):
                case "start":
                    last_v = next_v;
                case "line":
                    if equals(last_v, next_v, self.precision):
                        # line segment too short, we simply skip it
                        next_v = last_v
                    else:
                        edges.append(LineSegment(last_v, next_v).toShape())
                case "arc":
                    rx = pdset["rx"]
                    ry = pdset["ry"]
                    x_rotation = pdset["x_rotation"]
                    large_flag = pdset["large_flag"]
                    sweep_flag = pdset["sweep_flag"]           
                    # Calculate the possible centers for an arc
                    # in 'endpoint parameterization'.
                    _x_rot = math.radians(-x_rotation)
                    (solution, (rx, ry)) = arc_end_to_center(
                        last_v, next_v, rx, ry, 
                        x_rotation=_x_rot, correction=True
                    )
                    # Choose one of the two solutions
                    neg_sol = large_flag != sweep_flag
                    v_center, angle1, angle_delta = solution[neg_sol]
                    if ry > rx:
                        rx, ry = ry, rx
                        swap_axis = True
                    else:
                        swap_axis = False
                    e1 = Ellipse(v_center, rx, ry)
                    if sweep_flag:
                        angle1 = angle1 + angle_delta
                        angle_delta = -angle_delta
    
                    d90 = math.radians(90)
                    e1a = Arc(e1, angle1 - swap_axis * d90, 
                                  angle1 + angle_delta - swap_axis * d90)
                    seg = e1a.toShape()
                    if swap_axis:
                        seg.rotate(v_center, Vector(0, 0, 1), 90)
                    _precision = precision_step(DraftPrecision)
                    if abs(x_rotation) > _precision:
                        seg.rotate(v_center, Vector(0, 0, 1), -x_rotation)
                    if sweep_flag:
                        seg.reverse()
                    edges.append(seg)
                    
                case "cbezier":
                    pole1 = pdset["pole1"]
                    pole2 = pdset["pole2"]
                    _precision = precision_step(DraftPrecision + 2)
                    _d1 = pole1.distanceToLine(last_v, next_v)
                    _d2 = pole2.distanceToLine(last_v, next_v)
                    if  _d1 < _precision and _d2 < _precision:
                        # poles and endpints are all on a line
                        _seg = LineSegment(self.last_v, next_v)
                        seg = _seg.toShape()
                    else:
                        b = BezierCurve()
                        b.setPoles([last_v, pole1, pole2, next_v])
                        seg = approx_bspline(b, self.discretization).toShape()
                    edges.append(seg)
                case "qbezier":
                    if equals(last_v, next_v, self.precision):
                        # segment too small - skipping.
                        next_v = last_v
                    else:
                        pole = pdset["pole"]
                        _precision = precision_step(DraftPrecision + 2)
                        _distance = pole.distanceToLine(last_v, next_v)
                        if _distance < _precision:
                            # pole is on the line
                            _seg = LineSegment(last_v, next_v)
                            seg = _seg.toShape()
                        else:
                            b = BezierCurve()
                            b.setPoles([last_v, pole, next_v])
                            seg = approx_bspline(b, self.discretization).toShape()
                        edges.append(seg)
                case _:
                    raise Exception("Illegal path_data type. {}" % pdset["type"])
            last_v = next_v
        return edges
            

@dataclass
class SvgPath(SvgShape):
    d: str
    discretization: int
    precision: int

    @cached_copy
    def to_shape(self) -> Shape | None:
        paths = [s for s in self.shapes()]
        if paths:
            return make_compound(paths)

    @cached_copy_list
    def shapes(self) -> list[Shape]:
        paths: list[SvgSubPath] = []
        commands = iter(PathCommands(self.d))
        path = SvgSubPath(self.discretization, self.precision)
        paths.append(path)
        while True:
            try:
                path.start(commands)
            except PathBreak as ex:
                if ex.end:
                    break
                path = SvgSubPath(self.discretization, self.precision, ex.point)
                paths.append(path)
        if len(paths[-1].path) == 1 and paths[-1].path[0]["type"] == "start":
            # nothing more than the start preamble - delete.
            paths.pop();

        shapes = []
        for sub_path in paths:
            if sub_path.path:
                edges = sub_path.create_Edges()
                sh = make_wire(edges, check_closed=False)
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
