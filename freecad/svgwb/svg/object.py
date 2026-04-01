# SPDX-License: LGPL-2.1-or-later
# (c) 2025 Frank David Martínez Muñoz. <mnesarco at gmail.com>

from dataclasses import dataclass

from .shape import SvgShape


@dataclass
class SvgObject:
    """Identifiable Svg object"""

    id: str
    path: str
    shape: SvgShape
    href: str | None = None
