# SPDX-License: LGPL-3.0-or-later
# (c) 2024 Frank David Martínez Muñoz. <mnesarco at gmail.com>

from __future__ import annotations

from ..config import resources, commands
from ..vendor.fcapi.lang import QT_TRANSLATE_NOOP
from ..utils import clipboard

import FreeCAD as App  # type: ignore


@commands.add(
    label=QT_TRANSLATE_NOOP("SvgWB", "Copy objects as SVG"),
    tooltip=QT_TRANSLATE_NOOP("SvgWB", "Copy objects as SVG to clipboard"),
    status_tip=QT_TRANSLATE_NOOP("SvgWB", "Copy objects as SVG to clipboard"),
    icon=resources.icon("copy.svg"),
    accel="Alt+Ctrl+C",
)
class CopySvg:
    """Copy as svg."""

    def on_activated(self) -> None:
        clipboard.copy_selection()

    def is_active(self) -> bool:
        return bool(App.GuiUp and App.activeDocument() and App.Gui.Selection.getSelection())


@commands.add(
    label=QT_TRANSLATE_NOOP("SvgWB", "Copy elements as SVG"),
    tooltip=QT_TRANSLATE_NOOP("SvgWB", "Copy elements as SVG to clipboard"),
    status_tip=QT_TRANSLATE_NOOP("SvgWB", "Copy elements as SVG to clipboard"),
    icon=resources.icon("copy_elem.svg"),
)
class CopyElementSvg:
    """Copy sub element as svg."""

    def on_activated(self) -> None:
        clipboard.copy_selection(sub_elements=True)

    def is_active(self) -> bool:
        if not App.GuiUp:
            return False

        sel = App.Gui.Selection.getSelectionEx()
        return bool(sel and any(s.HasSubObjects for s in sel))
