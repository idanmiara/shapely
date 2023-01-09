from typing import Union

import numpy as np

import shapely
from shapely import lib
from shapely.lib import Geometry

__all__ = [
    "transform",
    "_transform_multi_vec",
    "_transform",
    "_transform2_multi_vec",
    "_transform2",
    "count_coordinates",
    "get_coordinates",
    "set_coordinates",
]

from shapely.errors import GeometryTypeError


def transform(
    geometry,
    transformation,
    include_z: Union[bool, int] = False,
    single_vec: bool = True,
    rebuild: bool = False,
):
    """Returns a copy of a geometry array with a function applied to its coordinates.

    With the default of ``rebuild=False``, ``include_z=False``,
    all returned geometries will be two-dimensional;
    the third dimension will be discarded, if present.
    When specifying ``rebuild=False``, ``include_z=True``,
    the returned geometries preserve the dimensionality of the
    respective input geometries.
    When specifying ``rebuild=True`` the output geometries
    will get rebuilt from the transformation output

    Parameters
    ----------
    geometry : Geometry or array_like
    transformation : function
        A function that transforms coordinates, in ``single_vec=True`` mode:
        the function transforms a (N, 2) or (N, 3) ndarray of float64 to
        another (N, 2) or (N, 3) ndarray of float64.
        in ``single_vec=False`` mode: the function transform 2 or 3 N ndarray
        of float64 to another 2 or 3 ndarray of float64.
        With the default ``rebuild=False``, the transform function must also
        return N sized array(s).
    include_z : bool or int, default False
        If True | 1, include the third dimension in the coordinates array
            that is passed to the ``transformation`` function. If a
            geometry has no third dimension, the z-coordinates passed to the
            function will be NaN.
        If False | 0, The third-dimension of the geometries (if exist),
            would not be included in the input to transform function.
        If -1 Include the third dimension in the coordinates array that is passed to the
            ``transformation`` function only if the geoemtries are three-dimensional.
    single_vec: bool, default True
        How to pass coordinates to the transform function:
        if True, pass them as a single argument
            (2D array in case of multiple coordinates)
        Otherwise, Pass them as separate x, y(, z) arguments
            (separate 1D arrays in case of multiple coordinates)
    rebuild: bool, default False
        If False, output geometries will preserve the coordinate number and
            dimnensionality as the input geometries (but in include_z=False,
            two-dimension geometries are always returned).
        Otherwise, output geometries will get rebuilt from the transformation
            output, so they might have different number of coordinate or
            a different coordiante-dimensionality.

    Examples
    --------
    >>> from shapely import LineString, Point
    >>> transform(Point(0, 0), lambda x: x + 1)
    <POINT (1 1)>
    >>> transform(LineString([(2, 2), (4, 4)]), lambda x: x * [2, 3])
    <LINESTRING (4 6, 8 12)>
    >>> transform(None, lambda x: x) is None
    True
    >>> transform([Point(0, 0), None], lambda x: x).tolist()
    [<POINT (0 0)>, None]

    By default, the third dimension is ignored:

    >>> transform(Point(0, 0, 0), lambda x: x + 1)
    <POINT (1 1)>
    >>> transform(Point(0, 0, 0), lambda x: x + 1, include_z=True)
    <POINT Z (1 1 1)>

    An identity function applicable to both types of input with single_vec=False

    >>> g1 = LineString([(1, 2), (3, 4)])

    >>> transform(g1, lambda x, y, z=None: tuple(filter(None, [x, y, z])), single_vec=False)
    <LINESTRING (1 2, 3 4)>

    example of another lambda expression:

    >>> transform(g1, lambda x, y, z=None: (x+1.0, y+1.0), single_vec=False)
    <LINESTRING (2 3, 4 5)>

    Using pyproj >= 2.1, the following example will accurately project Shapely geometries
    It transforms from EPSG:4326 (WGS84 log/lat) to EPSG:32618 (WGS84 UTM 18 North)
    Note: always_xy kwarg is required as Shapely geometries only support X,Y coordinate ordering.

    >>> try:
    ...     import pyproj
    ...     project = pyproj.Transformer.from_crs(4326, 32618, always_xy=True).transform
    ...     p = transform(Point(-75, 50), project, single_vec=False)
    ...     assert (round(p.x), round(p.y)) == (500000, 5538631)
    ... except ImportError:
    ...     pass
    """
    if include_z == -1:
        include_z = shapely.get_coordinate_dimension(geometry) == 3
    if rebuild:
        transform_wrapper = _transform2 if single_vec else _transform2_multi_vec
        vectorize = not isinstance(geometry, Geometry)
    else:
        transform_wrapper = _transform if single_vec else _transform_multi_vec
        vectorize = False
        if not np.isscalar(include_z):
            if np.all(include_z == include_z[0]):
                include_z = include_z[0]
            else:
                vectorize = True
    if vectorize:
        transform_wrapper = np.frompyfunc(transform_wrapper, 3, 1)

    return transform_wrapper(
        geometry,
        transformation,
        include_z,
    )


def _transform(geometry, transformation, include_z: bool = False):
    geometry_arr = np.array(geometry, dtype=np.object_)  # makes a copy
    coordinates = lib.get_coordinates(geometry_arr, include_z, False)
    new_coordinates = transformation(coordinates)
    # check the array to yield understandable error messages
    if not isinstance(new_coordinates, np.ndarray):
        raise ValueError("The provided transformation did not return a numpy array")
    if new_coordinates.dtype != np.float64:
        raise ValueError(
            "The provided transformation returned an array with an unexpected "
            f"dtype ({new_coordinates.dtype}, but expected {coordinates.dtype})"
        )
    if new_coordinates.shape != coordinates.shape:
        # if the shape is too small we will get a segfault
        raise ValueError(
            "The provided transformation returned an array with an unexpected "
            f"shape ({new_coordinates.shape}, but expected {coordinates.shape})"
        )
    geometry_arr = lib.set_coordinates(geometry_arr, new_coordinates)
    if geometry_arr.ndim == 0 and not isinstance(geometry, np.ndarray):
        return geometry_arr.item()
    return geometry_arr


def _transform_multi_vec(geometry, transformation, include_z: bool = False):
    try:
        # First we try to apply func to x, y, z vectors.
        return _transform(
            geometry,
            lambda coords: np.array(transformation(*coords.T)).T,
            include_z=include_z,
        )
    except Exception:
        # A func that assumes x, y, z are single values will likely raise a
        # TypeError or a ValueError in which case we'll try again.
        return _transform(
            geometry,
            lambda coords: np.array([transformation(*c) for c in coords]),
            include_z=include_z,
        )


def _transform2(
    geometry,
    transformation,
    include_z: bool = False,
):
    if geometry.is_empty:
        return geometry
    if geometry.geom_type in ("Point", "LineString", "LinearRing", "Polygon"):
        return transform_rebuild_single_part(
            geometry, transformation, include_z=include_z
        )
    elif (
        geometry.geom_type.startswith("Multi")
        or geometry.geom_type == "GeometryCollection"
    ):
        return type(geometry)(
            [
                _transform2(part, transformation, include_z=include_z)
                for part in geometry.geoms
            ]
        )
    else:
        raise GeometryTypeError(f"Type {geometry.geom_type!r} not recognized")


def _transform2_multi_vec(
    geometry,
    transformation,
    include_z: bool = False,
):
    if geometry.is_empty:
        return geometry
    if geometry.geom_type in ("Point", "LineString", "LinearRing", "Polygon"):
        try:
            # First we try to apply func to x, y, z vectors.
            return transform_rebuild_single_part(
                geometry,
                lambda coords: np.array(transformation(*np.array(coords).T)).T,
                include_z=include_z,
            )
        except Exception:
            # A func that assumes x, y, z are single values will likely raise a
            # TypeError or a ValueError in which case we'll try again.
            return transform_rebuild_single_part(
                geometry,
                lambda coords: [transformation(*c) for c in coords],
                include_z=include_z,
            )
    elif (
        geometry.geom_type.startswith("Multi")
        or geometry.geom_type == "GeometryCollection"
    ):
        return type(geometry)(
            [
                _transform2_multi_vec(part, transformation, include_z=include_z)
                for part in geometry.geoms
            ]
        )
    else:
        raise GeometryTypeError(f"Type {geometry.geom_type!r} not recognized")


def transform_rebuild_single_part(geometry, transformation, include_z: bool = False):
    """helper function for transform2, for a single part geometries"""
    if geometry.geom_type in ("Point", "LineString", "LinearRing"):
        return type(geometry)(
            transformation(get_coordinates(geometry, include_z=include_z))
        )
    elif geometry.geom_type == "Polygon":
        shell = type(geometry.exterior)(
            transformation(get_coordinates(geometry.exterior, include_z=include_z))
        )
        holes = list(
            type(ring)(transformation(get_coordinates(ring, include_z=include_z)))
            for ring in geometry.interiors
        )
        return type(geometry)(shell, holes)


def count_coordinates(geometry):
    """Counts the number of coordinate pairs in a geometry array.

    Parameters
    ----------
    geometry : Geometry or array_like

    Examples
    --------
    >>> from shapely import LineString, Point
    >>> count_coordinates(Point(0, 0))
    1
    >>> count_coordinates(LineString([(2, 2), (4, 2)]))
    2
    >>> count_coordinates(None)
    0
    >>> count_coordinates([Point(0, 0), None])
    1
    """
    return lib.count_coordinates(np.asarray(geometry, dtype=np.object_))


def get_coordinates(geometry, include_z=False, return_index=False):
    """Gets coordinates from a geometry array as an array of floats.

    The shape of the returned array is (N, 2), with N being the number of
    coordinate pairs. With the default of ``include_z=False``, three-dimensional
    data is ignored. When specifying ``include_z=True``, the shape of the
    returned array is (N, 3).

    Parameters
    ----------
    geometry : Geometry or array_like
    include_z : bool, default False
        If, True include the third dimension in the output. If a geometry
        has no third dimension, the z-coordinates will be NaN.
    return_index : bool, default False
        If True, also return the index of each returned geometry as a separate
        ndarray of integers. For multidimensional arrays, this indexes into the
        flattened array (in C contiguous order).

    Examples
    --------
    >>> from shapely import LineString, Point
    >>> get_coordinates(Point(0, 0)).tolist()
    [[0.0, 0.0]]
    >>> get_coordinates(LineString([(2, 2), (4, 4)])).tolist()
    [[2.0, 2.0], [4.0, 4.0]]
    >>> get_coordinates(None)
    array([], shape=(0, 2), dtype=float64)

    By default the third dimension is ignored:

    >>> get_coordinates(Point(0, 0, 0)).tolist()
    [[0.0, 0.0]]
    >>> get_coordinates(Point(0, 0, 0), include_z=True).tolist()
    [[0.0, 0.0, 0.0]]

    When return_index=True, indexes are returned also:

    >>> geometries = [LineString([(2, 2), (4, 4)]), Point(0, 0)]
    >>> coordinates, index = get_coordinates(geometries, return_index=True)
    >>> coordinates.tolist(), index.tolist()
    ([[2.0, 2.0], [4.0, 4.0], [0.0, 0.0]], [0, 0, 1])
    """
    return lib.get_coordinates(
        np.asarray(geometry, dtype=np.object_), include_z, return_index
    )


def set_coordinates(geometry, coordinates):
    """Adapts the coordinates of a geometry array in-place.

    If the coordinates array has shape (N, 2), all returned geometries
    will be two-dimensional, and the third dimension will be discarded,
    if present. If the coordinates array has shape (N, 3), the returned
    geometries preserve the dimensionality of the input geometries.

    .. warning::

        The geometry array is modified in-place! If you do not want to
        modify the original array, you can do
        ``set_coordinates(arr.copy(), newcoords)``.

    Parameters
    ----------
    geometry : Geometry or array_like
    coordinates: array_like

    See Also
    --------
    transform : Returns a copy of a geometry array with a function applied to its
        coordinates.

    Examples
    --------
    >>> from shapely import LineString, Point
    >>> set_coordinates(Point(0, 0), [[1, 1]])
    <POINT (1 1)>
    >>> set_coordinates([Point(0, 0), LineString([(0, 0), (0, 0)])], [[1, 2], [3, 4], [5, 6]]).tolist()
    [<POINT (1 2)>, <LINESTRING (3 4, 5 6)>]
    >>> set_coordinates([None, Point(0, 0)], [[1, 2]]).tolist()
    [None, <POINT (1 2)>]

    Third dimension of input geometry is discarded if coordinates array does
    not include one:

    >>> set_coordinates(Point(0, 0, 0), [[1, 1]])
    <POINT (1 1)>
    >>> set_coordinates(Point(0, 0, 0), [[1, 1, 1]])
    <POINT Z (1 1 1)>
    """
    geometry_arr = np.asarray(geometry, dtype=np.object_)
    coordinates = np.atleast_2d(np.asarray(coordinates)).astype(np.float64)
    if coordinates.ndim != 2:
        raise ValueError(
            "The coordinate array should have dimension of 2 "
            f"(has {coordinates.ndim})"
        )
    n_coords = lib.count_coordinates(geometry_arr)
    if (coordinates.shape[0] != n_coords) or (coordinates.shape[1] not in {2, 3}):
        raise ValueError(
            f"The coordinate array has an invalid shape {coordinates.shape}"
        )
    lib.set_coordinates(geometry_arr, coordinates)
    if geometry_arr.ndim == 0 and not isinstance(geometry, np.ndarray):
        return geometry_arr.item()
    return geometry_arr
