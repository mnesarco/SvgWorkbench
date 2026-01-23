# SPDX-License: LGPL-3.0-or-later
# (c) 2025 Frank David Martínez Muñoz. <mnesarco at gmail.com>

"""
Custom actions for freecad.FileExplorerExt
"""

from pathlib import Path
from ..vendor.fcapi.fpo import print_log
from ..vendor.fcapi.lang import translate

import FreeCAD as App

class _State:
    activated: bool = False

def init() -> None:
    if _State.activated:
        return

    try:
        from freecad.FileExplorerExt import API
        from freecad.FileExplorerExt import CustomFileAction
    except ImportError:
        print_log("freecad.FileExplorerExt not detected.")
        return

    _State.activated = True

    from freecad.svgwb.commands.import_svg import import_svg
    from freecad.svgwb.config import resources
    from ..features.svg_file import SvgFileFeature

    def import_plain_svg(path: list[Path]) -> None:
        print(f"Open: {path!s}")
        import_svg(str(path[0]))

    def import_svg_source_object(svg_file: list[Path]) -> None:
        obj = SvgFileFeature.create(name="SvgImport")
        obj.ExternalFile = str(svg_file[0])
        obj.Label = svg_file[0].name
        obj.recompute()

    def create_actions(paths: list[Path]) -> list[CustomFileAction]:
        """Returns set of custom actions based on paths."""

        actions = []

        if paths[0].suffix.lower() == ".svg":
            actions.append(
                CustomFileAction(
                    text=translate("SvgWB", "Import Svg as plain Geometry"),
                    icon=resources.icon("import_svg.svg"),
                    activated=import_plain_svg,
                ),
            )

            if App.activeDocument():
                actions.append(
                    CustomFileAction(
                        text=translate("SvgWB", "Import Svg as SvgFile Object"),
                        icon=resources.icon("add-svg-db.svg"),
                        activated=import_svg_source_object,
                    ),
                )

        return actions

    API.add_action_provider(create_actions, key="svgwb-actions")
