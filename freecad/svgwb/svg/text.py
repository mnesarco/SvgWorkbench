# SPDX-License: LGPL-3.0-or-later
# (c) 2025 Frank David Martínez Muñoz. <mnesarco at gmail.com>

from __future__ import annotations

from dataclasses import dataclass

from FreeCAD import Vector, Placement, Document, DocumentObject  # type: ignore

from .shape import SvgShape


@dataclass
class SvgText(SvgShape):
    x: float
    y: float
    parent: SvgText | None = None

    def __post_init__(self):
        self._raw_text = []
        self._children = []
        if self.parent:
            self.parent._children.append(self)

    def to_text(self, doc: Document):
        text = []
        text.extend(self._raw_text)
        for sub in self._children:
            text.extend(sub._raw_text)

        text_lines = [s.strip() for s in text]
        if not text_lines:
            return

        from draftobjects.text import Text  # type: ignore

        placement = Placement()
        placement.Rotation.Q = (0.0, 0.0, 0.0, 1.0)
        x, y = self.x, self.y
        placement.Base = self.transform.multiply(Vector(x, -y, 0))
        obj = doc.addObject("App::FeaturePython", self.id)
        Text(obj)
        obj.Text = text_lines
        obj.Placement = placement
        return obj

    def append(self, content: str):
        self._raw_text.append(content)

    def apply_style(self, obj: DocumentObject):
        from draftviewproviders.view_text import ViewProviderText  # type: ignore

        vo = obj.ViewObject
        ViewProviderText(vo)
        if self.style.font_size:
            vo.FontSize = self.style.font_size
        if self.style.fill_color:
            vo.TextColor = self.style.fill_color.as_tuple()
        if self.style.stroke_color:
            vo.LineColor = self.style.stroke_color.as_tuple()
        if self.style.stroke_width:
            vo.LineWidth = self.style.stroke_width
