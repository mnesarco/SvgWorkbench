# SPDX-License: LGPL-3.0-or-later
# (c) 2024 Frank David Martínez Muñoz. <mnesarco at gmail.com>

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..preferences import SvgExportPreferences
from ..config import resources, commands, export_pref
from ..vendor.fcapi.lang import QT_TRANSLATE_NOOP, translate

import FreeCAD as App  # type: ignore


@dataclass
class LastExport:
    file: str | None = None
    pref: SvgExportPreferences | None = None


_last_export = LastExport()


@commands.add(
    label=QT_TRANSLATE_NOOP("SvgWB", "Export Svg"),
    tooltip=QT_TRANSLATE_NOOP("SvgWB", "Export selection to svg"),
    status_tip=QT_TRANSLATE_NOOP("SvgWB", "Export selection to svg"),
    icon=resources.icon("export_svg.svg"),
)
class ExportSvg:
    def on_activated(self):
        from ..svg import export
        from ..vendor.fcapi import fcui as ui
        from ..vendor.fcapi.preferences import gui_pages

        svg_file = ui.get_save_file(
            QT_TRANSLATE_NOOP("SvgWB", "Export svg file"),
            QT_TRANSLATE_NOOP("SvgWB", "Svg files (*.svg)"),
        )

        if not svg_file:
            return

        def execute():
            try:
                dialog.page.save()
            except Exception as ex:
                ui.show_error(ex.args[0])
                raise

            with ui.progress_indicator(translate("SvgWB", "Exporting svg")):
                pref = SvgExportPreferences(dialog.page.selector.selected)
                try:
                    export.export(svg_file, App.Gui.Selection.getSelection(), pref)
                except Exception as ex:
                    ui.show_error(ex.args[0])
                    raise
                dialog.close()
                _last_export.file = svg_file
                _last_export.pref = pref

        with ui.Dialog(
            translate("SvgWB", "Export svg file"), modal=True, minimumSize=(600, 400)
        ) as dialog:
            pref_ui = gui_pages(export_pref)["Svg"][0]
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
                    ui.Button(translate("SvgWB", "Export"), clicked=execute, default=True)

    def is_active(self):
        return bool(
            App.GuiUp
            and App.activeDocument()
            and App.Gui.activeView()
            and App.Gui.Selection.getSelection()
        )


@commands.add(
    label=QT_TRANSLATE_NOOP("SvgWB", "Export Svg with last file and preferences"),
    tooltip=QT_TRANSLATE_NOOP("SvgWB", "Export selection to svg"),
    status_tip=QT_TRANSLATE_NOOP("SvgWB", "Export selection to svg"),
    icon=resources.icon("re-export_svg.svg"),
)
class ReExportSvg:
    def on_activated(self):
        from ..svg import export
        from ..vendor.fcapi import fcui as ui

        if _last_export.file is None:
            App.Gui.runCommand("SvgWB_ExportSvg", 0)
            return

        pref = _last_export.pref
        svg_file = _last_export.file

        if Path(svg_file).exists() and not ui.confirm(
            translate("SvgWB", "Override {}?".format(svg_file))
        ):
            return

        with ui.progress_indicator(translate("SvgWB", "Exporting svg")):
            try:
                export.export(svg_file, App.Gui.Selection.getSelection(), pref)
            except Exception as ex:
                ui.show_error(ex.args[0])
                raise

    def is_active(self):
        return bool(
            App.GuiUp
            and App.activeDocument()
            and App.Gui.activeView()
            and App.Gui.Selection.getSelection()
        )
