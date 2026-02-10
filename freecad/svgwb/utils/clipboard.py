# SPDX-License: LGPL-3.0-or-later
# (c) 2026 Frank David Martínez Muñoz. <mnesarco at gmail.com>

from typing import TYPE_CHECKING
from pathlib import Path
from tempfile import gettempdir
import time

if TYPE_CHECKING:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QByteArray, QMimeData
else:
    from PySide.QtGui import QApplication
    from PySide.QtCore import QByteArray, QMimeData

import FreeCAD as App

SVG_MIME_FORMATS = ["image/x-inkscape-svg", "image/svg+xml"]


def find_format(mime_formats: list[str] | None = None) -> str | None:
    if mime_formats is None:
        mime_formats = SVG_MIME_FORMATS
    clipboard = QApplication.clipboard()
    mime_data = clipboard.mimeData()
    for fmt in mime_formats:
        if mime_data.hasFormat(fmt):
            return fmt
    return None


def get_data_as_file(mime_format: str) -> Path:
    clipboard = QApplication.clipboard()
    mime_data = clipboard.mimeData()
    raw_data: QByteArray = mime_data.data(mime_format)
    file = Path(gettempdir()) / f"_clipboard_{hex(int(time.time()))}.svg"
    file.write_bytes(raw_data.data())
    return file


def copy_selection() -> None:
    from freecad.svgwb.svg.export import export
    from freecad.svgwb.config import export_pref, SvgExportPreferences

    if "Clipboard" in export_pref.preset_names():
        export_pref = SvgExportPreferences("Clipboard")
    else:
        export_pref = SvgExportPreferences("Clipboard", copy_from=export_pref)
        export_pref.direction(update="Camera")
        export_pref.hairline_effect(update=True)

    file = Path(gettempdir()) / f"_clipboard_{hex(int(time.time()))}.svg"
    export(str(file), App.Gui.Selection.getSelection(), export_pref)

    if file.exists():
        clipboard = QApplication.clipboard()
        mime_data = QMimeData()
        mime_data.setData("image/svg+xml", file.read_bytes())
        clipboard.setMimeData(mime_data)
