# SPDX-License: LGPL-3.0-or-later
# (c) 2025 Frank David Martínez Muñoz. <mnesarco at gmail.com>

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .dimension import SvgDimension


@dataclass(slots=True)
class SvgOptions:
    """Additional custom freecad options in svg object"""

    skip: bool = False
    dimension: SvgDimension | None = None
