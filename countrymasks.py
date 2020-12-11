import json , os
import netCDF4 as nc
import shortcountrynames

def getarea(code, mask=None, grid=None):
    geopath = os.path.join('country_data', code, 'country.geojson')
    geojs = json.load(open(geopath))
    try:
        return geojs['properties']['km2_tot']
    except KeyError:
        return areafrommask(code, mask, grid)

def areafrommask(code, mask=None, grid=None):
    if mask is None:
        mask = nc.Dataset('countrymasks_fractional.nc')
    if grid is None:
        grid = nc.Dataset('../datasets/gridarea.nc')
    m = mask['m_'+code][:]
    return (grid['cell_area'][:][m>0]*m[m>0]).sum()*1e-6  # in km2


def countrymetadata():
    fmask = nc.Dataset('countrymasks_fractional.nc')
    grid = nc.Dataset('../datasets/gridarea.nc')

    with nc.Dataset('countrymasks.nc') as ds:
        for v in ds.variables:
            if not v.startswith('m_'):
                continue
            code = v[2:]
            try:
                name = shortcountrynames.to_name(code)
            except:
                print(code, ':: code not found, read from netCDF mask')
                name = ds.variables[v].long_name
            print(code)
            path = os.path.join('country_data', code, code+'_general.json')
            if os.path.exists(path):
                js = json.load(open(path))
            else:
                js = {}

            js['name'] = name
            js['type'] = 'country'
            js['sub-countries'] = []
            #if 'stats' not in js:
            js['stats'] = []
            keys = [stat['type'] for stat in js['stats']]

            if 'area' not in keys:
                area = getarea(code, fmask, grid)
                stat = {
                        'type': 'total_area',
                        'units': 'km2',
                        'value': area,
                        }
                js['stats'].append(stat)

            print('write to', path)
            json.dump(js, open(path, 'w'))

def main():
    countrymetadata()


if __name__ == '__main__':
    main()
