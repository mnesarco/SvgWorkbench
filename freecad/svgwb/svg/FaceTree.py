# SPDX-License: LGPL-3.0-or-later
# (c) 2025 Frank David Martínez Muñoz. <mnesarco at gmail.com>
from __future__ import annotations

from dataclasses import dataclass

from Part import (  # type: ignore
    Arc,
    BezierCurve,
    BSplineCurve,
    Ellipse,
    Face,
    LineSegment,
    OCCError,
    Shape,
)

class FaceTreeNode:
    '''Building Block of a tree structure holding one-closed-wire faces 
       sorted after each others enclosure.
       This class only works with faces that have exactly one closed wire
    '''
    face     : Face
    children : list
    name     : str

    
    def __init__(self, face=None, name="root"):
        super().__init__()
        self.face = face
        self.name = name
        self.children = [] 

      
    def insert (self, face : Face, name : str):
        ''' takes a single-wire face, and inserts it into the tree 
            depending on its enclosure in/of in already added faces

            Parameters
            ----------
            face : Part.Face
                   single closed wire face to be added to the tree
            name : str
                   face identifier       
        ''' 
        new = None
        inserted = False
        for node in self.children:
            if  node.face.Area > face.Area:
                # new face could be encompassed
                if face.distToShape(node.face)[0] == 0.0:
                    # it is encompassed - enter next tree layer
                    node.insert(face, name)
                    inserted = True
            else:
                # new face could encompass
                if node.face.distToShape(face)[0] == 0.0:
                    # it does encompass the current child nodes face
                    #create new node from face
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

     
    def makeCuts(self):
        ''' recursively traverse the tree and cuts all faces in even 
            numbered tree levels with their direct childrens faces. 
            Additionally the tree is shrunk by removing the odd numbered 
            tree levels.                 
        '''
        result = self.face
        if not result:
            for node in self.children:
                node.makeCuts()
        else:
            new_children = []
            for node in self.children:
                result = result.cut(node.face)
                for subnode in node.children:
                    subnode.makeCuts()
                    new_children.append(subnode)
            self.children = new_children
            self.face = result

                
    def traverse(self, function):
        function(self)
        for node in self.children:
            node.traverse(function) 

           
    def flatten(self):
        ''' creates a flattened list of face-name tuples from the facetree
            content
        '''
        result = []
        if self.face:
            result.append(self.face)
        for node in self.children:
            result.extend(node.flatten())
        return result  
        
