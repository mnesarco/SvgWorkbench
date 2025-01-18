# SPDX-License: LGPL-3.0-or-later
# (c) 2024 Frank David Martínez Muñoz. <mnesarco at gmail.com>

from __future__ import annotations

from ..config import resources, commands, import_pref
from ..vendor.fcapi.lang import QT_TRANSLATE_NOOP, dtr, translate

import FreeCAD as App  # type: ignore


@commands.add(
    label=QT_TRANSLATE_NOOP("SvgWB", "Import Svg"),
    tooltip=QT_TRANSLATE_NOOP("SvgWB", "Import svg file"),
    status_tip=QT_TRANSLATE_NOOP("SvgWB", "Import an svg file into the document"),
    icon=resources.icon("import_svg.svg"),
    transaction=dtr("SvgWB", "Import svg file"),
)
def ImportSvg():
    from pathlib import Path
    from ..preferences import SvgImportPreferences
    from ..vendor.fcapi import fcui as ui
    from ..svg import parser, processor
    from ..vendor.fcapi.preferences import gui_pages

    svg_file = ui.get_open_file(
        translate("SvgWB", "Import svg file"),
        translate("SvgWB", "Svg files (*.svg)"),
    )

    if not svg_file or not Path(svg_file).exists():
        return

    def execute():
        try:
            dialog.page.save()
        except Exception as ex:
            ui.show_error(ex.args[0])
            return

        doc = App.activeDocument() or App.newDocument()
        pref = SvgImportPreferences(dialog.page.selector.selected)
        result = parser.parse(svg_file, pref, 96.0)
        proc = processor.PlainSvgImporter(result, doc)
        proc.execute()

        App.Gui.runCommand("Std_OrthographicCamera", 1)
        App.Gui.SendMsgToActiveView("ViewFit")
        dialog.close()

    with ui.Dialog(translate("SvgWB", "Import Svg"), modal=True, minimumSize=(600, 400)) as dialog:
        pref_ui = gui_pages(import_pref)["Svg"][0]
        margins = (0, 0, 0, 0)
        with ui.Scroll(widgetResizable=True, contentsMargins=margins):
            with ui.Container(contentsMargins=margins):
                dialog.page = pref_ui()
                dialog.page.load()
                ui.Stretch()
        with ui.Container(contentsMargins=margins):
            with ui.Row(contentsMargins=margins):
                ui.Stretch()
                ui.Button(translate("SvgWB", "Cancel"), clicked=lambda: dialog.close())
                ui.Button(translate("SvgWB", "Import"), clicked=execute, default=True)
