# SPDX-License: LGPL-3.0-or-later
# (c) 2025 Frank David Martínez Muñoz. <mnesarco at gmail.com>

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, TypeAlias

import FreeCAD as App

if TYPE_CHECKING:
    from collections.abc import Callable
    from FreeCAD import Document, DocumentObject
    from Part import Shape
    import FreeCADGui as Gui
    from ..svg.database import SvgEntity

    ShapeTransformer: TypeAlias = Callable[[Shape], Shape]


def is_sketch_like(obj: DocumentObject) -> bool:
    return bool(obj and hasattr(obj, "delGeometries"))


@dataclass
class SvgObjectFeature:
    """Base DocumentObject creator/updater."""

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
        *,
        is_plane: bool = False,
    ) -> None:
        obj.Label = self.label or self.id or ""
        self.update_common_props(obj, is_plane=is_plane, action=action)

    def update_common_props(
        self,
        obj: DocumentObject,
        *,
        is_plane: bool = False,
        action: DocumentObject | None = None,
    ) -> None:
        self._update_ro_prop(obj, "App::PropertyString", "SvgPath", self.path or "")
        self._update_ro_prop(obj, "App::PropertyString", "SvgId", self.id or "")
        self._update_ro_prop(obj, "App::PropertyString", "SvgLabel", self.label or "")
        self._update_ro_prop(obj, "App::PropertyString", "SvgHref", self.href or "")
        self._update_ro_prop(obj, "App::PropertyString", "SvgTag", self.tag or "")
        self._update_ro_prop(obj, "App::PropertyBool", "SvgIsPlane", is_plane)
        self._update_ro_prop(obj, "App::PropertyLinkHidden", "SvgAction", action)
        if hasattr(obj, "Placement"):
            obj.setPropertyStatus("Placement", "Hidden")

    def _update_ro_prop(
        self,
        obj: DocumentObject,
        prop_type: str,
        name: str,
        value: object,
    ) -> None:
        try:
            obj.setPropertyStatus(name, "-ReadOnly")
            setattr(obj, name, value)
        except AttributeError:
            obj.addProperty(prop_type, name, "Svg", "")
        obj.setPropertyStatus(name, "ReadOnly")

    def add_to_document(self, doc: Document, action: DocumentObject) -> DocumentObject:
        pass


@dataclass
class SvgPartFeature(SvgObjectFeature):
    """Part::FeatureExt creator/updater."""

    def add_to_document(self, doc: Document, action: DocumentObject) -> DocumentObject:
        obj = doc.getObject(self.name)

        if is_sketch_like(obj):
            doc.removeObject(obj.Name)
            obj = None

        if obj:
            self.update_common_props(obj, action=action)
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
    """Sketch creator/updater."""

    def add_to_document(self, doc: Document, action: DocumentObject) -> DocumentObject:
        from Draft import make_sketch  # type: ignore

        obj = doc.getObject(self.name)

        if obj and not is_sketch_like(obj):
            doc.removeObject(obj.Name)
            obj = None

        if obj:
            self.update_common_props(obj, action=action)
            obj.delGeometries(list(range(obj.GeometryCount)))
            make_sketch(self.shape, autoconstraints=True, addTo=obj)
            obj.recompute()
            return obj

        obj = make_sketch(self.shape, autoconstraints=True, name=self.name)
        self.init_properties(obj, action)
        obj.recompute()
        return obj


@dataclass
class SvgSketchFastFeature(SvgObjectFeature):
    """Sketch creator/updater, faster version without constraints and planar checks."""

    def make_sketch(
        self,
        doc: Document,
        shape: Shape,
        obj: DocumentObject | None = None,
    ) -> DocumentObject:
        import Part

        if obj is None:
            obj = doc.addObject("Sketcher::SketchObject", self.name)

        for edge in shape.Edges:
            if isinstance(edge.Curve, Part.BezierCurve):
                obj.addGeometry(
                    edge.Curve.toBSpline(
                        edge.FirstParameter,
                        edge.LastParameter,
                    ),
                )
            else:
                obj.addGeometry(edge.Curve)

        return obj

    def add_to_document(self, doc: Document, action: DocumentObject) -> DocumentObject:
        obj = doc.getObject(self.name)

        if obj and not is_sketch_like(obj):
            doc.removeObject(obj.Name)
            obj = None

        if obj:
            self.update_common_props(obj, action=action)
            obj.delGeometries(list(range(obj.GeometryCount)))
            self.make_sketch(doc, self.shape, obj)
            obj.recompute()
            return obj

        obj = self.make_sketch(doc, self.shape)
        self.init_properties(obj, action)
        obj.recompute()
        return obj


@dataclass
class SvgPlaneFeature(SvgObjectFeature):
    """Plane/DatumPlane creator/updater."""

    def add_geometry(
        self,
        doc: Document,
        obj: DocumentObject | None,
        action: DocumentObject,
    ) -> DocumentObject:
        if obj and (obj.TypeId != "Part::FeatureExt"):
            doc.removeObject(obj.Name)
            obj = None

        if obj:
            self.update_common_props(obj, is_plane=True, action=action)
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
        self,
        doc: Document,
        obj: DocumentObject,
        action: DocumentObject,
    ) -> DocumentObject:
        if obj and obj.TypeId != "App::Plane":
            doc.removeObject(obj.Name)
            obj = None

        edge = self.shape.Edges[0]
        center = edge.CenterOfGravity
        start = edge.firstVertex().CenterOfGravity
        end = edge.lastVertex().CenterOfGravity
        line_vec = end - start
        MIN_SIZE = 1e-6  # noqa: N806
        if line_vec.Length < MIN_SIZE:
            return None

        z = App.Vector(0, 0, 1)
        x = App.Vector(line_vec).normalize()
        y = x.cross(z)
        placement = App.Placement(center, App.Rotation(x, z, y, "ZXY"))

        if obj:
            self.update_common_props(obj, is_plane=True, action=action)
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


@dataclass
class FeatureBuilder:
    """Adapter between SvgEntity and DocumentObject."""

    feature: type[SvgObjectFeature]
    transform: ShapeTransformer
    options: dict[str, Any] | None = None

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
        return None
