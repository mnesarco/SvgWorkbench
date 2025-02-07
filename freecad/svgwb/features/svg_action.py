# SPDX-License: LGPL-3.0-or-later
# (c) 2025 Frank David Martínez Muñoz. <mnesarco at gmail.com>

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Generator, TypeAlias

from FreeCAD import BoundBox, Document, DocumentObject, Vector  # type: ignore
from Part import Compound, Face, LineSegment, Shape, Vertex, Wire, Edge  # type: ignore
from Part import makeCompound as make_compound  # type: ignore
from Part import makePlane as make_plane  # type: ignore

from ..config import resources
from ..svg.database import SvgDatabase, SvgEntity
from ..vendor.fcapi import fpo
from ..vendor.fcapi.utils import run_later
from .svg_object import SvgObjectFeature, SvgPartFeature, SvgPlaneFeature, SvgSketchFeature

Z_DIR = Vector(0, 0, 1)


class QueryType(Enum):
    ById = "Id"
    ByLabel = "Label"
    ByTag = "Tag"
    ByPath = "Path"
    All = "All"


class ShapeOutput(Enum):
    Shape = "Shape"
    Vertices = "Vertices"
    Edges = "Edges"
    Wires = "Wires"
    Faces = "Faces"
    CenterOfMass = "Center of mass"
    CenterOfBoundingBox = "Center of bounding box"
    BoundingBox = "Bounding box"
    Sketch = "Sketch"
    PlanesGeom = "Planes as geometry"
    PlanesDatum = "Planes as datum"


ShapeTransformer: TypeAlias = Callable[[Shape], Shape]


def bound_box_rect(box: BoundBox) -> Wire:
    if not box.isValid():
        return Wire()
    edges = [LineSegment(v[0], v[1]).toShape() for v in (box.getEdge(i) for i in range(4))]
    return Wire(edges)


def edge_to_plane(edge: Edge) -> Face:
    MIN_PLANE_SIZE = 50
    if edge.Orientation != "Forward":
        edge.reverse()
    start, end = edge.firstVertex().CenterOfGravity, edge.lastVertex().CenterOfGravity
    line: Vector = end - start
    tan: Vector = Vector(line).normalize()
    size = max(line.Length, MIN_PLANE_SIZE)
    start = (start + tan * ((line.Length - size) / 2.0)) + Vector(0, 0, size / 2.0)
    normal = Z_DIR.cross(tan)
    return make_plane(size, size, start, normal, tan)


@dataclass
class FeatureBuilder:
    feature: type[SvgObjectFeature]
    transform: ShapeTransformer
    options: dict[str, Any]

    def __call__(
        self,
        entity: SvgEntity,
        name: str,
        parent: DocumentObject,
    ) -> DocumentObject | None:
        shape = self.transform(entity.shape)
        if shape and not shape.isNull() and shape.BoundBox.isValid():
            feature = self.feature(
                name,
                entity.id,
                entity.tag,
                entity.label,
                entity.path,
                entity.href,
                shape,
                self.options,
            )
            return feature.add_to_document(parent.Document, parent)


@fpo.view_proxy(icon=resources.icon("svg-query.svg"))
class SvgActionViewProvider(fpo.ViewProxy):
    Default = fpo.DisplayMode(is_default=True)

    def on_edit_start(self, event) -> bool:
        if event.mode == fpo.EditMode.Default:
            from .svg_action_task import ActionTaskPanel

            self.task_panel = ActionTaskPanel(event.source.Proxy)
            self.task_panel.show()
            return True

    def on_edit_end(self, event):
        if event.mode == fpo.EditMode.Default:
            return True

    def on_dbl_click(self, event) -> bool:
        event.view_provider.Document.setEdit(self.Object, fpo.EditMode.Default)
        return True


@fpo.proxy(view_proxy=SvgActionViewProvider, subtype="Svg::Action")
class SvgActionFeature(fpo.DataProxy):
    source = fpo.PropertyLinkHidden(mode=fpo.PropertyMode.Hidden)

    query_type = fpo.PropertyEnumeration(
        enum=QueryType,
        section="Query",
        default=QueryType.ById,
        description=("Search type"),
    )

    query = fpo.PropertyString(
        section="Query",
        description=(
            "Search criteria, accepts '*' as wildcard and comma separated discrete values"
        ),
    )

    output_type = fpo.PropertyEnumeration(
        enum=ShapeOutput,
        section="Output",
        default=ShapeOutput.Shape,
        description=("How to interpret/transform the imported svg objects."),
    )

    compound = fpo.PropertyBool(
        default=True,
        section="Output",
        description="If True, the result of the query will be added to a compound.",
    )

    file_hash = fpo.PropertyString(
        mode=fpo.PropertyMode.Hidden | fpo.PropertyMode.NoRecompute | fpo.PropertyMode.Output
    )

    _dirty: bool = False

    _must_recompute = {
        "QueryType",
        "OutputType",
        "Compound",
        "Query",
        "Source",
    }

    _hot_recompute = {
        "QueryType",
        "OutputType",
        "Compound",
    }

    def _hash_changed(self) -> bool:
        return self.source and self.file_hash != self.source.FileHash

    def on_change(self, event: fpo.events.PropertyChangedEvent) -> None:
        property_name = event.property_name
        self._dirty = property_name in self._must_recompute
        if property_name in self._hot_recompute:
            event.source.recompute()

    def execute_query(self) -> list[SvgEntity]:
        query = self.query
        db = SvgDatabase(self.source.SqlFile)
        match self.query_type:
            case QueryType.ById:
                return db.find_by_id(query)
            case QueryType.ByPath:
                return db.find_by_path(query)
            case QueryType.ByTag:
                return db.find_by_tag(query)
            case QueryType.ByLabel:
                return db.find_by_label(query)
            case _:
                return db.find_all()

    def select_behavior(self) -> FeatureBuilder:
        match self.output_type:
            case ShapeOutput.Sketch:
                return FeatureBuilder(SvgSketchFeature, lambda s: s, {})
            case ShapeOutput.Vertices:
                return FeatureBuilder(SvgPartFeature, lambda s: make_compound(s.Vertexes), {})
            case ShapeOutput.Edges:
                return FeatureBuilder(SvgPartFeature, lambda s: make_compound(s.Edges), {})
            case ShapeOutput.Wires:
                return FeatureBuilder(SvgPartFeature, self.output_wires, {})
            case ShapeOutput.Faces:
                return FeatureBuilder(SvgPartFeature, self.output_faces, {})
            case ShapeOutput.CenterOfMass:
                return FeatureBuilder(SvgPartFeature, lambda s: Vertex(s.CenterOfGravity), {})
            case ShapeOutput.BoundingBox:
                return FeatureBuilder(SvgPartFeature, lambda s: bound_box_rect(s.BoundBox), {})
            case ShapeOutput.CenterOfBoundingBox:
                return FeatureBuilder(SvgPartFeature, lambda s: Vertex(s.BoundBox.Center), {})
            case ShapeOutput.PlanesGeom:
                return FeatureBuilder(
                    SvgPlaneFeature, self.output_planes, {"PlaneMode": "Geometry"}
                )
            case ShapeOutput.PlanesDatum:
                return FeatureBuilder(SvgPlaneFeature, lambda s: s, {"PlaneMode": "Datum"})
            case _:
                return FeatureBuilder(SvgPartFeature, lambda s: s, {})

    @contextmanager
    def clean_objects(self) -> Generator[dict[str, str], None, None]:
        parent = self.Object
        self._pending_remove = {
            obj.SvgPath: obj.Name
            for obj in self.Object.Document.Objects
            if hasattr(obj, "SvgAction") and obj.SvgAction is parent
        }
        try:
            yield self._pending_remove
        finally:
            if self._pending_remove:
                run_later(lambda: self.remove_orphans(self.Object.Document))

    def validate(self) -> bool:
        query = self.query
        if not self.source:
            return False
        if self.query_type != QueryType.All and (query is None or query.strip() == ""):
            return False
        return True

    def on_execute(self, event: fpo.events.ExecuteEvent) -> None:
        if not self._hash_changed() and not self._dirty:
            return

        with self.clean_objects() as existing_names:
            if not self.validate():
                return

            objects = self.execute_query()
            if not objects:
                return

            action = event.source
            builder = self.select_behavior()
            base_name = action.Name
            comp_name = f"{base_name}Comp"
            comp_label = f"{action.Label}.Comp"
            compound = []
            create_compound = all((
                self.compound,
                self.output_type != ShapeOutput.Sketch,
                self.output_type != ShapeOutput.PlanesDatum,
                self.output_type != ShapeOutput.PlanesGeom,
            ))

            for item in objects:
                name = existing_names.pop(item.path, f"{base_name}_{item.id}")
                if obj := builder(item, name, action):
                    if create_compound:
                        compound.append(obj)
                else:
                    existing_names[item.path] = name

            self.update_compound(
                comp_name,
                comp_label,
                compound,
                existing_names,
            )

            self.file_hash = action.FileHash
            self._dirty = False

    def update_compound(
        self,
        comp_name: str,
        comp_label: str,
        compound: list[Shape],
        existing_names: dict[str, str],
    ) -> None:
        doc = self.Object.Document
        if compound:
            obj = doc.getObject(comp_name)
            if not obj:
                obj = doc.addObject("Part::Compound", comp_name)
            obj.Links = compound
            obj.Label = comp_label
            obj.recompute()
        else:
            existing_names["__compound__"] = comp_name
            if obj := doc.getObject(comp_name):
                for child in obj.Links:
                    if vo := getattr(child, "ViewObject", None):
                        vo.Visibility = True

    def remove_orphans(self, doc: Document) -> None:
        if self._pending_remove:
            for name in self._pending_remove.values():
                if doc.getObject(name):
                    doc.removeObject(name)
        self._pending_remove = None

    def output_planes(self, shape: Shape) -> Face | Compound | None:
        if shape is None or not shape.isValid() or shape.isNull():
            return None

        planes = [edge_to_plane(e) for e in shape.Edges if not e.isClosed() and e.Length >= 1]
        if len(planes) == 1:
            return planes[0]

        return make_compound(planes)

    def output_faces(self, shape: Shape) -> Face | Compound | None:
        if shape is None or not shape.isValid() or shape.isNull():
            return None

        match shape.ShapeType:
            case "Face":
                return shape
            case "Wire" if shape.isClosed():
                return Face(shape)
            case "Edge" if shape.isClosed():
                return Face(Wire([shape]))
            case "Vertex":
                return None
            case _:
                faces = [f for f in shape.Faces]
                wires = shape.Wires
                edges = shape.Edges
                for wire in wires:
                    if all(wire not in f.Wires for f in faces) and wire.isClosed():
                        faces.append(Face(wire))
                for edge in edges:
                    if all(edge not in w.Edges for w in wires) and edge.isClosed():
                        faces.append(Face(Wire([edge])))
                return make_compound(faces)

    def output_wires(self, shape: Shape) -> Wire | Compound | None:
        if shape is None or not shape.isValid() or shape.isNull():
            return None

        match shape.ShapeType:
            case "Face":
                return make_compound(shape.Wires)
            case "Wire":
                return shape
            case "Edge":
                return Wire([shape])
            case "Vertex":
                return None
            case _:
                wires = [w for w in shape.Wires]
                edges = shape.Edges
                for edge in edges:
                    if all(edge not in w.Edges for w in wires):
                        wires.append(Wire([edge]))
                return make_compound(wires)
