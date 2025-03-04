# SPDX-License: LGPL-3.0-or-later
# (c) 2025 Frank David Martínez Muñoz. <mnesarco at gmail.com>

# ruff: noqa: S314

from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from itertools import chain
from typing import TypeAlias, TYPE_CHECKING

import FreeCAD as App  # type: ignore
from FreeCAD import BoundBox, DocumentObject, Matrix, Rotation, Vector  # type: ignore
from Part import Edge, LineSegment, Shape, makeBox  # type: ignore
from TechDraw import project  # type: ignore
from TechDraw import projectToSVG as project_to_svg  # type: ignore

from ..preferences import SvgExportPreferences
from ..vendor.fcapi.fcui import Color
from ..vendor.fcapi.lang import translate
from . import parsers

if TYPE_CHECKING:
    from pathlib import Path
    from collections.abc import Iterable

Degrees: TypeAlias = float


def get_camera_direction() -> tuple[Vector, Degrees]:
    view = App.Gui.ActiveDocument.ActiveView
    up = view.getUpDirection()
    direction = view.getViewDirection().negative()
    spy = LineSegment(Vector(0, 0, 0), up * 20).toShape()
    shapes: Iterable[Shape] = project(spy, direction)
    e: Edge = next(chain.from_iterable(s.Edges for s in shapes if s.isValid()), None)
    MIN_LEN = 1e-6
    if e and e.Length > MIN_LEN:
        vec = e.lastVertex().CenterOfGravity
        if vec.Length < MIN_LEN:
            vec = e.firstVertex().CenterOfGravity
        y_axis = Vector(0, 1, 0)
        v_angle = vec.getAngle(y_axis)
        angle = -math.copysign(1, vec.x) * v_angle
    else:
        angle = 0
    return direction, round(math.degrees(angle), 6)


def get_direction(pref: SvgExportPreferences) -> tuple[Vector, Matrix, Degrees]:
    dir_s = pref.direction()
    if dir_s == "Camera":
        direction, angle = get_camera_direction()
        return direction, Matrix(), angle

    vals = [round(v, 6) for v in parsers.parse_floats(dir_s)]
    m = Matrix()
    match vals:
        case (x, y, z) if x != 0 and y != 0 and z != 0:
            m.rotateX(math.radians(-90))
            direction = Vector(x, y, z)
        case (x, y, -1):
            m.rotateZ(math.radians(180))
            direction = Vector(x, y, z)
        case (x, y, 0) if abs(y) == 1:
            m.rotateY(math.radians(90))
            direction = Vector(x, y, z)
        case (x, y, 0) if abs(x) == 1:
            m.rotateX(math.radians(90))
            direction = Vector(x, y, z)
        case (x, y, z):
            direction = Vector(x, y, z)
        case _:
            direction = Vector(0, 0, 1)
    return direction.normalize(), m, 0


def project_bounding_box(bb: BoundBox, direction: Vector, rotation: Degrees) -> BoundBox:
    x, y, z = bb.XMax - bb.XMin, bb.YMax - bb.YMin, bb.ZMax - bb.ZMin
    box = makeBox(max(x, 1), max(y, 1), max(z, 1))
    box.Placement.Base = Vector(bb.XMin, bb.YMin, bb.ZMin)
    box_p = project(box, direction)
    bb2 = BoundBox()
    m = Matrix()
    if rotation:
        m = Rotation(Axis=direction.cross(Vector(0, 0, 1)), Degree=rotation).toMatrix()
    for s in box_p:
        if s and not s.isNull() and s.isValid():
            bb2.add(s.transformed(m).BoundBox)
    return bb2


def export(
    filename: str | Path,
    objects: list[DocumentObject],
    preferences: SvgExportPreferences | None = None,
) -> None:
    pref = preferences or SvgExportPreferences()
    translated = pref.transform() == 0
    scale: float = pref.scale()
    direction, matrix, rotation = get_direction(pref)
    shapes, bb = get_shapes(objects, matrix)
    bb = project_bounding_box(bb, direction, rotation)

    (min_x, min_y), (max_x, max_y), (size_x, size_y) = get_dimensions(bb, with_margins=translated)

    # TODO: Determine the correct viewbox

    if translated:
        # translated-style exports have the viewbox starting at X=0, Y=0
        viewbox = f"0 0 {size_x:.6f} {size_y:.6f}"
        transform = f"translate({-min_x:.6f},{max_y:.6f})"
        if rotation:
            transform = f"rotate({rotation:.6f}) {transform}"
        if scale:
            transform = f"{transform} scale({scale:.6f},{scale:.6f})"
    else:
        # Raw-style exports have the viewbox starting at X=xmin, Y=-ymax
        # We need the negative Y here because SVG is upside down, and we
        # flip the sketch right-way up with a scale later
        viewbox = f"{min_x:.6f} {-max_y:.6f} {size_x:.6f} {size_y:.6f}"
        if scale:
            transform = f"scale({scale:.6f},{scale:.6f})"
        else:
            transform = "scale(1,-1)"

    svg = ET.Element(
        "svg",
        width=f"{size_x:.6f}mm",
        height=f"{size_y:.6f}mm",
        viewBox=viewbox,
        version="1.1",
        xmlns="http://www.w3.org/2000/svg",
    )

    # Fake inkscape version
    svg.set("xmlns:inkscape", "http://www.inkscape.org/namespaces/inkscape")
    svg.set("inkscape:version", "1.4 (e7c3feb100, 2024-10-09)")

    v_color, v_alpha = Color(pref.visible_line_color()).rgb_and_alpha()
    v_width = pref.visible_line_width()
    non_scaling = pref.hairline_effect()

    visible_style = {
        "stroke": v_color,
        "stroke-opacity": f"{v_alpha / 255.0}",
        "stroke-width": f"{v_width}mm",
        "stroke-linecap": "butt",
        "stroke-linejoin": "miter",
        "fill": "none",
    }

    if non_scaling:
        visible_style["vector-effect"] = "non-scaling-stroke"

    v_color, v_alpha = Color(pref.hidden_line_color()).rgb_and_alpha()
    v_width = pref.hidden_line_width()
    v_dash = pref.hidden_line_style()

    hidden_style = {
        "stroke": v_color,
        "stroke-width": f"{v_width}mm",
        "stroke-opacity": f"{v_alpha / 255.0}",
        "stroke-dasharray": v_dash,
        "stroke-linecap": "butt",
        "stroke-linejoin": "miter",
        "fill": "none",
    }

    if non_scaling:
        hidden_style["vector-effect"] = "non-scaling-stroke"

    type_ = "ShowHiddenLines" if pref.show_hidden_lines() else "NoHiddenLines"

    def generate(shape: Shape) -> str:
        code = project_to_svg(
            shape,
            direction=direction,
            type=type_,
            vStyle=visible_style,
            v0Style=visible_style,
            v1Style=visible_style,
            hStyle=hidden_style,
            h0Style=hidden_style,
            h1Style=hidden_style,
        )
        return f"<generated>{code}</generated>"

    # Write paths
    for shape, name, label in shapes:
        g = ET.SubElement(svg, "g", id=name)
        g.set("inkscape:label", label)
        g.set("transform", transform)
        code = generate(shape)
        elements = ET.fromstring(code)
        for elem in elements:
            if non_scaling:
                add_hairline_effect(elem)
            g.append(elem)

    if not filename.strip().lower().endswith(".svg"):
        filename = f"{filename!s}.svg"

    tree = ET.ElementTree(svg)
    tree.write(
        filename,
        encoding="UTF-8",
        xml_declaration=True,
        method="xml",
    )


def get_shapes(
    objects: list[DocumentObject],
    matrix: Matrix,
) -> tuple[list[tuple[Shape, str, str]], BoundBox]:
    bb = BoundBox()
    shapes = []
    for obj in objects:
        label = obj.Label.replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
        shape: Shape
        if shape := getattr(obj, "Shape", None):
            shape = shape.transformed(matrix)
            shapes.append((shape, obj.Name, label))
            if (sbb := shape.BoundBox) and sbb.isValid():
                bb.add(sbb)
    return shapes, bb


def add_hairline_effect(elem: ET.Element) -> None:
    for sub in elem.iter():
        if "vector-effect" not in sub.attrib:
            sub.set("vector-effect", "non-scaling-stroke")
            sub.set("style", "-inkscape-stroke:hairline;vector-effect:non-scaling-stroke")


def get_dimensions(
    bb: BoundBox,
    *,
    with_margins: bool,
) -> tuple[tuple[float, float], tuple[float, float], tuple[float, float]]:
    """
    Determine the size of the page by adding the bounding boxes of all shapes
    """
    if not bb.isValid():
        msg = translate("SvgWB", "The export list contains no object with a valid bounding box")
        raise ValueError(msg)

    min_x = bb.XMin
    max_x = bb.XMax
    min_y = bb.YMin
    max_y = bb.YMax

    if with_margins:
        # translated-style exports get a bit of a margin
        margin = (max_x - min_x) * 0.01
    else:
        # raw-style exports get no margin
        margin = 0

    min_x -= margin
    max_x += margin
    min_y -= margin
    max_y += margin
    size_x = max_x - min_x
    size_y = max_y - min_y
    min_y += margin

    return (min_x, min_y), (max_x, max_y), (size_x, size_y)
