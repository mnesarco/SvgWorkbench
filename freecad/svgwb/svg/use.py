# SPDX-License: LGPL-3.0-or-later
# (c) 2025 Frank David Martínez Muñoz. <mnesarco at gmail.com>

from __future__ import annotations

from dataclasses import dataclass
import copy

from Part import Shape  # type: ignore

from .shape import SvgShape
from .index import SvgIndex
from .cache import cached_copy, cached_copy_list, cached_property
from .object import SvgObject

def id_hash(parent: str, child: str) -> str:
    return f"S{hex(hash((parent, child)))[2:]}_{child.split('_')[-1]}"

@dataclass
class SvgUse(SvgShape):
    href: str
    x: float
    y: float
    index: SvgIndex

    @cached_copy
    def to_shape(self) -> Shape | None:
        if target := self.index.find(self.href):
            if sh := target.to_shape():
                return sh.transformGeometry(self.transform)

    @cached_copy_list
    def shapes(self) -> list[Shape]:
        target = self.index.find(self.href)
        if not target:
            return []
        if hasattr(target, "shapes"):
            results = target.shapes()
        else:
            results = [target.to_shape()]
        return [s.transformGeometry(self.transform) for s in results if s]

    @cached_property
    def objects(self) -> list[SvgObject]:
        objects: list[SvgObject] = []
        parent_id = self.id
        target = self.index.find(self.href)
        if not target:
            return []
        if hasattr(target, "objects"):
            count = 1
            for obj in target.objects:
                objects.append(
                    SvgObject(
                        id_hash(parent_id, obj.id),
                        f"{parent_id}/{obj.path}",
                        self.transformed(obj.shape),
                        href=self.id,
                    ),
                )
                count += 1
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
        sh.transform = self.transform.multiply(sh.transform)
        return sh
