"""
Plot single geometries using Matplotlib.

Note: this module is experimental, and mainly targeting (interactive)
exploration, debugging and illustration purposes.

"""
from typing import Optional, TYPE_CHECKING, Union

import numpy as np

import shapely

if TYPE_CHECKING:
    from shapely import LinearRing, LineString, MultiLineString, MultiPolygon, Polygon
    from shapely.geometry.base import BaseGeometry


def _default_ax():
    import matplotlib.pyplot as plt

    ax = plt.gca()
    ax.grid(True)
    ax.set_aspect("equal")
    return ax


def _path_from_polygon(polygon: "Polygon"):
    from matplotlib.path import Path

    path = Path.make_compound_path(
        Path(np.asarray(polygon.exterior.coords)[:, :2]),
        *[Path(np.asarray(ring.coords)[:, :2]) for ring in polygon.interiors],
    )
    return path


def plot_polygon(
    polygon: Union["Polygon", "MultiPolygon"],
    ax=None,
    add_points: bool = True,
    color=None,
    facecolor=None,
    edgecolor=None,
    linewidth: Optional[float] = None,
    **kwargs
):
    """
    Plot a (Multi)Polygon.

    Note: this function is experimental, and mainly targetting (interactive)
    exploration, debugging and illustration purposes.

    Parameters
    ----------
    polygon : shapely.Polygon or shapely.MultiPolygon
    ax : matplotlib Axes, default None
        The axes on which to draw the plot. If not specified, will get the
        current active axes or create a new figure.
    add_points : bool, default True
        If True, also plot the coordinates (vertices) as points.
    color : matplotlib color specification
        Color for both the polygon fill (face) and boundary (edge). By default,
        the fill is using an alpha of 0.3. You can specify `facecolor` and
        `edgecolor` separately for greater control.
    facecolor : matplotlib color specification
        Color for the polygon fill.
    edgecolor : matplotlib color specification
        Color for the polygon boundary.
    linewidth : float
        The line width for the polygon boundary.
    **kwargs
        Additional keyword arguments passed to the matplotlib Patch.

    Returns
    -------
    Matplotlib artist (PathPatch)
    """
    if ax is None:
        ax = _default_ax()

    from matplotlib import colors
    from matplotlib.patches import PathPatch
    from matplotlib.path import Path

    if color is None:
        color = "C0"
    color = colors.to_rgba(color)

    if facecolor is None:
        facecolor = list(color)
        facecolor[-1] = 0.3
        facecolor = tuple(facecolor)

    if edgecolor is None:
        edgecolor = color

    if isinstance(polygon, shapely.MultiPolygon):
        path = Path.make_compound_path(
            *[_path_from_polygon(poly) for poly in polygon.geoms]
        )
    else:
        path = _path_from_polygon(polygon)
    patch = PathPatch(
        path, facecolor=facecolor, edgecolor=edgecolor, linewidth=linewidth, **kwargs
    )
    ax.add_patch(patch)
    ax.autoscale_view()

    if add_points:
        line = plot_points(polygon, ax=ax, color=color)
        return patch, line

    return patch


def plot_line(
    line: Union["LineString", "MultiLineString", "LinearRing"],
    ax=None,
    add_points: bool = True,
    color=None,
    linewidth: float = 2,
    **kwargs
):
    """
    Plot a (Multi)LineString/LinearRing.

    Note: this function is experimental, and mainly targetting (interactive)
    exploration, debugging and illustration purposes.

    Parameters
    ----------
    line : shapely.LineString or shapely.LinearRing
    ax : matplotlib Axes, default None
        The axes on which to draw the plot. If not specified, will get the
        current active axes or create a new figure.
    add_points : bool, default True
        If True, also plot the coordinates (vertices) as points.
    color : matplotlib color specification
        Color for the line (edgecolor under the hood) and pointes.
    linewidth : float, default 2
        The line width for the polygon boundary.
    **kwargs
        Additional keyword arguments passed to the matplotlib Patch.

    Returns
    -------
    Matplotlib artist (PathPatch)
    """
    if ax is None:
        ax = _default_ax()

    from matplotlib.patches import PathPatch
    from matplotlib.path import Path

    if color is None:
        color = "C0"

    if isinstance(line, shapely.MultiLineString):
        path = Path.make_compound_path(
            *[Path(np.asarray(mline.coords)[:, :2]) for mline in line.geoms]
        )
    else:
        path = Path(np.asarray(line.coords)[:, :2])

    patch = PathPatch(
        path, facecolor="none", edgecolor=color, linewidth=linewidth, **kwargs
    )
    ax.add_patch(patch)
    ax.autoscale_view()

    if add_points:
        line = plot_points(line, ax=ax, color=color)
        return patch, line

    return patch


def plot_points(geom: "BaseGeometry", ax=None, color=None, marker: str = "o", **kwargs):
    """
    Plot a Point/MultiPoint or the vertices of any other geometry type.

    Parameters
    ----------
    geom : shapely.Geometry
        Any shapely Geometry object, from which all vertices are extracted
        and plotted.
    ax : matplotlib Axes, default None
        The axes on which to draw the plot. If not specified, will get the
        current active axes or create a new figure.
    color : matplotlib color specification
        Color for the filled points. You can use `markeredgecolor` and
        `markeredgecolor` to have different edge and fill colors.
    marker : str, default "o"
        The matplotlib marker for the points.
    **kwargs
        Additional keyword arguments passed to matplotlib `plot` (Line2D).

    Returns
    -------
    Matplotlib artist (Line2D)
    """
    if ax is None:
        ax = _default_ax()

    coords = shapely.get_coordinates(geom)
    (line,) = ax.plot(
        coords[:, 0], coords[:, 1], linestyle="", marker=marker, color=color, **kwargs
    )
    return line
