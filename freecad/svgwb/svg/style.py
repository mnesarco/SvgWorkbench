# SPDX-License: LGPL-3.0-or-later
# (c) 2025 Frank David Martínez Muñoz. <mnesarco at gmail.com>

from __future__ import annotations

from dataclasses import dataclass


_SVG_COLORS = {
    "Pink": (255, 192, 203),
    "Blue": (0, 0, 255),
    "Honeydew": (240, 255, 240),
    "Purple": (128, 0, 128),
    "Fuchsia": (255, 0, 255),
    "LawnGreen": (124, 252, 0),
    "Amethyst": (153, 102, 204),
    "Crimson": (220, 20, 60),
    "White": (255, 255, 255),
    "NavajoWhite": (255, 222, 173),
    "Cornsilk": (255, 248, 220),
    "Bisque": (255, 228, 196),
    "PaleGreen": (152, 251, 152),
    "Brown": (165, 42, 42),
    "DarkTurquoise": (0, 206, 209),
    "DarkGreen": (0, 100, 0),
    "MediumOrchid": (186, 85, 211),
    "Chocolate": (210, 105, 30),
    "PapayaWhip": (255, 239, 213),
    "Olive": (128, 128, 0),
    "Silver": (192, 192, 192),
    "PeachPuff": (255, 218, 185),
    "Plum": (221, 160, 221),
    "DarkGoldenrod": (184, 134, 11),
    "SlateGrey": (112, 128, 144),
    "MintCream": (245, 255, 250),
    "CornflowerBlue": (100, 149, 237),
    "Gold": (255, 215, 0),
    "HotPink": (255, 105, 180),
    "DarkBlue": (0, 0, 139),
    "LimeGreen": (50, 205, 50),
    "DeepSkyBlue": (0, 191, 255),
    "DarkKhaki": (189, 183, 107),
    "LightGrey": (211, 211, 211),
    "Yellow": (255, 255, 0),
    "Gainsboro": (220, 220, 220),
    "MistyRose": (255, 228, 225),
    "SandyBrown": (244, 164, 96),
    "DeepPink": (255, 20, 147),
    "Magenta": (255, 0, 255),
    "AliceBlue": (240, 248, 255),
    "DarkCyan": (0, 139, 139),
    "DarkSlateGrey": (47, 79, 79),
    "GreenYellow": (173, 255, 47),
    "DarkOrchid": (153, 50, 204),
    "OliveDrab": (107, 142, 35),
    "Chartreuse": (127, 255, 0),
    "Peru": (205, 133, 63),
    "Orange": (255, 165, 0),
    "Red": (255, 0, 0),
    "Wheat": (245, 222, 179),
    "LightCyan": (224, 255, 255),
    "LightSeaGreen": (32, 178, 170),
    "BlueViolet": (138, 43, 226),
    "LightSlateGrey": (119, 136, 153),
    "Cyan": (0, 255, 255),
    "MediumPurple": (147, 112, 219),
    "MidnightBlue": (25, 25, 112),
    "FireBrick": (178, 34, 34),
    "PaleTurquoise": (175, 238, 238),
    "PaleGoldenrod": (238, 232, 170),
    "Gray": (128, 128, 128),
    "MediumSeaGreen": (60, 179, 113),
    "Moccasin": (255, 228, 181),
    "Ivory": (255, 255, 240),
    "DarkSlateBlue": (72, 61, 139),
    "Beige": (245, 245, 220),
    "Green": (0, 128, 0),
    "SlateBlue": (106, 90, 205),
    "Teal": (0, 128, 128),
    "Azure": (240, 255, 255),
    "LightSteelBlue": (176, 196, 222),
    "DimGrey": (105, 105, 105),
    "Tan": (210, 180, 140),
    "AntiqueWhite": (250, 235, 215),
    "SkyBlue": (135, 206, 235),
    "GhostWhite": (248, 248, 255),
    "MediumTurquoise": (72, 209, 204),
    "FloralWhite": (255, 250, 240),
    "LavenderBlush": (255, 240, 245),
    "SeaGreen": (46, 139, 87),
    "Lavender": (230, 230, 250),
    "BlanchedAlmond": (255, 235, 205),
    "DarkOliveGreen": (85, 107, 47),
    "DarkSeaGreen": (143, 188, 143),
    "SpringGreen": (0, 255, 127),
    "Navy": (0, 0, 128),
    "Orchid": (218, 112, 214),
    "SaddleBrown": (139, 69, 19),
    "IndianRed": (205, 92, 92),
    "Snow": (255, 250, 250),
    "SteelBlue": (70, 130, 180),
    "MediumSlateBlue": (123, 104, 238),
    "Black": (0, 0, 0),
    "LightBlue": (173, 216, 230),
    "Turquoise": (64, 224, 208),
    "MediumVioletRed": (199, 21, 133),
    "DarkViolet": (148, 0, 211),
    "DarkGray": (169, 169, 169),
    "Salmon": (250, 128, 114),
    "DarkMagenta": (139, 0, 139),
    "Tomato": (255, 99, 71),
    "WhiteSmoke": (245, 245, 245),
    "Goldenrod": (218, 165, 32),
    "MediumSpringGreen": (0, 250, 154),
    "DodgerBlue": (30, 144, 255),
    "Aqua": (0, 255, 255),
    "ForestGreen": (34, 139, 34),
    "LemonChiffon": (255, 250, 205),
    "LightSlateGray": (119, 136, 153),
    "SlateGray": (112, 128, 144),
    "LightGray": (211, 211, 211),
    "Indigo": (75, 0, 130),
    "CadetBlue": (95, 158, 160),
    "LightYellow": (255, 255, 224),
    "DarkOrange": (255, 140, 0),
    "PowderBlue": (176, 224, 230),
    "RoyalBlue": (65, 105, 225),
    "Sienna": (160, 82, 45),
    "Thistle": (216, 191, 216),
    "Lime": (0, 255, 0),
    "Seashell": (255, 245, 238),
    "DarkRed": (139, 0, 0),
    "LightSkyBlue": (135, 206, 250),
    "YellowGreen": (154, 205, 50),
    "Aquamarine": (127, 255, 212),
    "LightCoral": (240, 128, 128),
    "DarkSlateGray": (47, 79, 79),
    "Khaki": (240, 230, 140),
    "DarkGrey": (169, 169, 169),
    "BurlyWood": (222, 184, 135),
    "LightGoldenrodYellow": (250, 250, 210),
    "MediumBlue": (0, 0, 205),
    "DarkSalmon": (233, 150, 122),
    "RosyBrown": (188, 143, 143),
    "LightSalmon": (255, 160, 122),
    "PaleVioletRed": (219, 112, 147),
    "Coral": (255, 127, 80),
    "Violet": (238, 130, 238),
    "Grey": (128, 128, 128),
    "LightGreen": (144, 238, 144),
    "Linen": (250, 240, 230),
    "OrangeRed": (255, 69, 0),
    "DimGray": (105, 105, 105),
    "Maroon": (128, 0, 0),
    "LightPink": (255, 182, 193),
    "MediumAquamarine": (102, 205, 170),
    "OldLace": (253, 245, 230),
}

_SVG_COLORS_LOWER = {k.lower(): v for k, v in _SVG_COLORS.items()}


class SvgColor:
    def __init__(self, source):
        self.source = source

    def __repr__(self):
        return self.source

    def as_tuple(self) -> tuple[float, float, float, float]:
        """Check if the given string is an RGB value, or if it is a named color.

        Parameters
        ----------
        color : str
            Color in hexadecimal format, long '#12ab9f' or short '#1af'

        Returns
        -------
        tuple
        (r, g, b, a)
            RGBA float tuple, where each value is between 0.0 and 1.0.
        """
        color = self.source
        if color == "none":
            return (0.0, 0.0, 0.0, 0.0)

        if color[0] == "#":
            if len(color) == 7 or len(color) == 9:  # Color string '#RRGGBB' or '#RRGGBBAA'
                r = float(int(color[1:3], 16) / 255.0)
                g = float(int(color[3:5], 16) / 255.0)
                b = float(int(color[5:7], 16) / 255.0)
                a = 1.0
                if len(color) == 9:
                    a = float(int(color[7:9], 16) / 255.0)
                return (r, g, b, 1 - a)
            if len(color) == 4:  # Color string '#RGB'
                # Expand the hex digits
                r = float(int(color[1], 16) * 17 / 255.0)
                g = float(int(color[2], 16) * 17 / 255.0)
                b = float(int(color[3], 16) * 17 / 255.0)
                return (r, g, b, 0.0)

        if color.lower().startswith("rgb(") or color.lower().startswith(
            "rgba("
        ):  # Color string 'rgb[a](0.12,0.23,0.3,0.0)'
            cvalues = color.lstrip("rgba(").rstrip(")").replace("%", "").split(",")
            if len(cvalues) == 3:
                a = 1.0
                if "%" in color:
                    r, g, b = [int(float(cv)) / 100.0 for cv in cvalues]
                else:
                    r, g, b = [int(float(cv)) / 255.0 for cv in cvalues]
            if len(cvalues) == 4:
                if "%" in color:
                    r, g, b, a = [int(float(cv)) / 100.0 for cv in cvalues]
                else:
                    r, g, b, a = [int(float(cv)) / 255.0 for cv in cvalues]
            return (r, g, b, 1 - a)

        # Trying named color like 'MediumAquamarine'
        v = _SVG_COLORS_LOWER.get(color.lower())
        if v:
            r, g, b = [float(vf) / 255.0 for vf in v]
            return (r, g, b, 0.0)

        return (0.0, 0.0, 0.0, 0.0)


@dataclass(slots=True)
class SvgStyle:
    stroke_color: SvgColor | None = None
    stroke_width: float | None = None
    fill_color: SvgColor | None = None
    font_size: int | None = None
