# SPDX-License: LGPL-3.0-or-later
# (c) 2025 Frank David Martínez Muñoz. <mnesarco at gmail.com>

from __future__ import annotations

from dataclasses import dataclass, field
from Part import Shape  # type: ignore
from Part import makeCompound as make_compound  # type: ignore
from .shape import SvgShape
from .cache import cached_copy, cached_copy_list, cached_property
from .object import SvgObject


@dataclass
class SvgGroup(SvgShape):
    """Group of shapes"""

    _children: list[SvgShape] = field(default_factory=list)

    @cached_copy
    def to_shape(self) -> Shape | None:
        shapes = self.shapes()
        if shapes:
            return make_compound(self.shapes())
        return None

    @cached_copy_list
    def shapes(self) -> list[Shape]:
        shapes: list[Shape] = []
        for s in self._children:
            if hasattr(s, "shapes"):
                shapes.extend(s.shapes())
            else:
                shape = s.to_shape()
                if shape:
                    shapes.append(shape)
        return [s for s in shapes if s]

    def append(self, shape: SvgShape) -> None:
        self._children.append(shape)

    @cached_property
    def objects(self) -> list[SvgObject]:
        objects: list[SvgObject] = []
        parent_id = self.id
        for s in self._children:
            if hasattr(s, "objects"):
                for obj in s.objects:
                    obj.path = f"{parent_id}/{obj.path}"
                    objects.append(obj)
            else:
                obj = SvgObject(s.id, f"{parent_id}/{s.id}", s)
                objects.append(obj)
        return objects
