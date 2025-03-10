# SPDX-License: LGPL-3.0-or-later
# (c) 2025 Frank David Martínez Muñoz. <mnesarco at gmail.com>

from __future__ import annotations

from contextlib import contextmanager
from enum import Enum

from ..config import resources
from ..svg.database import SvgDatabase, SvgEntity
from ..vendor.fcapi import fpo
from ..vendor.fcapi.utils import run_later
from . import transformations as trsf
from .svg_object import FeatureBuilder, SvgPartFeature, SvgPlaneFeature, SvgSketchFeature
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from ..vendor.fcapi.fpo import events
    from Part import Shape  # type: ignore
    from FreeCAD import Document  # type: ignore
    from collections.abc import Generator


class QueryType(Enum):
    """Query criteria."""

    ById = "Id"
    ByLabel = "Label"
    ByTag = "Tag"
    ByPath = "Path"
    All = "All"


class ShapeOutput(Enum):
    """Shape output type."""

    Shape = "Shape"
    Vertices = "Vertices"
    Edges = "Edges"
    Wires = "Wires"
    Faces = "Faces"
    CenterOfGravity = "Center of mass"
    CenterOfBoundingBox = "Center of bounding box"
    BoundingBox = "Bounding box"
    Sketch = "Sketch"
    PlanesGeom = "Planes as geometry"
    PlanesDatum = "Planes as datum"


@fpo.view_proxy(icon=resources.icon("svg-query.svg"))
class SvgActionViewProvider(fpo.ViewProxy):
    """View provider for Svg actions."""

    Default = fpo.DisplayMode(is_default=True)

    def on_edit_start(self, event: events.EditStartEvent) -> bool:
        if event.mode == fpo.EditMode.Default:
            from .svg_action_task import ActionTaskPanel

            self.task_panel = ActionTaskPanel(event.source.Proxy)
            self.task_panel.show()
            return True
        return False

    def on_edit_end(self, event: events.EditEndEvent) -> bool:
        return event.mode == fpo.EditMode.Default

    def on_dbl_click(self, event: events.DoubleClickEvent) -> bool:
        event.view_provider.Document.setEdit(self.Object, fpo.EditMode.Default)
        return True


@fpo.proxy(view_proxy=SvgActionViewProvider, subtype="Svg::Action")
class SvgActionFeature(fpo.DataProxy):
    """Action DocumentObject Proxy."""

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
        mode=fpo.PropertyMode.Hidden | fpo.PropertyMode.NoRecompute | fpo.PropertyMode.Output,
    )

    _dirty: bool = False

    _must_recompute: ClassVar[set[str]] = {
        "QueryType",
        "OutputType",
        "Compound",
        "Query",
        "Source",
    }

    _immediate_recompute: ClassVar[set[str]] = {
        "QueryType",
        "OutputType",
        "Compound",
    }

    def _hash_changed(self) -> bool:
        return self.source and self.file_hash != self.source.FileHash

    def on_change(self, event: events.PropertyChangedEvent) -> None:
        property_name = event.property_name
        self._dirty = property_name in self._must_recompute
        if property_name in self._immediate_recompute:
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

    def select_behavior(self) -> FeatureBuilder:  # noqa: C901, PLR0911
        match self.output_type:
            case ShapeOutput.Sketch:
                return FeatureBuilder(SvgSketchFeature, trsf.passthrough)
            case ShapeOutput.Vertices:
                return FeatureBuilder(SvgPartFeature, trsf.shape_to_vertices)
            case ShapeOutput.Edges:
                return FeatureBuilder(SvgPartFeature, trsf.shape_to_edges)
            case ShapeOutput.Wires:
                return FeatureBuilder(SvgPartFeature, trsf.shape_to_wires)
            case ShapeOutput.Faces:
                return FeatureBuilder(SvgPartFeature, trsf.shape_to_faces)
            case ShapeOutput.CenterOfGravity:
                return FeatureBuilder(SvgPartFeature, trsf.shape_to_center_of_gravity)
            case ShapeOutput.BoundingBox:
                return FeatureBuilder(SvgPartFeature, trsf.shape_to_boundbox)
            case ShapeOutput.CenterOfBoundingBox:
                return FeatureBuilder(SvgPartFeature, trsf.shape_to_boundbox_center)
            case ShapeOutput.PlanesGeom:
                return FeatureBuilder(
                    SvgPlaneFeature,
                    trsf.shape_to_planes,
                    {"PlaneMode": "Geometry"},
                )
            case ShapeOutput.PlanesDatum:
                return FeatureBuilder(
                    SvgPlaneFeature,
                    trsf.shape_to_edge,
                    {"PlaneMode": "Datum"},
                )
            case _:
                return FeatureBuilder(SvgPartFeature, trsf.passthrough)

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
        if not self.source:
            return False

        query = self.query
        return not (self.query_type != QueryType.All and (query is None or query.strip() == ""))

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
                obj.addExtension("Part::AttachExtensionPython")
                obj.changeAttacherType("Attacher::AttachEnginePlane")
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
