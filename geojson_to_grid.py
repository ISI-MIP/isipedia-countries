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


def make_binary_mask(file_name, js, res, version=None):

    ds = init_dataset(file_name, js, res, version)
    ds.note = 'Any grid cell that is "touched" by a polygon is marked as belonging to that country'
    lon, lat = ds['lon'][:], ds['lat'][:]

    countries = js['features']

    for c in tqdm.tqdm(list(sorted(countries, key=lambda c: c['properties']['ISIPEDIA']))):
        props = c['properties']
        code = props['ISIPEDIA']
        name = c['properties']['NAME']

        geom = shg.shape(c['geometry'])
        mask = polygon_to_mask(geom, (lon, lat), all_touched=True)
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
    parser.add_argument('--binary-mask', action="store_true")
    o = parser.parse_args()

    js = json.load(open('countrymasks.geojson'))

    res = {
        "0.5deg": 0.5,
        "5arcmin": 5/60,
        "30arcsec": 30/3600,
    }.get(o.grid_resolution)

    if o.binary_mask:
        with make_binary_mask(f'countrymasks_{o.grid_resolution}.nc', js, res, version=o.version) as binary:
            pass

    if o.fractional_mask:
        with make_fractional_mask(f'countrymasks_fractional_{o.grid_resolution}.nc', js, res, version=o.version) as fractional:
            pass

if __name__ == "__main__":
    main()