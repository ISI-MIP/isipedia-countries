#!venv/bin/python
import sys
sys.path.insert(0, '.')
import tqdm
import argparse
import numpy as np
# import xarray as xa
import netCDF4 as nc
import json
import shapely.geometry as shg
from geomtools import polygon_to_mask, polygon_to_fractional_mask

REPOSITORY = 'https://github.com/ISI-MIP/isipedia-countries'


caribbean_sids = ['ATG', 'BHS', 'BLZ', 'BMU', 'BRB', 'CUW', 'CYM', 'DMA', 'GRD', 'KNA', 'LCA', 'SXM', 'TCA', 'VCT', 'VGB', 'VIR']
indianocean_sids = ['BHR', 'COM', 'MDV', 'MUS', 'SGP', 'STP', 'SYC']
pacific_sids = ['ASM', 'FSM', 'GUM', 'KIR', 'MHL', 'MNP', 'NRU', 'PLW', 'TON', 'TUV']

grouping = {
    'groups': [
        {
            'NAME': 'Caribbean island small states',
            'ISIPEDIA': 'CSID',
            'country_codes': caribbean_sids,
        },
        {
            'NAME': 'Indian Ocean island small state',
            'ISIPEDIA': 'IOSID',
            'country_codes': indianocean_sids,
        },
        {
            'NAME': 'Pacific island small states',
            'ISIPEDIA': 'PSID',
            'country_codes': pacific_sids,
        },
    ]}

group_codes = [g['ISIPEDIA'] for g in grouping['groups']]


def init_dataset(file_name, js, res, version=None):
    version = version or js['properties']['version']
    source = js['properties']['source']

    lon = np.arange(-180+res/2, 180, res)
    lat = np.arange(90-res/2, -90, -res)  # upside down...
    ni, nj = lat.size, lon.size

    ds = nc.Dataset(file_name,'w', zlib=True)

    ds.source = source
    ds.repository = REPOSITORY
    ds.version = version

    ds.createDimension('lon', lon.size)
    ds.createDimension('lat', lat.size)
    v = ds.createVariable('lon', float, 'lon')
    v[:] = lon
    v.long_name = 'longitude_coordinate'
    v.units = 'degree'
    v = ds.createVariable('lat', float, 'lat')
    v[:] = lat
    v.lat_name = 'latitude_coordinate'
    v.units = 'degree'

    return ds


def make_exclusive(ds):
    # Add world mask from existing countries
    print("Force exclusivity of pixels")
    shp = ds['lat'].size, ds["lon"].size
    sum_mask = np.zeros(shp, dtype=int)
    collect = {}
    for m in ds.variables:
        if not is_country(m):
            continue
        mask = ds[m][:].filled(0) > 0
        already_occupied = sum_mask[mask] > 0
        n = already_occupied.sum()
        if n > 0:
            print(f"{m[2:]}: {n} grid cells already taken by another country, mask out ! (out of {mask.sum()} ~ {n/mask.sum()*100:.2f} %)")

            i, j = np.where(mask & (sum_mask > 0))
            for ii, jj in zip(i, j):
                ds[m][ii,jj] = 0
            mask = ds[m][:].filled(0) > 0

        sum_mask[mask] += 1

    assert sum_mask.max() == 1, repr(sum_mask.max())


def exclusive_country_masks_as_one_labelled_array(ds):

    shp = ds['lat'].size, ds["lon"].size
    label_mask = np.zeros(shp, dtype=int)
    label_names = {}
    collect = {}
    for i, m in enumerate(tqdm.tqdm(ds.variables)):
        if not is_country(m):
            continue
        mask = ds[m][:].filled(0) > 0
        label_mask[mask] = i
        label_names[i] = m[2:]

    return label_mask, label_names


def _add_exclusive_label_mask(ds):
    try:
        label = ds.createVariable('labels', int, ("lat", "lon"), zlib=True)
    except RuntimeError:
        label = ds['labels']

    label_mask, label_names = exclusive_country_masks_as_one_labelled_array(ds)
    ds["labels"][:] = label_mask
    ds["labels"].label_mapping = label_names


def _add_world_mask_binary(ds):
    # Add world mask from existing countries
    print("Create world mask (binary)")
    shp = ds['lat'].size, ds["lon"].size
    world_mask = np.zeros(shp, dtype=bool)
    for m in ds.variables:
        if not m.startswith('m_'):
            continue
        mask = ds[m][:].filled(0) > 0
        world_mask |= mask
    try:
        world = ds.createVariable('m_world', "i1", ("lat", "lon"), zlib=True)
    except RuntimeError:
        world = ds['m_world']
    world[:] = world_mask
    ds['m_world'].long_name = 'World'


def make_binary_mask(file_name, js, res, version=None, all_touched=True):

    ds = init_dataset(file_name, js, res, version)
    if all_touched:
        ds.note = 'Any grid cell that is "touched" by a polygon is marked as belonging to that country. Note bordering grid cells will be marked as belonging to several countries.'
    else:
        ds.note = 'Any grid cell whose center is contained in a polygon is marked as belonging to that country. Each grid cell belongs to a single country, but some coastal grid cells may be left out (e.g. tiny island).'
    lon, lat = ds['lon'][:], ds['lat'][:]

    countries = js['features']

    for c in tqdm.tqdm(list(sorted(countries, key=lambda c: c['properties']['ISIPEDIA']))):
        props = c['properties']
        code = props['ISIPEDIA']
        name = c['properties']['NAME']

        geom = shg.shape(c['geometry'])
        mask = polygon_to_mask(geom, (lon, lat), all_touched=all_touched)
    #     mask = polygon_to_mask(geom, (lon, lat), all_touched=False)

        if not np.any(mask):
            print('- '+name)
            [(lo, la)] = geom.centroid.coords[:]
            i = int(round(-(la-lat[0])/res))
            j = int(round((lo-lon[0])/res))
            mask[i, j] = True

        v = ds.createVariable('m_'+code, 'i1', ('lat', 'lon'), zlib=True)
        v[:] = mask
        v.long_name = name
        if 'ISIPEDIA_NOTE' in props:
            v.note = props['ISIPEDIA_NOTE']

    _add_world_mask_binary(ds)

    return ds


def is_country(m):
    return m.startswith('m_') and m != "m_world" and m.split("_")[1] not in group_codes


def _add_world_mask_fractional(ds):

    print("Create world mask (fractional)")
    variable = ds.variables['m_AFG']

    # World mask
    world_mask = np.zeros(variable.shape, dtype=variable.dtype)
    for m in ds.variables:
        if not is_country(m):
            print("skip", m)
            continue
        mask = ds[m][:].filled(0)
        world_mask += mask

    print("World mask ranges from", np.min(world_mask[world_mask>0]), "to", np.max(world_mask))
    # Normalization
    # check grid points where mask > 1, and scale it back
    iis, jjs = np.where(world_mask > 1)

    for ii, jj in zip(iis, jjs):
        print("normalize", ii, jj, world_mask[ii, jj])
        for m in ds.variables:
            if not is_country(m):
                continue
            value = ds[m][ii,jj].filled(0)
            if value > 0:
                newvalue = value / world_mask[ii, jj]
                print("    -", m[2:], value, "=>", newvalue)
                ds[m][ii, jj] = newvalue
        world_mask[ii, jj] = 1

    assert not np.any(world_mask > 1)
#     world_mask[world_mask > 1] = 1

    # Compute groups again
    for group in grouping['groups']:
        m = "m_"+group["ISIPEDIA"]
#         assert not np.any(ds[m][:].filled(0) > 1), (m, 'has some grid cells > 1')

        group_mask = np.zeros(variable.shape, dtype=variable.dtype)
        for code in group["country_codes"]:
            try:
                group_mask += ds.variables[f"m_{code}"][:].filled(0)
            except KeyError:
                print(code, "not found in countrymasks")
                continue
        assert not np.any(group_mask > 1)
        ds[m][:] = group_mask

    try:
        world = ds.createVariable('m_world', variable.datatype, variable.dimensions, zlib=True)
    except RuntimeError:
        world = ds['m_world']
    world[:] = world_mask + 0.
    # copy variable attributes all at once via dictionary
    ds['m_world'].setncatts(vars(variable))
    ds['m_world'].long_name = 'World'


def make_fractional_mask(file_name, js, res, version=None):

    ds = init_dataset(file_name, js, res, version)
    ds.note = 'Fractional mask'

    lon, lat = ds['lon'][:], ds['lat'][:]

    countries = js['features']

    for c in tqdm.tqdm(list(sorted(countries, key=lambda c: c['properties']['ISIPEDIA']))):
        props = c['properties']
        code = props['ISIPEDIA']
        name = c['properties']['NAME']

        print(code, name)
        geom = shg.shape(c['geometry'])
        mask = polygon_to_fractional_mask(geom, (lon, lat))

        v = ds.createVariable('m_'+code, 'f', ('lat', 'lon'), zlib=True)
        v[:] = mask
        v.long_name = name
        if 'ISIPEDIA_NOTE' in props:
            v.note = props['ISIPEDIA_NOTE']

    _add_world_mask_fractional(ds)

    return ds



def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('--geojson', default="countrymasks.geojson")
    parser.add_argument('--grid-resolution', choices=["0.5deg", "5arcmin", "30arcsec"], default="0.5deg")
    parser.add_argument('--version')
    parser.add_argument('--fractional-mask', action="store_true")
    parser.add_argument('--binary-mask', action="store_true", help="all_touched=True : grid cell marked when touched by polygon")
    parser.add_argument('--binary-exclusive-mask', action="store_true", help="all_touched=False : grid cell marked when center inside polygon")
    parser.add_argument('--force-exclusivity', action="store_true", help="ensure the pixels belong to only one country")
    parser.add_argument('--label-mask', action="store_true", help="write a label mask (assuming exclusivity)")
    o = parser.parse_args()

    js = json.load(open('countrymasks.geojson'))

    res = {
        "0.5deg": 0.5,
        "5arcmin": 5/60,
        "30arcsec": 30/3600,
    }.get(o.grid_resolution)

    if o.binary_mask:
        with make_binary_mask(f'countrymasks_{o.grid_resolution}.nc', js, res, version=o.version, all_touched=True) as binary:
            if o.force_exclusivity:
                make_exclusive(binary)
            if o.label_mask:
                _add_exclusive_label_mask(binary)

    if o.binary_exclusive_mask:
        with make_binary_mask(f'countrymasks_binary_exclusive_{o.grid_resolution}.nc', js, res, version=o.version, all_touched=False) as binary:
            if o.force_exclusivity:
                make_exclusive(binary)
            if o.label_mask:
                _add_exclusive_label_mask(binary)

    if o.fractional_mask:
        with make_fractional_mask(f'countrymasks_fractional_{o.grid_resolution}.nc', js, res, version=o.version) as fractional:
            pass

if __name__ == "__main__":
    main()
