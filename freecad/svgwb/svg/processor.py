# SPDX-License: LGPL-3.0-or-later
# (c) 2025 Frank David Martínez Muñoz. <mnesarco at gmail.com>

from .parser import SvgParseResult
from .text import SvgText

import FreeCAD as App  # type: ignore
from FreeCAD import Document  # type: ignore


class PlainSvgImporter:
    def __init__(self, svg: SvgParseResult, doc: Document):
        self.svg = svg
        self.doc = doc

    def execute(self):
        view = App.GuiUp
        doc = self.doc
        for svg_obj in self.svg.objects():
            obj = None
            source = svg_obj.shape
            if isinstance(source, SvgText):
                obj = source.to_text(doc)
            elif shape := source.to_shape():
                obj = doc.addObject("Part::Feature", svg_obj.id)
                obj.Shape = shape

            if obj:
                obj.addProperty("App::PropertyString", "SvgPath", "Svg")
                obj.addProperty("App::PropertyString", "SvgId", "Svg")
                obj.addProperty("App::PropertyString", "SvgLabel", "Svg")
                obj.addProperty("App::PropertyString", "SvgHref", "Svg")
                obj.addProperty("App::PropertyString", "SvgTag", "Svg")
                obj.SvgPath = svg_obj.path or ""
                obj.SvgId = svg_obj.id or ""
                obj.SvgLabel = source.label or ""
                obj.SvgHref = svg_obj.href or ""
                obj.SvgTag = source.tag or ""
                obj.Label = source.label or ""
                for prop in ("SvgPath", "SvgId", "SvgLabel", "SvgHref", "SvgTag"):
                    obj.setPropertyStatus(prop, "ReadOnly")
                if view:
                    source.apply_style(obj)
