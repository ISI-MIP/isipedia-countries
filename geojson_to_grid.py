import argparse
import argparse
import numpy as np
import xarray as xa
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


def init_dataset(js, res, version=None):
    version = version or js['properties']['version']
    source = js['properties']['source']

    lon = np.arange(-180+res/2, 180, res)
    lat = np.arange(90-res/2, -90, -res)  # upside down...
    ni, nj = lat.size, lon.size
    ds = xa.Dataset(coords={ "lat": lat, "lon": lon})
    ds.attrs.update(dict(
        source = source,
        note = 'Fractional mask',
        repository = REPOSITORY,
        version = version,
        ))

    ds['lon'].attrs["long_name"] = 'longitude_coordinate'
    ds['lon'].attrs["units"] = 'degree'
    ds['lat'].attrs["long_name"] = 'latitude_coordinate'
    ds['lat'].attrs["units"] = 'degree'

    return ds


def _add_world_mask_binary(ds):
    # Add world mask from existing countries
    print("Create world mask (binary)")
    shp = ds.lat.size, ds.lon.size
    world_mask = np.zeros(shp, dtype=bool)
    for m in ds:
        if not m.startswith('m_'):
            continue
        mask = (ds[m].values + 0) > 0
        world_mask |= mask

    ds['m_world'] = xa.DataArray(world_mask.astype('i1'), dims=('lat', 'lon'), coords=ds.coords)
    ds['m_world'].attrs["long_name"] = 'World'


def make_binary_mask(js, res, version=None):

    ds = init_dataset(js, res, version)

    lon, lat = ds.lon.values, ds.lat.values

    countries = js['features']

    for c in sorted(countries, key=lambda c: c['properties']['ISIPEDIA']):
        props = c['properties']
        code = props['ISIPEDIA']
        name = c['properties']['NAME']

        geom = shg.shape(c['geometry'])
        mask = polygon_to_mask(geom, (lon, lat), all_touched=True)

        if not np.any(mask):
            print('- '+name)
            [(lo, la)] = geom.centroid.coords[:]
            i = int(round(-(la-lat[0])/res))
            j = int(round((lo-lon[0])/res))
            mask[i, j] = True

        ds['m_'+code] = v = xa.DataArray(mask.astype('i1'), dims=('lat', 'lon'), coords=ds.coords)
        v.attrs["long_name"] = name
        if 'ISIPEDIA_NOTE' in props:
            v.attrs["note"] = props['ISIPEDIA_NOTE']

    _add_world_mask_binary(ds)

    return ds


def is_country(m):
    return m.startswith('m_') and m != "m_world" and m.split("_")[1] not in group_codes


def _add_world_mask_fractional(ds):

    print("Create world mask (fractional)")
    shp = ds.lat.size, ds.lon.size
    world_mask = np.zeros(shp, dtype=float)

    for m in ds:
        if not is_country(m):
            print("skip", m)
            continue
        mask = ds[m].values
        world_mask += mask

    print("World mask ranges from", np.min(world_mask[world_mask>0]), "to", np.max(world_mask))
    # Normalization
    # check grid points where mask > 1, and scale it back
    iis, jjs = np.where(world_mask > 1)

    for ii, jj in zip(iis, jjs):
        print("normalize", ii, jj, world_mask[ii, jj])
        for m in ds:
            if not is_country(m):
                continue
            value = ds[m].values[ii,jj]
            if value > 0:
                newvalue = value / world_mask[ii, jj]
                print("    -", m[2:], value, "=>", newvalue)
                ds[m].values[ii, jj] = newvalue
        world_mask[ii, jj] = 1

    assert not np.any(world_mask > 1)
#     world_mask[world_mask > 1] = 1

    # Compute groups again
    for group in grouping['groups']:
        m = "m_"+group["ISIPEDIA"]
#         assert not np.any(ds[m][:].filled(0) > 1), (m, 'has some grid cells > 1')

        group_mask = np.zeros(shp, dtype=float)
        for code in group["country_codes"]:
            try:
                group_mask += ds[f"m_{code}"].values
            except KeyError:
                print(code, "not found in countrymasks")
                continue
        assert not np.any(group_mask > 1)
        ds[m].values[:] = group_mask

    ds['m_world'] = xa.DataArray(world_mask + 0., dims=('lat', 'lon'), coords=ds.coords)
    ds['m_world'].attrs["long_name"] = 'World'



def make_fractional_mask(js, res, version=None):

    ds = init_dataset(js, res, version)

    lon, lat = ds.lon.values, ds.lat.values

    countries = js['features']

    for c in sorted(countries, key=lambda c: c['properties']['ISIPEDIA']):
        props = c['properties']
        code = props['ISIPEDIA']
        name = c['properties']['NAME']

        geom = shg.shape(c['geometry'])
        mask = polygon_to_fractional_mask(geom, (lon, lat))

        ds['m_'+code] = v = xa.DataArray(mask, dims=('lat', 'lon'), coords=ds.coords)

        v.attrs["long_name"] = name

        if 'ISIPEDIA_NOTE' in props:
            v.attrs["note"] = props['ISIPEDIA_NOTE']

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
        binary = make_binary_mask(js, res, version=o.version)
        binary.to_netcdf(f'countrymasks_{o.grid_resolution}.nc', encoding={k:{"zlib":True} for k in binary if k.startswith("m_")})

    if o.fractional_mask:
        fractional = make_fractional_mask(js, res, version=o.version)
        fractional.to_netcdf(f'countrymasks_fractional_{o.grid_resolution}.nc', encoding={k:{"zlib":True} for k in fractional if k.startswith("m_")})


if __name__ == "__main__":
    main()