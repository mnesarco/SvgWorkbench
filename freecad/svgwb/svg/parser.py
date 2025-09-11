# SPDX-License: LGPL-3.0-or-later
# (c) 2025 Frank David Martínez Muñoz. <mnesarco at gmail.com>

# ruff: noqa: A001

from __future__ import annotations

from dataclasses import dataclass, astuple
from functools import reduce
from pathlib import Path
from typing import TYPE_CHECKING
from hashlib import md5

from xml import sax # nosec B406: parsing will be from defusedxml if available

try:
    from defusedxml.sax import make_parser
except ImportError:
    from xml.sax import make_parser  # nosec B406: parsing will be from defusedxml if available

from .text import SvgText
from .style import SvgColor, SvgStyle
from .options import SvgOptions
from .group import SvgGroup, SvgObject
from .use import SvgUse
from .line import SvgLine
from .rect import SvgRect
from .path import SvgPath
from .index import SvgIndex
from .polyline import SvgPolyLine
from .ellipse import SvgEllipse
from .circle import SvgCircle
from .dimension import SvgDimension
from . import parsers

from FreeCAD import Matrix  # type: ignore

if TYPE_CHECKING:
    from ..preferences import SvgImportPreferences
    from .shape import SvgShape
    from collections.abc import Generator


@dataclass
class StackFrame:
    """Build stack frame."""

    shape: SvgShape | None = None
    options: SvgOptions | None = None
    style: SvgStyle | None = None
    transform: Matrix | None = None


Attrs = dict[str, str]  # Typing


class SvgContentHandler(sax.ContentHandler):
    """
    Svg content handler.
    """

    def __init__(self, preferences: SvgImportPreferences, dpi_fallback: float = 96.0) -> None:
        super().__init__()
        self.stack: list[StackFrame] = []
        self.dpi = dpi_fallback
        self.count = 0
        self.default_style = SvgStyle(
            stroke_color=SvgColor(preferences.line_color()),
            stroke_width=preferences.line_width(),
            fill_color=SvgColor(preferences.fill_color()),
            font_size=preferences.font_size(),
        )
        self.disable_unit_scaling = preferences.disable_unit_scaling()
        self.root: SvgGroup = None
        self.index = SvgIndex()
        self.muted = []
        self.discretization = preferences.edge_approx_points()
        self.precision = preferences.precision()

    def get_id_and_label(self, tag: str, attrs: Attrs) -> tuple[str, str]:
        if not (id := attrs.get("id")):
            id = f"auto_{tag}{self.count}_"
        label = attrs.get("label") or attrs.get("inkscape:label") or id
        return id, label

    def get_transform(self, _tag: str, attrs: Attrs, unit_scaling: Matrix | None = None) -> Matrix:
        transforms: list[Matrix] = []

        if unit_scaling and not (unit_scaling.isNull() or unit_scaling.isUnity()):
            transforms.append(Matrix(unit_scaling))

        if (
            (tr := attrs.get("transform"))
            and (m := parsers.parse_svg_transform(tr))
            and not (m.isNull() or m.isUnity())
        ):
            transforms.append(m)

        return reduce(Matrix.multiply, transforms, Matrix())

    def get_style(self, _tag: str, attrs: Attrs) -> SvgStyle:
        pairs = attrs.get("style", "").split(";")
        pairs = (tuple(v.strip() for v in pair.split(":")) for pair in pairs)
        data = dict(v for v in pairs if len(v) == 2)
        fill_color = data.get("fill")
        stroke_color = data.get("stroke")
        stroke_width = data.get("stroke-width")
        font_size = data.get("font-size")
        if self.stack:
            parent = self.stack[-1].style
        else:
            parent = self.default_style
        style = SvgStyle(*astuple(parent))
        if fill_color:
            if fill_color == "none":
                style.fill_color = None
            else:
                style.fill_color = SvgColor(fill_color)
        else:
            style.fill_color = None
        if stroke_color and stroke_color != "none":
            style.stroke_color = SvgColor(stroke_color)
        if stroke_width and stroke_width != "none":
            style.stroke_width = parsers.parse_size(stroke_width, f"css{self.dpi!s}")
        if font_size:
            style.font_size = parsers.parse_size(font_size, f"css{self.dpi!s}")
        return style

    def get_options(self, tag: str, attrs: Attrs, id_: str, transform: Matrix) -> SvgOptions:
        options = SvgOptions(skip=attrs.get("freecad:skip", False))
        if dim_start := attrs.get("freecad:basepoint1"):
            dim_end = attrs.get("freecad:basepoint2")
            dim_label = attrs.get("freecad:dimpoint")
            x1, y1 = parsers.parse_floats(dim_start)
            x2, y2 = parsers.parse_floats(dim_end)
            x3, y3 = parsers.parse_floats(dim_label)
            options.dimension = SvgDimension(
                tag,
                id_,
                id_,
                transform,
                None,
                None,
                x1,
                y1,
                x2,
                y2,
                x3,
                y3,
            )
        return options

    def get_common(
        self,
        tag: str,
        attrs: Attrs,
        unit_scaling: Matrix | None = None,
    ) -> tuple[str, str, Matrix, SvgStyle, SvgOptions]:
        id, label = self.get_id_and_label(tag, attrs)
        transform = self.get_transform(tag, attrs, unit_scaling)
        style = self.get_style(tag, attrs)
        options = self.get_options(tag, attrs, id, transform)
        return id, label, transform, style, options

    def startElement(self, tag: str, attrs: Attrs) -> None:
        if self.muted:
            self.muted.append(tag)
            return
        if handler := getattr(self, f"start{tag.capitalize()}", None):
            self.count += 1
            handler(tag, attrs)

    def endElement(self, tag: str) -> None:
        if self.muted:
            self.muted.pop()
            return
        if handler := getattr(self, f"end{tag.capitalize()}", None):
            handler(tag)

    def startRootSvg(self, _tag: str, attrs: Attrs) -> None:
        frame = StackFrame(
            options=SvgOptions(),
            style=self.default_style,
            transform=Matrix(),
        )
        self.stack.append(frame)
        if inks_full_ver := attrs.get("inkscape:version"):
            inks_ver_f = parsers.parse_inkscape_version(inks_full_ver)
            # Inkscape before 0.92 used 90 dpi as resolution
            # Newer versions use 96 dpi
            OLD_INKSCAPE_VER = 0.92
            if inks_ver_f < OLD_INKSCAPE_VER:
                self.dpi = 90.0
            else:
                self.dpi = 96.0
        else:  # noqa: PLR5501
            # exact scaling is calculated later below. Here we just want
            # to skip the DPI dialog if a unit is specified in the viewbox
            if (width := attrs.get("width")) and ("mm" in width or "in" in width or "cm" in width):
                self.dpi = 96.0

    def startSvg(self, tag: str, attrs: Attrs) -> None:
        is_root = False
        if not self.stack:
            self.startRootSvg(tag, attrs)
            is_root = True

        unit_scaling = parsers.parse_unit_scaling(
            disable_unit_scaling=self.disable_unit_scaling,
            dpi=self.dpi,
            nested=not is_root,
            attrs=attrs,
        )
        id, label, transform, style, options = self.get_common(tag, attrs, unit_scaling)
        if is_root:
            id = ""
        group = SvgGroup(tag, id, label, transform, style, options)
        self.push(StackFrame(group, options, style, transform))

    def startG(self, tag: str, attrs: Attrs) -> None:
        id, label, transform, style, options = self.get_common(tag, attrs)
        group = SvgGroup(tag, id, label, transform, style, options)
        self.push(StackFrame(group, options, style, transform))

    def startSymbol(self, tag: str, attrs: Attrs) -> None:
        self.startSvg(tag, attrs)

    def startPath(self, tag: str, attrs: Attrs) -> None:
        id, label, transform, style, options = self.get_common(tag, attrs)
        path = SvgPath(
            tag,
            id,
            label,
            transform,
            style,
            options,
            attrs.get("d"),
            self.discretization,
            self.precision,
        )
        self.push(StackFrame(path, options, style, transform))

    def startText(self, tag: str, attrs: Attrs) -> None:
        self.startTspan(tag, attrs)

    def startTspan(self, tag: str, attrs: Attrs) -> None:
        id, label, transform, style, options = self.get_common(tag, attrs)
        parent = self.stack[-1].shape
        if not isinstance(parent, SvgText):
            parent = None
        x, y = parsers.SvgAttrs(attrs, self.dpi).get_size_attrs(x=0, y=0)
        shape = SvgText(tag, id, label, transform, style, options, x, y, parent)
        self.push(StackFrame(shape, options, style, transform))

    def startRect(self, tag: str, attrs: Attrs) -> None:
        id, label, transform, style, options = self.get_common(tag, attrs)
        svg_attrs = parsers.SvgAttrs(attrs, self.dpi)
        x, y, w, h, rx, ry = svg_attrs.get_size_attrs(x=0, y=0, width=0, height=0, rx=0, ry=0)
        shape = SvgRect(
            tag, id, label, transform, style, options, x, y, w, h, rx, ry, self.precision
        )
        self.push(StackFrame(shape, options, style, transform))

    def startLine(self, tag: str, attrs: Attrs) -> None:
        id, label, transform, style, options = self.get_common(tag, attrs)
        svg_attrs = parsers.SvgAttrs(attrs, self.dpi)
        x1, y1, x2, y2 = svg_attrs.get_size_attrs(x1=0, y1=0, x2=0, y2=0)
        shape = SvgLine(tag, id, label, transform, style, options, x1, y1, x2, y2)
        self.push(StackFrame(shape, options, style, transform))

    def startPolyline(self, tag: str, attrs: Attrs) -> None:
        id, label, transform, style, options = self.get_common(tag, attrs)
        svg_attrs = parsers.SvgAttrs(attrs, self.dpi)
        points = svg_attrs.points()
        shape = SvgPolyLine(tag, id, label, transform, style, options, points, False)
        self.push(StackFrame(shape, options, style, transform))

    def startPolygon(self, tag: str, attrs: Attrs) -> None:
        id, label, transform, style, options = self.get_common(tag, attrs)
        svg_attrs = parsers.SvgAttrs(attrs, self.dpi)
        points = svg_attrs.points()
        shape = SvgPolyLine(tag, id, label, transform, style, options, points, True)
        self.push(StackFrame(shape, options, style, transform))

    def startEllipse(self, tag: str, attrs: Attrs) -> None:
        id, label, transform, style, options = self.get_common(tag, attrs)
        svg_attrs = parsers.SvgAttrs(attrs, self.dpi)
        cx, cy, rx, ry = svg_attrs.get_size_attrs(cx=0, cy=0, rx=0, ry=0)
        shape = SvgEllipse(tag, id, label, transform, style, options, cx, cy, rx, ry)
        self.push(StackFrame(shape, options, style, transform))

    def startCircle(self, tag: str, attrs: Attrs) -> None:
        id, label, transform, style, options = self.get_common(tag, attrs)
        svg_attrs = parsers.SvgAttrs(attrs, self.dpi)
        cx, cy, r = svg_attrs.get_size_attrs(cx=0, cy=0, r=0)
        shape = SvgCircle(tag, id, label, transform, style, options, cx, cy, r)
        self.push(StackFrame(shape, options, style, transform))

    def startUse(self, tag: str, attrs: Attrs) -> None:
        id, label, transform, style, options = self.get_common(tag, attrs)
        x, y = parsers.SvgAttrs(attrs, self.dpi).get_size_attrs(x=0, y=0)
        href = attrs.get("xlink:href", "")
        if not href:
            href = attrs.get("href", "")
        href = href.removeprefix("#")
        shape = SvgUse(tag, id, label, transform, style, options, href, x, y, self.index)
        self.push(StackFrame(shape, options, style, transform))

    def characters(self, content: str) -> None:
        if self.muted:
            return
        if self.stack and (text := self.stack[-1].shape) and isinstance(text, SvgText):
            text.append(content)

    def push(self, frame: StackFrame) -> None:
        shape = frame.shape
        if self.stack:
            parent = self.stack[-1]
            if isinstance(parent.shape, SvgGroup) and shape:
                parent.shape.append(shape)
        self.stack.append(frame)
        if shape:
            self.index.add(shape)

    def endPath(self, _tag: str) -> None:
        self.stack.pop()

    def endEllipse(self, _tag: str) -> None:
        self.stack.pop()

    def endCircle(self, _tag: str) -> None:
        self.stack.pop()

    def endUse(self, _tag: str) -> None:
        self.stack.pop()

    def endText(self, _tag: str) -> None:
        self.stack.pop()

    def endTspan(self, _tag: str) -> None:
        self.stack.pop()

    def endRect(self, _tag: str) -> None:
        self.stack.pop()

    def endLine(self, _tag: str) -> None:
        self.stack.pop()

    def endPolygon(self, _tag: str) -> None:
        self.stack.pop()

    def endPolyline(self, _tag: str) -> None:
        self.stack.pop()

    def endG(self, _tag: str) -> None:
        self.stack.pop()

    def endSymbol(self, _tag: str) -> None:
        self.stack.pop()

    def endSvg(self, _tag: str) -> None:
        self.root = self.stack.pop().shape

    def startMarker(self, tag: str, _attrs: Attrs) -> None:
        self.muted.append(tag)


@dataclass
class SvgParseResult:
    """
    Results from parsing svg.
    """

    root: SvgGroup
    index: SvgIndex
    hash: str

    def objects(self) -> Generator[SvgObject, None, None]:
        """Return a flat generator with all parsed svg objects."""
        if origin := self.index.find("freecad_origin"):
            shape = origin.to_shape()
            if shape:
                vec = shape.CenterOfGravity * -1
                for obj in self.root.objects:
                    base = obj.shape
                    if isinstance(base, SvgGroup) or obj.id == "freecad_origin":
                        continue
                    base.transform.move(vec)
                    yield obj
                return

        for obj in self.root.objects:
            if not isinstance(obj.shape, SvgGroup):
                yield obj


def parse(
    filename: str | Path,
    preferences: SvgImportPreferences,
    dpi_fallback: float = 96.0,
) -> SvgParseResult:
    parser = make_parser()  # nosec: defusedxml version used if available, # noqa: S317
    parser.setFeature(sax.handler.feature_external_ges, False)  # noqa: FBT003
    handler = SvgContentHandler(preferences, dpi_fallback)
    parser.setContentHandler(handler)

    BUFFER_SIZE = 4096
    hasher = md5(usedforsecurity=False)
    with Path(filename).open("rb") as f:
        while data := f.read(BUFFER_SIZE):
            hasher.update(data)
    file_hash = hasher.hexdigest()

    with Path(filename).open(encoding="utf-8") as f:
        parser.parse(f)

    return SvgParseResult(handler.root, handler.index, file_hash)
