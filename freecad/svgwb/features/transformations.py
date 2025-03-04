# SPDX-License: LGPL-3.0-or-later
# (c) 2025 Frank David Martínez Muñoz. <mnesarco at gmail.com>

from Part import (  # type: ignore
    Shape,
    Face,
    Compound,
    Wire,
    Edge,
    Vertex,
    LineSegment,
    makePlane as make_plane,
    makeCompound as make_compound,
)

from FreeCAD import Vector, BoundBox  # type: ignore


def boundbox_to_rect(box: BoundBox) -> Wire:
    if not box.isValid():
        return Wire()

    MIN_LEN = 1e-6
    if box.XLength <= MIN_LEN or box.YLength <= MIN_LEN:
        return Wire()

    x0, y0, x1, y1 = box.XMin, box.YMin, box.XMax, box.YMax
    edges = [
        LineSegment(Vector(x0, y0), Vector(x0, y1)).toShape(),
        LineSegment(Vector(x0, y1), Vector(x1, y1)).toShape(),
        LineSegment(Vector(x1, y1), Vector(x1, y0)).toShape(),
        LineSegment(Vector(x1, y0), Vector(x0, y0)).toShape(),
    ]
    return Wire(edges)


def edge_to_plane(edge: Edge) -> Face:
    Z_DIR = Vector(0, 0, 1)
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


def shape_to_planes(shape: Shape) -> Face | Compound | None:
    if shape is None or not shape.isValid() or shape.isNull():
        return None

    planes = [edge_to_plane(e) for e in shape.Edges if not e.isClosed() and e.Length >= 1]
    match planes:
        case []:
            return None
        case [plane]:
            return plane
        case _:
            return make_compound(planes)


def shape_to_edge(shape: Shape) -> Edge | None:
    if shape is None or not shape.isValid() or shape.isNull():
        return None
    if edges := shape.Edges:
        return edges[0]
    return None


def shape_to_faces(shape: Shape) -> Face | Compound | None:
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
            faces = list(shape.Faces)
            wires = shape.Wires
            edges = shape.Edges
            for wire in wires:
                if all(wire not in f.Wires for f in faces) and wire.isClosed():
                    faces.append(Face(wire))
            for edge in edges:
                if all(edge not in w.Edges for w in wires) and edge.isClosed():
                    faces.append(Face(Wire([edge])))  # noqa: PERF401
            return make_compound(faces)


def shape_to_wires(shape: Shape) -> Wire | Compound | None:
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
            wires = list(shape.Wires)
            edges = shape.Edges
            for edge in edges:
                if all(edge not in w.Edges for w in wires):
                    wires.append(Wire([edge]))
            return make_compound(wires)


def shape_to_vertices(shape: Shape) -> Compound:
    return make_compound(shape.Vertexes)


def shape_to_edges(shape: Shape) -> Compound:
    return make_compound(shape.Edges)


def shape_to_center_of_gravity(shape: Shape) -> Vertex:
    return Vertex(shape.CenterOfGravity)


def shape_to_boundbox(shape: Shape) -> Wire:
    return boundbox_to_rect(shape.BoundBox)


def shape_to_boundbox_center(shape: Shape) -> Vertex:
    return Vertex(shape.BoundBox.Center)


def passthrough(shape: Shape) -> Shape:
    return shape
