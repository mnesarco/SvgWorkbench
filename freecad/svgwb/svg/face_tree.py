# SPDX-License: LGPL-3.0-or-later
# (c) 2025 Frank David Martínez Muñoz. <mnesarco at gmail.com>

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from Part import Face # type: ignore


class FaceTreeNode:
    """
    Tree structure holding one-closed-wire faces sorted after each others enclosure.

    This class only works with faces that have exactly one closed wire
    """

    face: Face
    children: list[FaceTreeNode]
    name: str

    def __init__(self, face:Face=None, name:str="root") -> None:
        super().__init__()
        self.face = face
        self.name = name
        self.children = []

    def insert(self, face: Face, name: str) -> None:
        """
        Take a single-wire face, and inserts it into the tree.

        Insertion depends on its enclosure in/of in already added faces

        Parameters
        ----------
        face : Part.Face
               single closed wire face to be added to the tree
        name : str
               face identifier

        """
        new = None
        inserted = False
        for node in self.children:
            if node.face.Area > face.Area:
                # new face could be encompassed
                if face.distToShape(node.face)[0] == 0.0 and \
                        face.Wires[0].distToShape(node.face.Wires[0])[0] != 0.0:
                    # it is encompassed - enter next tree layer
                    node.insert(face, name)
                    inserted = True
            # new face could encompass
            elif node.face.distToShape(face)[0] == 0.0 and \
                    node.face.Wires[0].distToShape(face.Wires[0])[0] != 0.0:
                # it does encompass the current child nodes face
                # create new node from face
                if not new:
                    new = FaceTreeNode(face, name)
                # swap the new one with the child node
                self.children.remove(node)
                self.children.append(new)
                # add former child node as child to the new node
                new.children.append(node)
        if not new and not inserted:
            # the face is not encompassing and is not encompassed
            # (from) any other face, we add it as new child
            new = FaceTreeNode(face, name)
            self.children.append(new)

    def make_cuts(self) -> None:
        """
        Recursively traverse the tree and cuts all faces in even
        numbered tree levels with their direct childrens faces.

        Additionally the tree is shrunk by removing the odd numbered
        tree levels.
        """  # noqa: D205
        result = self.face
        if not result:
            for node in self.children:
                node.make_cuts()
        else:
            new_children = []
            for node in self.children:
                result = result.cut(node.face)
                for subnode in node.children:
                    subnode.make_cuts()
                    new_children.append(subnode)
            self.children = new_children
            self.face = result

    def flatten(self) -> list[Face]:
        """Create a flattened list of face-name tuples from the FaceTree."""
        result = []
        if self.face:
            result.append(self.face)
        for node in self.children:
            result.extend(node.flatten())
        return result
