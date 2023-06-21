module load python/3.9.12
module load netcdf
module load geos/3.9.1

source venv/bin/activate

#sbatch --mem=8000 geojson_to_grid.py --grid 0.5deg --binary-mask --fractional-mask --version v2.6
#sbatch --mem=64000 geojson_to_grid.py --grid 5arcmin --binary-mask --fractional-mask --version v2.6
#sbatch --mem=64000 geojson_to_grid.py --grid 30arcsec --binary-mask --version v2.6

# sbatch --mem=8000 geojson_to_grid.py --grid 0.5deg --fractional-mask --version v2.6
# sbatch --mem=64000 geojson_to_grid.py --grid 5arcmin --fractional-mask --version v2.6

#sbatch --mem=64000 geojson_to_grid.py --grid 30arcsec --binary-exclusive-mask --version v2.7
sbatch --mem=64000 geojson_to_grid.py --grid 5arcmin --binary-exclusive-mask --version v2.7
#sbatch --mem=64000 geojson_to_grid.py --grid 0.5deg --binary-exclusive-mask --version v2.7

# and later:
# mv countrymasks_fractional_0.5deg.nc countrymasks_fractional.nc
# mv countrymasks_0.5deg.nc countrymasks.nc
