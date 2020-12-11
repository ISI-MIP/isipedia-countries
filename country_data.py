"""Get details from World Bank etc
"""
import json, glob, os
import logging
import pandas as pd
import world_bank_data as wb
import netCDF4 as nc

countrymasks = os.path.dirname(__file__)
country_data_path = os.path.join(countrymasks, 'country_data')
datasets = os.path.join(countrymasks, 'datasets')


class Variable:
    def __init__(self, type, label, unit, wdi_code=None, un_code=None, alias=None, wdi_scale=1):
        self.type = type
        self.label = label
        self.alias = alias or type.lower()
        self.unit = unit
        self.wdi_code = wdi_code
        self.wdi_scale = wdi_scale
        self.un_code = un_code
        self._wdi = None
        self._un = None

    def load_wdi(self):
        if not self.wdi_code:
            raise ValueError('{}: no associated WDI variable'.format(self.label))
        fname = os.path.join(datasets, 'wdi', self.wdi_code+'.csv')
        try:
            timeseries = pd.read_csv(fname, index_col=('Country','Year'))[self.wdi_code]
        except:
            # NOTE: mrv=1 for most recent value would be equivalent to subsequent treatment
            # ....: except that sometimes it results to NaN (e.g CO2 emissions for PSE, Palestine)
            timeseries = wb.get_series(self.wdi_code, id_or_value='id', simplify_index=True)
            timeseries.to_csv(fname)
        return timeseries

    # lazy loading
    @property
    def wdi(self):
        if self._wdi is None:
            self._wdi = self.load_wdi()
        return self._wdi

    @property
    def un(self):
        if not self.un_code:
            raise ValueError('{}: no associated UN variable'.format(self.label))
        if self._un is None:
            self._un = json.load(os.path.join(datasets, 'countryprofiledata.json'))
        return self._un
    

    def get_wdi(self, country_code):
        try:
            value = self.wdi.loc[country_code].dropna().values[-1]*self.wdi_scale
        except:
            value = float('nan')
            logging.warning('no valid WDI value for {},{}'.format(country_code, self.wdi_code))
        return value


    def get_un(self, country_code):
        try:
            return self.un[country_code][self.un_code]
        except:
            logging.warning('no valid UN value for {},{}'.format(country_code, self.un_code))
            return float('nan')


    def get(self, country_code):
        if self.wdi_code:
            return self.get_wdi(country_code)

        elif self.un_code:
            return self.get_un(country_code)

        raise ValueError('no method provided')


    def to_dict(self, value, rank=None):
        return {
            'type': self.type,
            'label': self.label,
            'unit': self.unit,
            'value': value,
            'rank': rank,
            'un_code': self.un_code,
            'wdi_code': self.wdi_code,
        }

# https://data.worldbank.org/indicator/AG.SRF.TOTL.K2
# AG.LND.TOTL.K2 : land area !
stats_variables = [
    Variable('POP_TOTL', label='Total population', unit='million people', alias='pop_total', wdi_code='SP.POP.TOTL', wdi_scale=1e-6),
    Variable('POP_DNST', label='Population density', unit='people/sq. km', alias='pop_density', wdi_code='EN.POP.DNST'),
    Variable('RUR_POP_PRCT', label='Rural population', unit='% of total population', alias='pop_rural', wdi_code='SP.RUR.TOTL.ZS'),
    Variable('URB_POP_PRCT', label='Urban population', unit='% of total population', alias='pop_urban', wdi_code='SP.URB.TOTL.IN.ZS'),
    Variable('POP_GROWTH', label='Population growth', unit='% per year', alias='pop_growth', wdi_code='SP.POP.GROW'),
    Variable('SURFACE_AREA', label='Surface area', unit='sq. km', alias='area', wdi_code='AG.SRF.TOTL.K2'),

    Variable('GDP_PPP', label='Growth Domestic Product, PPP', unit='billion $ (PPP, current)', alias='gdp_ppp', wdi_code='NY.GDP.MKTP.PP.CD', wdi_scale=1e-9),
    Variable('GDP_PER_CAPITA_PPP', label='GDP per capita, PPP', unit='$ (PPP, current)', alias='gdp_capita_ppp', wdi_code='NY.GDP.PCAP.PP.CD'),
    Variable('GDP', label='Growth Domestic Product', unit='billion $ (current)', alias='gdp', wdi_code='NY.GDP.MKTP.CD', wdi_scale=1e-9),
    Variable('GDP_PER_CAPITA', label='GDP per capita', unit='$ (current)', alias='gdp_capita', wdi_code='NY.GDP.PCAP.CD'),

    Variable('GDP_GROWTH', label='GDP growth', unit='annual %', alias='gdp_growth', wdi_code='NY.GDP.MKTP.KD.ZG'),

    Variable('POV_DDAY', label='Poverty headcount rank at $ 1.90 a day (2011 PPP)', unit='% of total population', alias='poverty', wdi_code='SI.POV.DDAY'),
    # Variable('CO2_EM_CAPITA', label='CO2 emissions per capita', unit='metric tons/capita', alias='co2_capita', wdi_code='EM.ATM.CO2E.PC'),
    Variable('CO2_EM', label='CO2 emissions', unit='kt', alias='co2', wdi_code='EN.ATM.CO2E.KT'),
    Variable('CO2_EM_INTENSITY', label='CO2 intensity', unit='kg per kg of oil equivalent energy use', wdi_code='EN.ATM.CO2E.EG.ZS'),
    Variable('CO2_EM_GDP', label='CO2 emissions per GDP', unit='kg per 2011 PPP $ of GDP', wdi_code='EN.ATM.CO2E.PP.GD.KD'),

    Variable('HDI', label='Human Development Index', unit='(-)', un_code='HDI_Human_development_index_HDIg_value'),
]


class CountryStats:
    """This is the class for the corresponding json file in country_data 
    """
    def __init__(self, name, type="country", sub_countries=[], code=None, stats=None):
        self.name = name
        self.type = type
        self.code = code
        self.sub_countries = sub_countries
        self.stats = stats or []

    def get(self, name, insert=False):
        try:
            i = [e['type'] for e in self.stats].index(name)
            return self.stats[i]
        except ValueError:
            if insert:
                e = {'type': name}
                self.stats.append(e)
                return e
            else:
                raise

    def getvalue(self, name, missing=float('nan')):
        try:
            return self.get(name)['value']
        except ValueError:
            return missing

    @classmethod
    def load(cls, fname):
        js = json.load(open(fname))
        code = os.path.basename(os.path.dirname(fname))
        return cls(js['name'], js.get('type', 'country'), js.get('sub-countries',[]), code=js.get('code', code), stats=js.get('stats', []))

    def save(self, fname):
        cdir = os.path.dirname(fname)
        if not os.path.exists(cdir):
            logging.info('create '+repr(cdir))
            os.makedirs(cdir)

        js = {
            'name': self.name,
            'code': self.code,
            'type': self.type,
            'sub-countries': self.sub_countries,
            'stats': self.stats,
        }
        json.dump(js, open(fname, 'w'))


    def __repr__(self):
        return 'CountryStats({name}, {code})'.format(**vars(self))


class CountryStatDB:
    def __init__(self, countries=None):
        self.countries = countries or {}

    @staticmethod
    def cpath(code):
        return os.path.join(country_data_path, code, '{}_general.json'.format(code))

    @classmethod
    def load(cls):
        db = cls()
        for root, codes, _ in glob.glob(country_data_path):
            break

        for c in codes:
            cpath = os.path.join(country_data_path, c, '{}_general.json'.format(c))
            try:
                cstat = CountryStats.load(cpath)
            except Exception as error:
                logging.warning(str(error))
                continue
                db.countries[c] = stat
        return db

    def save(self):
        for c, cstat in self.countries.items():
            cpath = self.cpath(c)
            cstat.save(cpath)


def main():
    import argparse

    parser = argparse.ArgumentParser()
    x = parser.add_mutually_exclusive_group()
    x.add_argument('--countries', nargs='+')
    x.add_argument('--folder', action='store_true', help='read country codes from country_data folder')
    # x.add_argument('--netcdf', '--nc', action='store_true', help='read country codes from default countrymasks.nc')
    x.add_argument('--mask-file', help='read country code from netcdf mask file')
    # x.add_argument('--shape-file', help='read country code from geojson shape file')
    o = parser.parse_args()

    wbcountries = wb.get_countries()

    if o.countries:
        codes = o.countries

    elif o.mask_file:
        with nc.Dataset(os.path.join(o.mask_file)) as ds:
          codes = [v[2:] for v in ds.variables if v.startswith('m_')]

    elif o.folder:
        for root, codes, _ in os.walk(country_data_path):
           break

    else:
        v = stats_variables[0]
        codes = sorted(set(c for c, y in v.wdi.index))

    countries = {}
    for code in codes:
        wbcode = 'WLD' if code == 'world' else code
        if wbcode in wbcountries.index:
            name = wbcountries.loc[wbcode]['name']
        else:
            logging.warning('{} not present in World Bank Database'.format(code))
            logging.info('try countrymasks.nc')
            try:
                with nc.Dataset(os.path.join(countrymasks, 'countrymasks.nc')) as ds:
                    name = ds['m_'+code].long_name
            except:
                logging.warning('{} not present in countrymasks.nc'.format(code))
                logging.warning('skip {}'.format(code))
                continue

        stats = [v.to_dict(v.get(wbcode)) for v in stats_variables]
        countries[code] = CountryStats(name, code=code, type='country', sub_countries=[], stats=stats)

    db = CountryStatDB(countries)
    db.save()


if __name__ == '__main__':
    main()
