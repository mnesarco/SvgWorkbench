# SPDX-License: LGPL-3.0-or-later
# (c) 2024 Frank David Martínez Muñoz. <mnesarco at gmail.com>

from __future__ import annotations

from ..config import resources, commands
from ..vendor.fcapi.lang import QT_TRANSLATE_NOOP
from ..utils import clipboard

import FreeCAD as App  # type: ignore


@commands.add(
    label=QT_TRANSLATE_NOOP("SvgWB", "Paste Svg as Svg source"),
    tooltip=QT_TRANSLATE_NOOP("SvgWB", "Paste SVG geometry from clipboard"),
    status_tip=QT_TRANSLATE_NOOP("SvgWB", "Paste SVG geometry from clipboard"),
    icon=resources.icon("paste.svg"),
    accel="Alt+Ctrl+V",
)
class PasteSvgFileObject:
    """Create an svg source form the clipboard."""

    def on_activated(self) -> None:
        mime = clipboard.find_format()
        if not mime:
            return

        svg_file = clipboard.get_data_as_file(mime)

        from ..features.svg_file import SvgFileFeature

        obj = SvgFileFeature.create(name="SvgImport")
        obj.ExternalFile = str(svg_file)
        obj.Label = svg_file.name
        obj.recompute()

    def is_active(self) -> bool:
        return bool(App.GuiUp and App.activeDocument() and clipboard.find_format())
