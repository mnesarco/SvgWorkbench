# SPDX-License: LGPL-3.0-or-later
# (c) 2026 Frank David Martínez Muñoz. <mnesarco at gmail.com>

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from Part import Face
    from FreeCAD import Vector


def get_face_normal(face: Face) -> Vector | None:
    u_min, u_max, v_min, v_max = face.ParameterRange
    u_mid = (u_min + u_max) / 2
    v_mid = (v_min + v_max) / 2
    return face.normalAt(u_mid, v_mid).normalize()
