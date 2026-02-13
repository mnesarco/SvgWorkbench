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

from .topology import get_face_normal

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


def copy_selection(*, sub_elements: bool = False) -> None:
    from freecad.svgwb.svg.export import export
    from freecad.svgwb.config import export_pref, SvgExportPreferences

    if "Clipboard" in export_pref.preset_names():
        export_pref = SvgExportPreferences("Clipboard")
    else:
        export_pref = SvgExportPreferences("Clipboard", copy_from=export_pref)
        export_pref.direction(update="Camera")
        export_pref.hairline_effect(update=True)

    if sub_elements:
        objects = App.Gui.Selection.getSelectionEx()
    else:
        objects = App.Gui.Selection.getSelection()

    is_single_face = (
        sub_elements
        and len(objects) == 1
        and len(objects[0].SubElementNames) == 1
        and objects[0].SubElementNames[0].startswith("Face")
    )

    if is_single_face:
        normal = get_face_normal(objects[0].Object.Shape.getElement(objects[0].SubElementNames[0]))
    else:
        normal = None

    file = Path(gettempdir()) / f"_clipboard_{hex(int(time.time()))}.svg"
    export(str(file), objects, export_pref, normal)

    if file.exists():
        clipboard = QApplication.clipboard()
        mime_data = QMimeData()
        for fmt in SVG_MIME_FORMATS:
            mime_data.setData(fmt, file.read_bytes())
        clipboard.setMimeData(mime_data)
