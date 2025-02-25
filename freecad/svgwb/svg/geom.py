# SPDX-License: LGPL-3.0-or-later
# (c) 2025 Frank David Martínez Muñoz. <mnesarco at gmail.com>

from DraftVecUtils import angle as angle_between_vectors  # type: ignore
from FreeCAD import Vector, Matrix  # type: ignore

import math

from Draft import precision as draft_precision  # type: ignore
from Part import OCCError, Wire, Edge, Compound  # type: ignore
from Part import __sortEdges__ as sort_edges  # type: ignore

# draft precision for calculations
DraftPrecision = draft_precision()

def precision_step(precision: int = DraftPrecision):
    """
    Return the smallest possible fraction or step size for a given precision.
    Since precision is defined as 'relevant decimal digits behind the comma' 
    the outcome for eg. precision = 3 is 0,001.
     
    Parameters
    ----------
    precision : int
                relevant digits behind comma
    Returns
    -------
    float
        smallest possible fraction or step for the given precision.

    """
    return 10 ** (-precision)

def arc_end_to_center(
    last_v: Vector,
    current_v: Vector,
    rx: float,
    ry: float,
    x_rotation: float = 0.0,
    correction: bool = False,
):
    """Calculate the possible centers for an arc in endpoint parameterization.

    Calculate (positive and negative) possible centers for an arc given in
    ``endpoint parametrization``.
    See http://www.w3.org/TR/SVG/implnote.html#ArcImplementationNotes

    the sweep_flag is interpreted as: sweep_flag <==>  arc is traveled clockwise

    Parameters
    ----------
    last_v : Base::Vector3
        First point of the arc.
    current_v : Base::Vector3
        End point (current) of the arc.
    rx : float
        Radius of the ellipse, semi-major axis in the X direction.
    ry : float
        Radius of the ellipse, semi-minor axis in the Y direction.
    x_rotation : float, optional
        Default is 0. Rotation around the Z axis, in radians (CCW).
    correction : bool, optional
        Default is `False`. If it is `True`, the radii will be scaled
        by a factor.

    Returns
    -------
    list, (float, float)
        A tuple that consists of one list, and a tuple of radii.
    [(positive), (negative)], (rx, ry)
        The first element of the list is the positive tuple,
        the second is the negative tuple.
    [(Base::Vector3, float, float),
    (Base::Vector3, float, float)], (float, float)
        Types
    [(v_center+, angle1+, angle_delta+),
    (v_center-, angle1-, angle_delta-)], (rx, ry)
        The first element of the list is the positive tuple,
        consisting of center, angle, and angle increment;
        the second element is the negative tuple.
    """
    # scale_fact_sign = 1 if (large_flag != sweep_flag) else -1
    rx = float(rx)
    ry = float(ry)
    v0 = last_v.sub(current_v)
    v0.multiply(0.5)
    m1 = Matrix()
    m1.rotateZ(-x_rotation)  # eq. 5.1
    v1 = m1.multiply(v0)
    if correction:
        e_param = v1.x**2 / rx**2 + v1.y**2 / ry**2
        if e_param > 1:
            ep_root = math.sqrt(e_param)
            rx = ep_root * rx
            ry = ep_root * ry
    denom = rx**2 * v1.y**2 + ry**2 * v1.x**2
    numer = rx**2 * ry**2 - denom
    results = []

    # If the division is very small, set the scaling factor to zero,
    # otherwise try to calculate it by taking the square root
    if abs(numer / denom) < precision_step(DraftPrecision):
        scale_fact_pos = 0
    else:
        try:
            scale_fact_pos = math.sqrt(numer / denom)
        except ValueError:
            scale_fact_pos = 0

    # Calculate two values because the square root may be positive or negative
    for scale_fact_sign in (1, -1):
        scale_fact = scale_fact_pos * scale_fact_sign
        # Step2 eq. 5.2
        vcx1 = Vector(v1.y * rx / ry, -v1.x * ry / rx, 0).multiply(scale_fact)
        m2 = Matrix()
        m2.rotateZ(x_rotation)
        center_off = current_v.add(last_v)
        center_off.multiply(0.5)
        v_center = m2.multiply(vcx1).add(center_off)  # Step3 eq. 5.3
        # angle1 = Vector(1, 0, 0).getAngle(Vector((v1.x - vcx1.x)/rx,
        #                                          (v1.y - vcx1.y)/ry,
        #                                          0))  # eq. 5.5
        # angle_delta = Vector((v1.x - vcx1.x)/rx,
        #                     (v1.y - vcx1.y)/ry,
        #                     0).getAngle(Vector((-v1.x - vcx1.x)/rx,
        #                                        (-v1.y - vcx1.y)/ry,
        #                                        0))  # eq. 5.6
        # we need the right sign for the angle
        angle1 = angle_between_vectors(
            Vector(1, 0, 0), Vector((v1.x - vcx1.x) / rx, (v1.y - vcx1.y) / ry, 0)
        )  # eq. 5.5
        angle_delta = angle_between_vectors(
            Vector((v1.x - vcx1.x) / rx, (v1.y - vcx1.y) / ry, 0),
            Vector((-v1.x - vcx1.x) / rx, (-v1.y - vcx1.y) / ry, 0),
        )  # eq. 5.6
        results.append((v_center, angle1, angle_delta))

    return results, (rx, ry)



def make_wire(
    path: list[Edge],
    check_closed: bool = False,
    dont_try: bool = False,
):
    """Try to make a wire out of the list of edges.

    If the wire functions fail or the wire is not closed,
    if required the TopoShapeCompoundPy::connectEdgesToWires()
    function is used.

    Parameters
    ----------
    path : Part.Edge
        A collection of edges
    check_closed : bool, optional
        Default is `False`.
    dont_try : bool, optional
        Default is `False`. If it's `True` it won't try to check
        for a closed path.

    Returns
    -------
    Part::Wire
        A wire created from the ordered edges.
    Part::Compound
        A compound made of the edges, but unable to form a wire.
    """
    if not dont_try:
        try:
            sh = Wire(sort_edges(path))
            # sh = Wire(path)
            isok = (not check_closed) or sh.isClosed()
            if len(sh.Edges) != len(path):
                isok = False
        # BRep_API: command not done
        except OCCError:
            isok = False
    if dont_try or not isok:
        # Code from wmayer forum p15549 to fix the tolerance problem
        # original tolerance = 0.00001
        comp = Compound(path)
        _sh = comp.connectEdgesToWires(False, precision_step(SVGPrecision))
        sh = _sh.Wires[0]
        if len(sh.Edges) != len(path):
            sh = comp
    return sh

    
def equals(
	u: Vector,
    v: Vector,
	precision: int = -1
):
    """Return False if each delta of the two vectors components is zero.

    Due to rounding errors, a delta is probably never going to be
    exactly zero. Therefore, it rounds the element by the number
    of decimals specified in the `precision` parameter - if `precision`
    is not set the svg import precision preference is used. 
    It then compares the rounded coordinates against zero.

    Parameters
    ----------
    u : Base::Vector3
        The first vector to compare
    v : Base::Vector3
        The second vector to compare  (comparison is commutative)
    precision : int
                mathematical precision - if not set draft precision 
                preference is used.

    Returns
    -------
    bool
        `True` if each of the coordinate deltas is smaller than precision.
        `False` otherwise.
    """
    delta = u.sub(v)
    if (precision == -1):
        precision = DraftPrecision()
    x = round(delta.x, precision)
    y = round(delta.y, precision)
    z = round(delta.z, precision)
    return (x == 0 and y == 0 and z == 0)

