# SPDX-License: LGPL-3.0-or-later
# (c) 2024 Frank David Martínez Muñoz. <mnesarco at gmail.com>

from __future__ import annotations

from pathlib import Path

from ..config import resources, commands
from ..vendor.fcapi.lang import QT_TRANSLATE_NOOP
from ..utils import clipboard

import FreeCAD as App  # type: ignore


@commands.add(
    label=QT_TRANSLATE_NOOP("SvgWB", "Sync all svg sources"),
    tooltip=QT_TRANSLATE_NOOP("SvgWB", "Sync all svg sources (if changed)"),
    status_tip=QT_TRANSLATE_NOOP("SvgWB", "Sync all svg sources (if changed)"),
    icon=resources.icon("sync.svg"),
    accel="F5",
)
class SyncAllSvgFileObject:
    """Sync all svg sources that have changed in the file system."""

    def on_activated(self) -> None:
        from ..features.svg_file import SvgFileFeature
        doc = App.activeDocument()
        for obj in doc.findObjects("App::FeaturePython"):
            if hasattr(obj, "Proxy") and isinstance(obj.Proxy, SvgFileFeature):
                proxy: SvgFileFeature = obj.Proxy
                if proxy.internal_file and proxy.external_file:
                    internal = Path(proxy.internal_file)
                    external = Path(proxy.external_file)
                    if internal.exists() and external.exists() and internal.stat().st_mtime < external.stat().st_mtime:
                        proxy.sync_file()

    def is_active(self) -> bool:
        return bool(App.GuiUp and App.activeDocument())
