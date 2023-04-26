import numpy as np
from skimage.measure import find_contours
import rasterio
import rasterio.mask
import shapely.ops
from shapely.geometry import LineString, Point, MultiPoint, Polygon, MultiLineString, GeometryCollection, LinearRing, MultiPolygon

def coords_to_gdal_transform(x, y):
    ni, nj = y.size, x.size
    dx = x[1]-x[0]
    dy = y[1]-y[0]
    return rasterio.Affine(dx, 0, x[0]-dx/2, 0, dy, y[0]-dy/2)


def find_contours2(coords, values, level, **kw):
    """Like find_contours, but return line in coordinate values
    """
    contours = find_contours(values, level, **kw)
    contours2 = []
    x, y = coords
    dx, dy = x[1] - x[0], y[1]-y[0]
    for c in contours:
        ii, jj = np.array(c).T
        xx, yy = x[0]+jj*dx, y[0]+ii*dy
        line = np.array((xx, yy)).T
        contours2.append(line)
    return contours2


def mask_to_polygon(coords, mask, tol=None, minarea=0):
    x, y = coords
    mask2 = mask + 0.
    mask2[:,[0,-1]] = 0  # close all contours
    mask2[[0,-1],:] = 0
    contours = find_contours2(coords, mask2, level=0.5)

    rings = [LinearRing(c) for c in contours]

    if tol is not None:
        rings = [r.simplify(tol) for r in rings]

    exteriors = [Polygon(p) for p in rings if p.is_ccw]
    interiors = [Polygon(p) for p in rings if not p.is_ccw]

    if minarea:
        exteriors = [p for p in exteriors if p.area > minarea]
        interiors = [p for p in interiors if p.area > minarea]

    mpoly = shapely.ops.unary_union(exteriors)
    return mpoly.symmetric_difference(MultiPolygon(interiors))


def polygon_to_mask(geom, coords, all_touched=False):
    """return a numpy mask array which is True when it intersects with geometry

    all_touched : boolean, optional
        If True, all pixels touched by geometries will be burned in.  If
        false, only pixels whose center is within the polygon or that
        are selected by Bresenham's line algorithm will be burned in.
    """
    geoms = getattr(geom, 'geoms', [geom])
    shape = coords[1].size, coords[0].size
    transform = coords_to_gdal_transform(*coords)
    return rasterio.mask.geometry_mask(geoms, shape, transform, invert=True, all_touched=all_touched)


def polygon_to_fractional_mask(geom, coords, subgrid=None):
    """return a float-valued numpy array (values between 0 and 1) to indicate the fraction of grid pixel belonging to a country.

    geom: shapely geometry (Polygon or MultiPolygon)
    coords: (lon, lat) defining the grid

    The approach is to first delineate the all_touched mask, then process marginal cells at higher resolution to calculate fractions.
    """
    # apply recursively to subgeometry (useful for small islands)
    if hasattr(geom, 'geoms'):
        geoms = geom.geoms
        mask = 0.
        for geom in geoms:
            mask += polygon_to_fractional_mask(geom, coords, subgrid=subgrid)
        return mask

    lon, lat = coords
    res = lon[1]-lon[0]
    # for tiny territory we want sub-divide the grid much more
    if subgrid is None:
        ratio = res/geom.area**.5
        subgrid = int(min(max(10, ratio*10), 100))
    large = polygon_to_mask(geom, (lon, lat), all_touched=True)
    test = geom.buffer(-res*1.4142) # diagonal res*squrt(2), for more precise marginal calculation
    if test.area > 0:
        interior = polygon_to_mask(test, (lon, lat), all_touched=False)
    else:
        interior = np.zeros_like(large)
    margin = large & ~interior
    mask = np.zeros_like(large, dtype=float)
    mask[interior] = 1
    ii, jj = np.where(margin)
    for i, j in zip(ii, jj):
        lo, la = lon[j], lat[i]
        lon2 = np.linspace(lo-res/2, lo+res/2, subgrid)
        lat2 = np.linspace(la-res/2, la+res/2, subgrid)
        mask2 = polygon_to_mask(geom, (lon2, lat2), all_touched=False)
        fraction = mask2.sum()/subgrid**2
        mask[i, j] = fraction
    return mask
