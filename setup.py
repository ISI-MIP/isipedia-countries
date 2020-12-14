import glob, os
from distutils.core import setup
import versioneer

setup(name='isipedia-countries',
      version=versioneer.get_version(),
      cmdclass = versioneer.get_cmdclass(),
      author='Mahe Perrette for ISIpedia',
      author_email='mahe.perrette@pik-potsdam.de',
      description='Country data for isipedia',
      url='https://github.com/ISI-MIP/isipedia-countries',
      py_modules = ['country_data'],
      data_files = [
          ('country_data', ['countrymasks.nc', 'countrymasks_fractional.nc', 'Estimated_population_2005.nc', 'gridarea.nc'])
      ] + [ (countrydir, glob.glob(f'{countrydir}/*') ) 
           for countrydir in glob.glob('country_data/*') if os.path.isdir(countrydir) ],
      install_requires = open('requirements.txt').read(),
      license = "MIT",
      )

