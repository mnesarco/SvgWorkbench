# SPDX-License: LGPL-3.0-or-later
# (c) 2025 Frank David Martínez Muñoz. <mnesarco at gmail.com>

# ruff: noqa: D107

from __future__ import annotations

from ..svg.database import SvgDatabase
from ..vendor.fcapi import fcui as ui
from .svg_action import SvgActionFeature, QueryType, ShapeOutput
from typing import TYPE_CHECKING
from ..vendor.fcapi.lang import translate
from ..vendor.fcapi.transactions import transaction
from ..vendor.fcapi.utils import recompute_buffer

if TYPE_CHECKING:
    from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem
else:
    from PySide.QtGui import QTreeWidget, QTreeWidgetItem


class ResultsTree:
    """Results widget for the Task panel."""

    def __init__(self, action: SvgActionFeature) -> None:
        self.action = action
        self.tree = QTreeWidget()
        self.tree.setColumnCount(4)
        self.tree.setHeaderLabels([
            translate("SvgWB", "Tag"),
            translate("SvgWB", "Id"),
            translate("SvgWB", "Label"),
            translate("SvgWB", "Path"),
        ])
        ui.place_widget(self.tree)

    def search(self, field: QueryType, pattern: str) -> None:
        db = SvgDatabase(self.action.source.SqlFile)
        tree = self.tree
        tree.clear()
        if field == QueryType.All or (pattern and pattern.strip()):
            if field == QueryType.All:
                data = db.find_all(include_brep=False)
            else:
                data = db.find_by_pattern(
                    pattern.split(","),
                    field.value.lower(),
                    include_brep=False,
                )
            for entity in data:
                item = QTreeWidgetItem(tree)
                item.setText(0, entity.tag)
                item.setText(1, entity.id)
                item.setText(2, entity.label)
                item.setText(3, entity.path)


QueryTypeDict = {
    "Id": QueryType.ById,
    "Tag": QueryType.ByTag,
    "Path": QueryType.ByPath,
    "Label": QueryType.ByLabel,
    "All": QueryType.All,
}

OutputTypeDict = {
    "Shape": ShapeOutput.Shape,
    "Vertices": ShapeOutput.Vertices,
    "Edges": ShapeOutput.Edges,
    "Wires": ShapeOutput.Wires,
    "Faces": ShapeOutput.Faces,
    "Center of gravity": ShapeOutput.CenterOfGravity,
    "Center of bounding box": ShapeOutput.CenterOfBoundingBox,
    "Bounding box": ShapeOutput.BoundingBox,
    "Sketch": ShapeOutput.Sketch,
    "Planes as geometry": ShapeOutput.PlanesGeom,
    "Planes as datum": ShapeOutput.PlanesDatum,
}


class ActionTaskPanel(ui.TaskPanel):
    """Task panel for Action."""

    action: SvgActionFeature

    def __init__(self, action: SvgActionFeature) -> None:
        self.action = action

    def build(self) -> ui.QDialog:
        with ui.Dialog() as form:
            with ui.GroupBox(title=translate("SvgWB", "Query")):
                self.query = ui.InputOptions(
                    QueryTypeDict,
                    value=self.action.query_type,
                    label=translate("SvgWB", "Filter criteria:"),
                )
                self.pattern = ui.InputText(
                    value=self.action.query,
                    label=translate("SvgWB", "Filter pattern:"),
                )

            with ui.GroupBox(title=translate("SvgWB", "Filter result")):
                self.results = ResultsTree(self.action)

            with ui.GroupBox(title=translate("SvgWB", "Output")):
                self.output = ui.InputOptions(
                    OutputTypeDict,
                    value=self.action.output_type,
                    label=translate("SvgWB", "Output type:"),
                )
                self.compound = ui.InputBoolean(
                    self.action.compound,
                    label=translate("SvgWB", "Make compound:"),
                )

        self.pattern.textChanged.connect(self.update)
        self.query.currentIndexChanged.connect(self.update)
        self.update()

        return form

    def update(self, *_args) -> None:
        query_type = self.query.value()
        if query_type == QueryType.All:
            self.pattern.setValue("")
        self.pattern.setEnabled(query_type != QueryType.All)
        self.results.search(self.query.value(), self.pattern.value())

    def on_accept(self) -> None:
        action = self.action.Object
        doc = action.Document
        with transaction(translate("SvgWB", "Update {}").format(action.Name), doc):
            with recompute_buffer(doc):
                action.QueryType = self.query.value().value
                action.Query = self.pattern.value()
                action.Compound = self.compound.value()
                action.OutputType = self.output.value().value
