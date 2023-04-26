module load python/3.9.12
module load_netcdf
module load geos/3.9.1

source venv/bin/activate

sbatch geojson_to_grid.py --grid 5arcmin --fractional-mask --version v2.6
