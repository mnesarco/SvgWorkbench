# SPDX-License: LGPL-3.0-or-later
# (c) 2025 Frank David Martínez Muñoz. <mnesarco at gmail.com>

from .vendor.fcapi.preferences import Preference, Preferences, auto_gui, validators as valid
from .vendor.fcapi.lang import dtr


@auto_gui(
    default_ui_group="Svg",
    default_ui_page=dtr("SvgWB", "Import"),
)
class SvgImportPreferences(Preferences):
    group = "Preferences/Mod/SvgWB/Import"

    disable_unit_scaling = Preference(
        group,
        name="disable_unit_scaling",
        default=False,
        label=dtr("SvgWB", "Disable unit scaling"),
        description=dtr(
            "SvgWB",
            ("If checked, no unit scaling will occur. One unit in svg will become one millimeter"),
        ),
        ui_section=dtr("SvgWB", "Geometry"),
    )

    precision = Preference(
        group,
        name="precision",
        default=3,
        label=dtr("SvgWB", "Coordinate Precision"),
        description=dtr("SvgWB", "Unit: digits behind comma. Important for closed wire detection and tiny edge filtering."),
        ui_section=dtr("SvgWB", "Geometry"),
        ui_validators=[valid.min(0), valid.max(6)],
    )

    style_import_mode = Preference(
        group,
        name="style_import_mode",
        default=0,
        label=dtr("SvgWB", "Transform style"),
        description=dtr("SvgWB", "Import transform"),
        options={
            dtr("SvgWB", "None (fastest)"): 0,
            dtr("SvgWB", "Use default styles"): 1,
            dtr("SvgWB", "Original styles"): 2,
        },
        ui_section=dtr("SvgWB", "Styles"),
    )

    line_width = Preference(
        group,
        name="line_width",
        default=0.35,
        label=dtr("SvgWB", "Default line width"),
        description=dtr("SvgWB", "Import line width"),
        unit="mm",
        ui_section=dtr("SvgWB", "Styles"),
        ui_validators=[valid.min(0.01)],
    )

    line_color = Preference(
        group,
        name="line_color",
        default="rgba(255,255,255,255)",
        label=dtr("SvgWB", "Default line color"),
        description=dtr("SvgWB", "Import line color"),
        ui="InputColor",
        ui_section=dtr("SvgWB", "Styles"),
    )

    fill_color = Preference(
        group,
        name="fill_color",
        default="rgba(100,100,100,255)",
        label=dtr("SvgWB", "Default fill color"),
        description=dtr("SvgWB", "Import fill color"),
        ui="InputColor",
        ui_section=dtr("SvgWB", "Styles"),
    )

    font_size = Preference(
        group,
        name="font_size",
        default=12,
        label=dtr("SvgWB", "Default font size"),
        description=dtr("SvgWB", "Import font size"),
        ui_section=dtr("SvgWB", "Styles"),
        ui_validators=[valid.min(6)],
    )

    edge_approx_points = Preference(
        group,
        name="edge_approx_points",
        default=10,
        label=dtr("SvgWB", "Discretization points"),
        description=dtr("SvgWB", "Number of discretization points for approximated edges"),
        ui_section=dtr("SvgWB", "Geometry"),
        ui_validators=[valid.min(10), valid.max(100)],
    )


@auto_gui(
    default_ui_group="Svg",
    default_ui_page=dtr("SvgWB", "Export"),
)
class SvgExportPreferences(Preferences):
    group = "Preferences/Mod/SvgWB/Export"

    transform = Preference(
        group,
        name="transform",
        default=0,
        label=dtr("SvgWB", "Transform"),
        description=dtr("SvgWB", "Export transform"),
        options={
            dtr("SvgWB", "Translated (for print and display)"): 0,
            dtr("SvgWB", "Raw (for CAM)"): 1,
        },
        ui_section=dtr("SvgWB", "General"),
    )

    scale = Preference(
        group,
        name="scale",
        default=1.0,
        label=dtr("SvgWB", "Scale"),
        description=dtr("SvgWB", "Export scale"),
        ui_validators=[valid.min(0.0, excluded=True)],
        ui_section=dtr("SvgWB", "General"),
    )

    direction = Preference(
        group,
        name="direction",
        default="(0, 0, -1)",
        label=dtr("SvgWB", "View direction"),
        description=dtr("SvgWB", "Projection direction"),
        options={
            dtr("SvgWB", "Front"): "(0, -1, 0)",
            dtr("SvgWB", "Back"): "(0, 1, 0)",
            dtr("SvgWB", "Left"): "(-1, 0, 0)",
            dtr("SvgWB", "Right"): "(1, 0, 0)",
            dtr("SvgWB", "Top"): "(0, 0, 1)",
            dtr("SvgWB", "Bottom"): "(0, 0, -1)",
            dtr("SvgWB", "Isometric 1 (Top-Front-Right)"): "(1, 1, 1)",
            dtr("SvgWB", "Isometric 2 (Top-Left-Front)"): "(-1, 1, 1)",
            dtr("SvgWB", "Isometric 3 (Top-Right-Back)"): "(1, 1, -1)",
            dtr("SvgWB", "Isometric 4 (Top-Back-Left)"): "(-1, 1, -1)",
            dtr("SvgWB", "Isometric 5 (Bottom-Front-Right)"): "(1, -1, 1)",
            dtr("SvgWB", "Isometric 6 (Bottom-Left-Front)"): "(-1, -1, 1)",
            dtr("SvgWB", "Isometric 7 (Bottom-Right-Back)"): "(1, -1, -1)",
            dtr("SvgWB", "Isometric 8 (Bottom-Back-Left)"): "(-1, -1, -1)",
            dtr("SvgWB", "Camera"): "Camera",
        },
        ui_section=dtr("SvgWB", "General"),
    )

    visible_line_width = Preference(
        group,
        name="visible_line_width",
        default=0.35,
        label=dtr("SvgWB", "Line width"),
        description=dtr("SvgWB", "Export visible line width"),
        unit="mm",
        ui_section=dtr("SvgWB", "Visible line style"),
        ui_validators=[valid.min(0.01)],
    )

    visible_line_color = Preference(
        group,
        name="visible_line_color",
        default="rgba(0,0,0,255)",
        label=dtr("SvgWB", "Line color"),
        description=dtr("SvgWB", "Export visible line color"),
        ui="InputColor",
        ui_section=dtr("SvgWB", "Visible line style"),
    )

    hidden_line_width = Preference(
        group,
        name="hidden_line_width",
        default=0.35,
        label=dtr("SvgWB", "Line width"),
        description=dtr("SvgWB", "Export hidden line width"),
        unit="mm",
        ui_section=dtr("SvgWB", "Hidden line style"),
        ui_validators=[valid.min(0.01)],
    )

    hidden_line_color = Preference(
        group,
        name="hidden_line_color",
        default="rgba(127,127,127,127)",
        label=dtr("SvgWB", "Line color"),
        description=dtr("SvgWB", "Export hidden line color"),
        ui="InputColor",
        ui_section=dtr("SvgWB", "Hidden line style"),
    )

    hidden_line_style = Preference(
        group,
        name="hidden_line_style",
        default="1,1,1,2",
        label=dtr("SvgWB", "Hidden line style (Dash array)"),
        description=dtr("SvgWB", "Hidden line style"),
        ui_section=dtr("SvgWB", "Hidden line style"),
        ui_validators=[valid.regex(r"\d+(\s*,\d+)*\s*")],
    )

    hairline_effect = Preference(
        group,
        name="hairline_effect",
        default=True,
        label=dtr("SvgWB", "Non scaling line width"),
        description=dtr("SvgWB", "Hidden line style"),
        ui_section=dtr("SvgWB", "General"),
    )

    show_hidden_lines = Preference(
        group,
        name="show_hidden_lines",
        default=True,
        label=dtr("SvgWB", "Show hidden lines"),
        description=dtr("SvgWB", "Hidden line style"),
        ui_section=dtr("SvgWB", "General"),
    )
