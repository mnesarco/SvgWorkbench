# SPDX-License: LGPL-3.0-or-later
# (c) 2025 Frank David Martínez Muñoz. <mnesarco at gmail.com>

from __future__ import annotations

from dataclasses import dataclass
import copy
from .shape import SvgShape
from .cache import cached_copy, cached_copy_list, cached_property
from .object import SvgObject
from typing import TYPE_CHECKING
from .parsers import parse_svg_transform
from FreeCAD import Matrix, Vector  # type: ignore

if TYPE_CHECKING:
    from .index import SvgIndex
    from Part import Shape  # type: ignore


def id_hash(parent: str, child: str) -> str:
    return f"{parent}_{child}"


@dataclass
class SvgUse(SvgShape):
    """svg use (aka link)"""

    href: str
    x: float
    y: float
    index: SvgIndex
    move: Matrix | None = None

    def __post_init__(self) -> None:
        self.move = Matrix()
        self.move.move(Vector(self.x, -self.y, 0))

    @cached_copy
    def to_shape(self) -> Shape | None:
        if (target := self.index.find(self.href)) and (sh := target.to_shape()):
            return sh.transformGeometry(self.transform * self.move)
        return None

    @cached_copy_list
    def shapes(self) -> list[Shape]:
        target = self.index.find(self.href)
        if not target:
            return []
        if hasattr(target, "shapes"):
            results = target.shapes()
        else:
            results = [target.to_shape()]
        return [s.transformGeometry(self.transform * self.move) for s in results if s]

    @cached_property
    def objects(self) -> list[SvgObject]:
        objects: list[SvgObject] = []
        parent_id = self.id
        target = self.index.find(self.href)
        if not target:
            return []
        if hasattr(target, "objects"):
            for obj in target.objects:
                objects.append(
                    SvgObject(
                        id_hash(parent_id, obj.id),
                        f"{parent_id}/{obj.path}",
                        self.transformed(obj.shape),
                        href=self.id,
                    ),
                )
        else:
            obj = SvgObject(
                id_hash(parent_id, target.id),
                f"{parent_id}/{target.id}",
                self.transformed(target),
                href=self.id,
            )
            objects.append(obj)
        return objects

    def transformed(self, shape: SvgShape) -> SvgShape:
        sh = copy.copy(shape)
        sh.transform = self.transform * sh.transform * self.move
        return sh
