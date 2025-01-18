# SPDX-License: LGPL-3.0-or-later
# (c) 2025 Frank David Martínez Muñoz. <mnesarco at gmail.com>

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
    def __init__(self, action: SvgActionFeature):
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
                    pattern.split(","), field.value.lower(), include_brep=False
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
    "Center of mass": ShapeOutput.CenterOfMass,
    "Center of bounding box": ShapeOutput.CenterOfBoundingBox,
    "Bounding box": ShapeOutput.BoundingBox,
    "Sketch": ShapeOutput.Sketch,
    "Planes as geometry": ShapeOutput.PlanesGeom,
    "Planes as datum": ShapeOutput.PlanesDatum,
}


class ActionTaskPanel(ui.TaskPanel):
    action: SvgActionFeature

    def __init__(self, action: SvgActionFeature):
        self.action = action

    def build(self):
        with ui.Dialog() as form:
            with ui.Col():
                with ui.Row():
                    self.query = ui.InputOptions(
                        QueryTypeDict,
                        value=self.action.query_type,
                    )
                    self.pattern = ui.InputText(value=self.action.query)

                self.results = ResultsTree(self.action)
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

    def update(self, *_args):
        self.pattern.setVisible(self.query.value() != QueryType.All)
        self.results.search(self.query.value(), self.pattern.value())

    def on_accept(self):
        action = self.action.Object
        doc = action.Document
        with transaction(translate("SvgWB", "Update {}").format(action.Name), doc):
            with recompute_buffer(doc):
                action.QueryType = self.query.value().value
                action.Query = self.pattern.value()
                action.Compound = self.compound.value()
                action.OutputType = self.output.value().value
