# Country masks

## Install

    pip install https://github.com/ISI-MIP/isipedia-countries/archive/master.tar.gz

## World map

![](map.svg)

## Country examples

![](country_data/AFG/country.svg)
![](country_data/FRA/country.svg)
![](country_data/SDN/country.svg)


## Which data?

- Country mask exists as:
    - binary mask: [countrymasks.nc](countrymasks.nc)
    - fractional mask: [countrymasks_fractional.nc](countrymasks_fractional.nc)

- Country shape files are present as:
    - one world dataset `countrymasks.geojson`
    - split up for every territory e.g. `country_data/AFG/country.geojson`


## How the country masks were derived? 

### Vector data

Shape files downloaded from ASAP-GAUL: 
- https://data.europa.eu/euodp/data/dataset/jrc-10112-10004
- Associated reference article: ["ASAP: A new global early warning system to detect anomaly hot spots of agricultural production for food security analysis"](https://www.sciencedirect.com/science/article/pii/S0308521X17309095?via%3Dihub)


The data was further processed as far as countries without ISOcode are concerned:

- West Bank and Gaza Strip merged into Palestine, State Of (PSE), according to UN, ISO, WB

- Added missing isocodes based on ISO website:
    - Reunion (REU)
    - Saint Pierre et Miquelon (SPM)
    - Saint Vincent and the Grenadines (VCT)

- Attach small disputed territories to larger neighbour, consistently with Natural Earth polygons
    - Abyei >>> Sudan
    - Aksai Chin >>> China
    - Arunachal Pradesh >>> India
    - China/India >>> India
    - Hala'ib triangle >>> Egypt
    - Ilemi triangle >>> Kenya
    - Ma'tan al-Sarra >>> Sudan

- Jammu and Kashmir split and attached to India and Pakistan, according to Natural Earth 10m v5.0.1 polygons

- Remove obsolete territories:
    - Netherlands Antilles (ANT) -- now partly independent since 2010

- Deleted smaller territories:
    - Kingman Reef
    - Kuril islands

- add small island groups from Natural Earth  10m v5.0.1 polygons (many more are provided)


- West Bank and Gaza Strip merged into Palestine, State Of (PSE), according to UN, ISO, WB
    

### Binary and fractional masks

Both binary and fractional masks were derived from the vector data thanks to `rasterio.mask.geometry_mask`
See (geomtools)[geomtools.py]'s polygon_to_mask and polygon_to_fraction_mask for details.



