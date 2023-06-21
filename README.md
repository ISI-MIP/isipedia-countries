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

- **"inclusive" binary masks (border cells might belong to several countries)**. Any grid cell touched by a country polygon is marked as belonging to the country. Grid cells located on a border shared by several countries will be marked as belonging to all bordering countries. File list:
  
    - [countrymasks.nc](countrymasks.nc) : 0.5 degrees resolution
    - [countrymasks_5arcmin.nc](countrymasks_5arcmin.nc) : 5' resolution
    - [countrymasks_30arcsec.nc](countrymasks_30arcsec.nc) : 30" resolution

- **"exclusive" binary masks (one country per cell, but some grid cells might be left without country)**. The grid cell center must be inside the country polygon to be marked as belong to the country. A grid cell can belong to only one country (provided the polygons do not overlap, which, unfortunately, is not guaranteed). Some grid cells on the coastline might be left out (especially tiny islands at coarse resolution, e.g Tuvalu is empty at 0.5 degrees resolution). File list:

    - [countrymasks_binary_exclusive.nc](countrymasks_binary_exclusive.nc) : 0.5 degrees resolution
    - [countrymasks_binary_exclusive_5arcmin.nc](countrymasks_binary_exclusive_5arcmin.nc) : 5' resolution
    - [countrymasks_binary_exclusive_30arcsec.nc](countrymasks_binary_exclusive_30arcsec.nc) : 30" resolution

- **fractional mask**:
    - [countrymasks_fractional.nc](countrymasks_fractional.nc) : 0.5 degrees resolution
    - [countrymasks_fractional_5arcmin.nc](countrymasks_fractional_5arcmin.nc) : 5' resolution

- Country shape files are present as:
    - one world dataset `countrymasks.geojson`
    - split up for every territory e.g. `country_data/AFG/country.geojson`


## How the country masks were derived? 

### Vector data

Shape files downloaded from ASAP-GAUL: 
- https://data.europa.eu/euodp/data/dataset/jrc-10112-10004
- Associated reference article: ["ASAP: A new global early warning system to detect anomaly hot spots of agricultural production for food security analysis"](https://www.sciencedirect.com/science/article/pii/S0308521X17309095?via%3Dihub)

The shapefiles were futher processed and corrected thanks to [Natural Earth 10m data](https://www.naturalearthdata.com/downloads/10m-cultural-vectors/) v5.0.1.

List of changes from ASAP-GAUL:

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
See the code [geojson_to_grid.py](geojson_to_grid.py) for details.
