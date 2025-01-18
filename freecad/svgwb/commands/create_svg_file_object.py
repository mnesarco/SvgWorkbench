# SPDX-License: LGPL-3.0-or-later
# (c) 2024 Frank David Martínez Muñoz. <mnesarco at gmail.com>

from __future__ import annotations

from pathlib import Path
from ..config import resources, commands
from ..vendor.fcapi.lang import QT_TRANSLATE_NOOP, translate

import FreeCAD as App  # type: ignore


@commands.add(
    label=QT_TRANSLATE_NOOP("SvgWB", "New Svg File Source"),
    tooltip=QT_TRANSLATE_NOOP("SvgWB", "Create an svg source form an external svg file"),
    status_tip=QT_TRANSLATE_NOOP("SvgWB", "Create an svg source form an external svg file"),
    icon=resources.icon("add-svg-db.svg"),
)
class NewSvgFileObject:
    def on_activated(self) -> None:
        from ..features.svg_file import SvgFileFeature
        from ..vendor.fcapi import fcui as ui

        obj = SvgFileFeature.create(name="SvgImport")

        svg_file = ui.get_open_file(
            translate("SvgWB", "Import svg file"),
            translate("SvgWB", "Svg files (*.svg)"),
        )

        if not svg_file:
            return

        svg_file = Path(svg_file)
        if svg_file.exists():
            obj.ExternalFile = str(svg_file)
            obj.Label = svg_file.name
            obj.recompute()

    def is_active(self) -> bool:
        return bool(App.GuiUp and App.activeDocument())
