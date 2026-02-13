# SPDX-License: LGPL-3.0-or-later
# (c) 2025 Frank David Martínez Muñoz. <mnesarco at gmail.com>

from __future__ import annotations

from pathlib import Path
from tempfile import gettempdir
from typing import TYPE_CHECKING
from uuid import uuid4

from ..config import SvgImportPreferences, resources
from ..svg.database import SvgDatabase, SvgEntity
from ..svg.parser import parse
from ..vendor.fcapi import fpo
from ..vendor.fcapi.lang import translate

if TYPE_CHECKING:
    from collections.abc import Generator
    from FreeCAD import DocumentObject  # type: ignore


def find_child_actions(parent: DocumentObject) -> Generator[DocumentObject, None, None]:
    return (obj for obj in parent.Document.Objects if getattr(obj, "Source", None) is parent)


@fpo.view_proxy(icon=resources.icon("svg-db.svg"))
class SvgFileViewProvider(fpo.ViewProxy):
    """ViewProvider for svg database objects."""

    Default = fpo.DisplayMode(is_default=True)

    def on_claim_children(self, event: fpo.events.ClaimChildrenEvent) -> list[DocumentObject]:
        return list(find_child_actions(self.Object))

    def on_context_menu(self, event: fpo.events.ContextMenuEvent) -> None:
        from ..vendor.fcapi import fcui as ui

        if event.source.Proxy.sql_file and Path(event.source.Proxy.sql_file).exists():
            action = ui.QAction(
                ui.QIcon(resources.icon("svg-query.svg")),
                translate("SvgWB", "Create action query"),
                event.menu,
            )
            action.triggered.connect(event.source.Proxy.create_action)
            event.menu.addAction(action)

        if (
            event.source.Proxy.external_file
            and Path(event.source.Proxy.external_file).exists()
            and "_clipboard_" not in event.source.Proxy.external_file
        ):
            action = ui.QAction(
                ui.QIcon(resources.icon("sync.svg")),
                translate("SvgWB", "Sync with external svg file"),
                event.menu,
            )
            action.triggered.connect(event.source.Proxy.sync_file)
            event.menu.addAction(action)

        if event.source.Proxy.internal_file and Path(event.source.Proxy.internal_file).exists():
            action = ui.QAction(
                ui.QIcon(resources.icon("extract.svg")),
                translate("SvgWB", "Extract original svg file"),
                event.menu,
            )
            action.triggered.connect(self.extract)
            event.menu.addAction(action)

    def extract(self) -> None:
        from ..vendor.fcapi import fcui as ui

        out = ui.get_save_file(translate("SvgWB", "Save as..."))
        if out:
            src = Path(self.Object.Proxy.internal_file)
            dst = Path(out)
            dst.write_text(src.read_text())


HiddenOutputMode = fpo.PropertyMode.Hidden | fpo.PropertyMode.NoRecompute | fpo.PropertyMode.Output


@fpo.proxy(view_proxy=SvgFileViewProvider, subtype="Svg::Import")
class SvgFileFeature(fpo.DataProxy):
    """Svg Database Object Proxy."""

    # External source svg file
    external_file = fpo.PropertyFile(section="")

    # Internal SQL Database
    sql_file = fpo.PropertyFileIncluded(mode=HiddenOutputMode, section="Files")

    # Internal SVG File
    internal_file = fpo.PropertyFileIncluded(mode=HiddenOutputMode, section="Files")

    # md5 hash of internal_file
    file_hash = fpo.PropertyString(mode=HiddenOutputMode, section="Files")

    def sync_file(self) -> None:
        if self.external_file and Path(self.external_file).exists():
            self.internal_file = self.external_file
            self.svg_to_sql()
            self.Object.Document.recompute()
            for child in find_child_actions(self.Object):
                child.recompute()

    def create_action(self) -> None:
        from .svg_action import SvgActionFeature, QueryType

        obj: DocumentObject = SvgActionFeature.create(name="SvgA001", label="Action.001")
        obj.Source = self.Object
        if (parent := self.Object.getParent()) and hasattr(parent, "addObject"):
            parent.addObject(obj)
            obj.adjustRelativeLinks(parent)
        self.Object.touch()
        self.Object.Document.recompute()
        if vo := obj.ViewObject:
            obj.Proxy.query_type = QueryType.All
            if "_clipboard_" in (self.external_file or ""):
                obj.recompute()
            else:
                vo.Document.setEdit(obj, fpo.EditMode.Default)

    @external_file.observer
    def on_external_file_change(self, _) -> None:
        self.sync_file()

    def svg_to_sql(self) -> None:
        from ..vendor.fcapi import fcui as ui

        with ui.progress_indicator(translate("SvgWB", "Importing svg elements...")):
            pref = SvgImportPreferences()
            dpi = 96.0
            result = parse(self.internal_file, pref, dpi)
            self.file_hash = result.hash
            file_name = Path(gettempdir()) / f"{uuid4()!s}.sqlite"
            db = SvgDatabase(file_name)
            db.initialize()
            shapes = ((obj, obj.shape.to_shape()) for obj in result.objects())
            entities = (
                SvgEntity(
                    obj.id,
                    obj.shape.tag,
                    obj.shape.label,
                    obj.path,
                    obj.href,
                    shape.exportBrepToString(),
                )
                for (obj, shape) in shapes
                if shape
            )
            db.add_many_iter(entities)
            self.sql_file = str(file_name)

            if next(find_child_actions(self.Object), 0) == 0:
                self.create_action()

    def on_execute(self, _) -> None:
        pass
