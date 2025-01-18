# SPDX-License: LGPL-3.0-or-later
# (c) 2025 Frank David Martínez Muñoz. <mnesarco at gmail.com>

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from FreeCAD import Matrix, DocumentObject  # type: ignore
    from Part import Shape  # type: ignore

from .style import SvgStyle
from .options import SvgOptions

@dataclass
class SvgShape:
    tag: str
    id: str
    label: str
    transform: Matrix
    style: SvgStyle
    options: SvgOptions

    def to_shape(self) -> Shape | None:
        return None

    def apply_style(self, obj: DocumentObject):
        vo = obj.ViewObject
        if self.style.stroke_color:
            vo.LineColor = self.style.stroke_color.as_tuple()
        if self.style.stroke_width:
            vo.LineWidth = self.style.stroke_width
        if self.style.fill_color:
            appearance = vo.ShapeAppearance[0]
            appearance.DiffuseColor = self.style.fill_color.as_tuple()
            vo.ShapeAppearance = appearance
            # vo.ShapeColor = self.style.fill_color.as_tuple()
