# SPDX-License: LGPL-3.0-or-later
# (c) 2025 Frank David Martínez Muñoz. <mnesarco at gmail.com>

# ruff: noqa: N806

from __future__ import annotations

import re
import math
from FreeCAD import Matrix, Vector  # type: ignore
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator


SvgUnits = {
    "mm90.0": {
        "": 25.4 / 90,  # default
        "px": 25.4 / 90,
        "pt": 4.0 / 3 * 25.4 / 90,
        "pc": 15 * 25.4 / 90,
        "mm": 1.0,
        "cm": 10.0,
        "in": 25.4,
        "em": 15 * 2.54 / 90,
        "ex": 10 * 2.54 / 90,
        "%": 100,
    },
    "mm96.0": {
        "": 25.4 / 96,  # default
        "px": 25.4 / 96,
        "pt": 4.0 / 3 * 25.4 / 96,
        "pc": 15 * 25.4 / 96,
        "mm": 1.0,
        "cm": 10.0,
        "in": 25.4,
        "em": 15 * 2.54 / 96,
        "ex": 10 * 2.54 / 96,
        "%": 100,
    },
    "css90.0": {
        "": 1.0,  # default
        "px": 1.0,
        "pt": 4.0 / 3,
        "pc": 15,
        "mm": 90.0 / 25.4,
        "cm": 90.0 / 2.54,
        "in": 90,
        "em": 15,
        "ex": 10,
        "%": 100,
    },
    "css96.0": {
        "": 1.0,  # default
        "px": 1.0,
        "pt": 4.0 / 3,
        "pc": 15,
        "mm": 96.0 / 25.4,
        "cm": 96.0 / 2.54,
        "in": 96,
        "em": 15,
        "ex": 10,
        "%": 100,
    },
}


_FLOAT_RE = re.compile(r"([-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?)")
_CONTENT_SPLIT_RE = re.compile(r",|\s+")
_INK_VERSION_RE = re.compile(r"\d+\.\d+")


class SvgQuantity:
    """Float quantity with units."""

    _num = _FLOAT_RE.pattern
    _unit = "(px|pt|pc|mm|cm|in|em|ex|%)?"
    _full_num = re.compile(_num + _unit)

    number: float
    exponent: str
    unit: str

    def __init__(self, value: str) -> None:
        """Parse quantity with units."""
        number, exponent, unit = self._full_num.findall(value)[0]
        self.number = float(number)
        self.exponent = exponent
        self.unit = unit

    def __iter__(self) -> re.Iterator[float | str]:
        """Expand as tuple"""
        return iter((self.number, self.exponent, self.unit))


class SvgTransformations:
    """Svg transform parser."""

    _op = "(matrix|translate|scale|rotate|skewX|skewY)"
    _val = "\\((.*?)\\)"
    _transf = _op + "\\s*?" + _val
    regex = re.compile(_transf, re.DOTALL)

    def __init__(self, text: str) -> None:
        """Parse svg transformation."""
        ops = []
        for op, args in self.regex.findall(text):
            _args = [float(v) for (v, e) in _FLOAT_RE.findall(args)]
            ops.append((op, _args))
        self.ops = ops

    def __iter__(self) -> Iterator[tuple[str, list[float]]]:
        """Retrieve all parsed transformations."""
        return iter(self.ops)


def parse_floats(text: str) -> list[float]:
    return [float(v) for v, _exp in _FLOAT_RE.findall(text)]


def parse_inkscape_version(text: str) -> float:
    inks_ver_pars = _INK_VERSION_RE.search(text)
    if inks_ver_pars is not None:
        return float(inks_ver_pars.group(0))
    return 99.99


def content_split(content: str) -> list[str]:
    return _CONTENT_SPLIT_RE.split(content)


def style_split(content: str) -> list[tuple[str, str]]:
    rules = (term.split(":") for term in content.split(";"))
    return [(term[0].strip(), term[1].strip()) for term in rules if len(term) > 1]


def parse_svg_transform(tr: str) -> Matrix:
    """
    Return a FreeCAD matrix from an SVG transform attribute.

    Parameters
    ----------
    tr : str
        The type of transform: 'matrix', 'translate', 'scale',
        'rotate', 'skewX', 'skewY' and its value

    Returns
    -------
    Base::Matrix4D
        The translated matrix.

    """
    m = Matrix()
    for transformation, args in SvgTransformations(tr):
        if transformation == "translate":
            tx = args[0]
            ty = args[1] if len(args) > 1 else 0.0
            m.move(Vector(tx, -ty, 0))

        elif transformation == "scale":
            sx = args[0]
            sy = args[1] if len(args) > 1 else sx
            m.scale(Vector(sx, sy, 1))

        elif transformation == "rotate":
            cx = 0
            cy = 0
            angle = args[0]
            if len(args) >= 3:  # noqa: PLR2004
                # Rotate around a non-origin center point
                # (note: SVG y axis is opposite FreeCAD y axis)
                cx = args[1]
                cy = args[2]
                m.move(Vector(-cx, cy, 0))  # Reposition for rotation
            # Mirroring one axis is equal to changing the direction
            # of rotation
            m.rotateZ(math.radians(-angle))
            if len(args) >= 3:  # noqa: PLR2004
                m.move(Vector(cx, -cy, 0))  # Reverse repositioning

        elif transformation == "skewX":
            # fmt: off
            C = math.tan(math.radians(args[0]))
            _m = Matrix(
                1, -C, 0, 0,
                0,  1, 0, 0,
                0,  0, 1, 0,
                0,  0, 0, 1,
            )
            m = m.multiply(_m)
            # fmt: on

        elif transformation == "skewY":
            # fmt: off
            B = math.tan(math.radians(args[0]))
            _m = Matrix(
                 1, 0, 0, 0,
                -B, 1, 0, 0,
                 0, 0, 1, 0,
                 0, 0, 0, 1,
            )
            m = m.multiply(_m)
            # fmt: on

        elif transformation == "matrix":
            # fmt: off
            # transformation matrix:
            #    FreeCAD                 SVG
            # (+A -C +0 +E)           (A C 0 E)
            # (-B +D -0 -F)  = (-Y) * (B D 0 F) * (-Y)
            # (+0 -0 +1 +0)           (0 0 1 0)
            # (+0 -0 +0 +1)           (0 0 0 1)
            #
            # Put the first two rows of the matrix
            A, B, C, D, E, F, *_ = args
            _m = Matrix(
                 A, -C,  0,  E,
                -B,  D,  0, -F,
                 0,  0,  1,  0,
                 0,  0,  0,  1,
            )
            m = m.multiply(_m)
            # fmt: on
    return m


def parse_unit_scaling(
    *,
    disable_unit_scaling: bool,
    dpi: float,
    nested: bool,
    attrs: dict[str, str],
) -> Matrix:
    m = Matrix()
    if not disable_unit_scaling:
        width = attrs.get("width")
        height = attrs.get("height")
        viewBox = attrs.get("viewBox")
        if width and height and viewBox:
            if nested:
                unit_mode = "css" + str(dpi)
            else:
                unit_mode = "mm" + str(dpi)
            viewBox = content_split(viewBox)
            vbw = parse_size(viewBox[2], "discard")
            vbh = parse_size(viewBox[3], "discard")
            abw = parse_size(width, unit_mode)
            abh = parse_size(height, unit_mode)
            sx = abw / vbw
            sy = abh / vbh
            preserveAspectRatio = attrs.get("preserveAspectRatio", "").lower()
            uniform_scaling = round(sx / sy, 5) == 1
            if uniform_scaling or preserveAspectRatio.startswith("none"):
                m.scale(Vector(sx, sy, 1))
            else:
                # preserve the aspect ratio
                if preserveAspectRatio.endswith("slice"):
                    sxy = max(sx, sy)
                else:
                    sxy = min(sx, sy)
                m.scale(Vector(sxy, sxy, 1))
        elif not nested:
            # fallback to current dpi
            m.scale(Vector(25.4 / dpi, 25.4 / dpi, 1))
    return m


def parse_size(
    length: str,
    mode: str = "discard",
    base: float = 1,
) -> float | tuple[float, str] | bool:
    """
    Parse the length string containing number and unit.

    Parameters
    ----------
    length : str
        The length is a string, including sign, exponential notation,
        and unit: '+56215.14565E+6mm', '-23.156e-2px'.
    mode : str, optional
        One of 'discard', 'tuple', 'css90.0', 'css96.0', 'mm90.0', 'mm96.0'.
        'discard' (default), it discards the unit suffix, and extracts
            a number from the given string.
        'tuple', return number and unit as a tuple
        'css90.0', convert the unit to pixels assuming 90 dpi
        'css96.0', convert the unit to pixels assuming 96 dpi
        'mm90.0', convert the unit to millimeters assuming 90 dpi
        'mm96.0', convert the unit to millimeters assuming 96 dpi
    base : float, optional
        A base to scale the length.

    Returns
    -------
    float
        The numeric value of the length, as is, or transformed to
        millimeters or pixels.
    float, string
        A tuple with the numeric value, and the unit if `mode='tuple'`.

    """
    # Dictionaries to convert units to millimeters or pixels.
    #
    # The `em` and `ex` units are typographical units used in systems
    # like LaTeX. Here the conversion factors are arbitrarily chosen,
    # as they should depend on a specific font size used.
    #
    # The percentage factor is arbitrarily chosen, as it should depend
    # on the viewport size or for filling patterns on the bounding box.
    units = SvgUnits.get(mode)
    # Extract a number from a string like '+56215.14565E+6mm'
    number, _exp, unit = SvgQuantity(length)
    if mode == "discard":
        return number
    if mode == "tuple":
        return number, unit
    if mode == "isabsolute":
        return unit in ("mm", "cm", "in", "px", "pt")
    if mode in ("mm96.0", "mm90.0"):
        return number * units[unit]
    if mode in ("css96.0", "css90.0"):
        if unit != "%":
            return number * units[unit]
        return number * base
    msg = f"Invalid mode {mode}"
    raise ValueError(msg)


class SvgAttrs:
    """Attribute parser."""

    def __init__(self, attrs: dict[str, str], dpi: float, base: float = 1) -> None:
        """Create attribute parser."""
        self.attrs = attrs
        self.mode = f"css{dpi!s}"
        self.base = base

    def get_size_attrs(self, **kw) -> Iterator[float]:
        """Parse size based attributes."""
        data = self.attrs.get
        mode = self.mode
        base = self.base
        for k, d in kw.items():
            if (v := data(k)) is None:
                yield d
            else:
                yield parse_size(v, mode, base)

    def points(self) -> list[float]:
        """Parse points attribute if present."""
        if points := self.attrs.get("points"):
            return parse_floats(points)
        return []
