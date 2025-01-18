# SPDX-License: LGPL-3.0-or-later
# (c) 2025 Frank David Martínez Muñoz. <mnesarco at gmail.com>

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import FreeCAD as App  # type: ignore

if TYPE_CHECKING:
    from FreeCAD import Document, DocumentObject  # type: ignore
    from Part import Shape  # type: ignore
    import FreeCADGui as Gui  # type: ignore


def is_sketch_like(obj: DocumentObject) -> bool:
    return obj and hasattr(obj, "delGeometries")


@dataclass
class SvgObjectFeature:
    name: str
    id: str
    tag: str
    label: str
    path: str
    href: str
    shape: Shape
    options: Any

    def init_properties(
        self,
        obj: DocumentObject,
        action: DocumentObject,
        is_plane: bool = False,
    ):
        obj.addProperty("App::PropertyString", "SvgPath", "Svg", "")
        obj.addProperty("App::PropertyString", "SvgId", "Svg", "")
        obj.addProperty("App::PropertyString", "SvgLabel", "Svg", "")
        obj.addProperty("App::PropertyString", "SvgHref", "Svg", "")
        obj.addProperty("App::PropertyString", "SvgTag", "Svg", "")
        obj.addProperty("App::PropertyLinkHidden", "SvgAction", "Svg", "")
        obj.addProperty("App::PropertyBool", "SvgIsPlane", "Svg", "")
        obj.SvgPath = self.path or ""
        obj.SvgId = self.id or ""
        obj.SvgLabel = self.label or ""
        obj.SvgHref = self.href or ""
        obj.SvgTag = self.tag or ""
        obj.SvgAction = action
        obj.SvgIsPlane = is_plane
        obj.Label = self.label or self.id or ""
        self.update_prop_status(obj, "ReadOnly")

    def update_prop_status(self, obj: DocumentObject, status: str):
        for prop in (
            "SvgPath",
            "SvgId",
            "SvgLabel",
            "SvgHref",
            "SvgTag",
            "SvgAction",
            "SvgIsPlane",
        ):
            obj.setPropertyStatus(prop, status)
        obj.setPropertyStatus("Placement", "Hidden")

    def update_common_props(self, obj: DocumentObject, *, is_plane: bool = False):
        self.update_prop_status(obj, "-ReadOnly")
        obj.SvgPath = self.path or ""
        obj.SvgId = self.id or ""
        obj.SvgLabel = self.label or ""
        obj.SvgHref = self.href or ""
        obj.SvgTag = self.tag or ""
        obj.SvgIsPlane = is_plane
        self.update_prop_status(obj, "ReadOnly")

    def add_to_document(self, doc: Document, action: DocumentObject) -> DocumentObject:
        pass


@dataclass
class SvgPartFeature(SvgObjectFeature):
    def add_to_document(self, doc: Document, action: DocumentObject) -> DocumentObject:
        obj = doc.getObject(self.name)

        if is_sketch_like(obj):
            doc.removeObject(obj.Name)
            obj = None

        if obj:
            self.update_common_props(obj)
            obj.Shape = self.shape
            obj.recompute()
            return obj

        obj = doc.addObject("Part::FeatureExt", self.name)
        obj.addExtension("Part::AttachExtensionPython")
        obj.Shape = self.shape
        self.init_properties(obj, action)
        obj.recompute()
        return obj


@dataclass
class SvgSketchFeature(SvgObjectFeature):
    def add_to_document(self, doc: Document, action: DocumentObject) -> DocumentObject:
        from Draft import make_sketch  # type: ignore

        obj = doc.getObject(self.name)

        if not is_sketch_like(obj):
            doc.removeObject(obj.Name)
            obj = None

        if obj:
            self.update_common_props(obj)
            obj.delGeometries([i for i in range(obj.GeometryCount)])
            make_sketch(self.shape, autoconstraints=True, addTo=obj)
            obj.recompute()
            return obj

        obj = make_sketch(self.shape, autoconstraints=True, name=self.name)
        self.init_properties(obj, action)
        obj.recompute()
        return obj


@dataclass
class SvgPlaneFeature(SvgObjectFeature):
    def add_geometry(
        self, doc: Document, obj: DocumentObject, action: DocumentObject
    ) -> DocumentObject:
        if obj and (obj.TypeId != "Part::FeatureExt" or not getattr(obj, "SvgIsPlane", False)):
            doc.removeObject(obj.Name)
            obj = None

        if obj:
            self.update_common_props(obj, is_plane=True)
            obj.Shape = self.shape
            if App.GuiUp:
                self.set_style(obj.ViewObject)
            obj.recompute()
            return obj

        obj = doc.addObject("Part::FeatureExt", self.name)
        obj.addExtension("Part::AttachExtensionPython")
        obj.changeAttacherType("Attacher::AttachEnginePlane")
        self.init_properties(obj, action, is_plane=True)
        obj.Label = f"Plane.{self.label}"
        obj.Shape = self.shape
        if App.GuiUp:
            self.set_style(obj.ViewObject)
        obj.recompute()
        return obj

    def add_datum(
        self, doc: Document, obj: DocumentObject, action: DocumentObject
    ) -> DocumentObject:
        if obj and obj.TypeId != "App::Plane":
            doc.removeObject(obj.Name)
            obj = None

        edge = self.shape.Edges[0]
        center = edge.CenterOfGravity
        start = edge.firstVertex().CenterOfGravity
        end = edge.lastVertex().CenterOfGravity
        line_vec = end - start
        if line_vec.Length < 1e-6:
            return None

        z = App.Vector(0, 0, 1)
        x = App.Vector(line_vec).normalize()
        y = x.cross(z)
        placement = App.Placement(center, App.Rotation(x, z, y, "ZXY"))

        if obj:
            self.update_common_props(obj, is_plane=True)
            obj.Placement = placement
            obj.recompute()
            return obj

        obj = doc.addObject("App::Plane", self.name)
        obj.addExtension("Part::AttachExtensionPython")
        obj.changeAttacherType("Attacher::AttachEnginePlane")
        self.init_properties(obj, action, is_plane=True)
        obj.Label = f"DPlane.{self.label}.001"
        obj.Placement = placement
        obj.recompute()
        return obj

    def add_to_document(self, doc: Document, action: DocumentObject) -> DocumentObject:
        obj = doc.getObject(self.name)
        match self.options.get("PlaneMode", "Geometry"):
            case "Geometry":
                return self.add_geometry(doc, obj, action)
            case "Datum":
                return self.add_datum(doc, obj, action)
            case other:
                msg = f"Invalid Plane type: {other}"
                raise ValueError(msg)

    def set_style(self, vo: Gui.ViewProviderDocumentObject) -> None:
        # TODO: Use stylesheet colors
        appearance = vo.ShapeAppearance[0]
        appearance.DiffuseColor = (255, 204, 170, 100)
        vo.ShapeAppearance = appearance
        vo.LineColor = (255, 102, 0, 100)
        vo.Transparency = 85
