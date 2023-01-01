from warnings import warn

import numpy as np

import shapely
from shapely import _is_ccw_geos_3_7
from shapely.decorators import vectorize_geom
from shapely.errors import ShapelyDeprecationWarning
from shapely.geos import geos_version

__all__ = [
    "is_ccw",
    "force_ccw",
    "is_ccw_impl",
]


def is_ccw_impl(name=None):
    """This function is deprecated, it is here only for backwards compatibility"""
    warn(
        "Please call `shapely.is_ccw` directly."
        "This function serves no purpose and will be removed in a future version",
        ShapelyDeprecationWarning,
        stacklevel=2,
    )
    return shapely.is_ccw


def signed_area(ring):
    """Return the signed area enclosed by a ring in linear time using the
    algorithm at: https://web.archive.org/web/20080209143651/http://cgafaq.info:80/wiki/Polygon_Area
    """
    coords = np.array(ring.coords)[:, :2]
    xs, ys = np.vstack([coords, coords[1]]).T
    return np.sum(xs[1:-1] * (ys[2:] - ys[:-2])) / 2.0


def _is_ccw_fallback(geometry, **kwargs):
    if kwargs:
        raise NotImplementedError(
            "is_ccw is not implemented with **kwargs using GEOS < 3.7"
        )
    if geometry is None:
        return False
    elif not hasattr(geometry, "geom_type"):
        return np.array([_is_ccw_fallback(g) for g in geometry], dtype=bool)
    elif geometry.geom_type in ["LinearRing", "LineString"]:
        if len(geometry.coords) < 4:
            return False
        else:
            return signed_area(geometry) >= 0.0
    else:
        return False


is_ccw = _is_ccw_geos_3_7 if geos_version >= (3, 7, 0) else _is_ccw_fallback


@vectorize_geom
def force_ccw(geometry, ccw: bool = True):
    """A properly oriented copy of the given geometry.

    Forces (Multi)Polygons to use a counter-clockwise orientation for their exterior ring,
    and a clockwise orientation for their interior rings (if ccw=True).
    Non-polygonal geometries are returned unchanged.

    Parameters
    ----------
    geometry : Geometry or array_like
        The original geometry. Either a Polygon, MultiPolygon, or GeometryCollection.
    ccw : bool or array_like, default True
        If True, force counter-clockwise of outer rings, and clockwise inner-rings.
        Otherwise, force clockwise of outer rings, and counter-clockwise inner-rings.

    Returns
    -------
    Geometry or array_like
    """
    if geometry.geom_type in ["MultiPolygon", "GeometryCollection"]:
        return geometry.__class__(list(force_ccw(geometry.geoms, ccw)))
    if geometry.geom_type == "Polygon":
        rings = [geometry.exterior, *geometry.interiors]
        reverse_rings = is_ccw(rings)
        reverse_rings[0] = not reverse_rings[0]
        if ccw:
            reverse_rings = np.logical_not(reverse_rings)
        rings = [
            ring if reverse_ring else list(ring.coords)[::-1]
            for ring, reverse_ring in zip(rings, reverse_rings)
        ]
        return geometry.__class__(rings[0], rings[1:])
    return geometry
