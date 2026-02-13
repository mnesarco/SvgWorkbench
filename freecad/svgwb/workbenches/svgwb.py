# SPDX-License: LGPL-3.0-or-later
# (c) 2025 Frank David Martínez Muñoz. <mnesarco at gmail.com>

from ..vendor.fcapi.workbenches import Workbench, ToolSet, Rules
from ..vendor.fcapi.lang import QT_TRANSLATE_NOOP
from ..config import resources, commands

# Import commands to register them
from ..commands import import_svg, export_svg, create_svg_file_object, paste_svg, sync_all, copy_svg  # noqa: F401


class SvgWorkbench(Workbench):
    """
    Svg Workbench
    """

    Label = "Svg"
    ToolTip = QT_TRANSLATE_NOOP("SvgWB", "Svg Manipulation Workbench")
    Icon = resources.icon("svgwb.svg")

    def on_activated(self) -> None:
        from freecad.svgwb.plugins import file_explorer
        self.wbm.install()
        file_explorer.init()

    def on_deactivated(self) -> None:
        self.wbm.uninstall()

    def on_init(self) -> None:
        commands.install()
        self.add_toolbar(ToolSet("SvgWB1", commands.names()))
        rules = Rules("SvgWB_WBM")
        rules.menubar_insert("SvgWB_ImportSvg", after="Std_Import")
        self.wbm = rules

    def on_context_menu(self, recipient: str, menu: ToolSet) -> None:
        menu.add([copy_svg.CopySvg, copy_svg.CopyElementSvg, paste_svg.PasteSvgFileObject])
