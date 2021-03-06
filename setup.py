import logging
import os
import shutil
import subprocess
import sys
from setuptools import setup
from setuptools.extension import Extension

# Use Cython if available.
try:
    from Cython.Build import cythonize
except ImportError:
    cythonize = None

logging.basicConfig()
log = logging.getLogger()

# python -W all setup.py ...
if 'all' in sys.warnoptions:
    log.level = logging.DEBUG

# Parse the version from the fiona module.
with open('fiona/__init__.py', 'r') as f:
    for line in f:
        if line.find("__version__") >= 0:
            version = line.split("=")[1].strip()
            version = version.strip('"')
            version = version.strip("'")
            continue

# Fiona's auxiliary files are UTF-8 encoded and we'll specify this when
# reading with Python 3+
open_kwds = {}
if sys.version_info > (3,):
    open_kwds['encoding'] = 'utf-8'

with open('VERSION.txt', 'w', **open_kwds) as f:
    f.write(version)

with open('README.rst', **open_kwds) as f:
    readme = f.read()

with open('CREDITS.txt', **open_kwds) as f:
    credits = f.read()

with open('CHANGES.txt', **open_kwds) as f:
    changes = f.read()

# By default we'll try to get options via gdal-config. On systems without,
# options will need to be set in setup.cfg or on the setup command line.
include_dirs = []
library_dirs = []
libraries = []
extra_link_args = []

try:
    gdal_config = os.environ.get('GDAL_CONFIG', 'gdal-config')
    with open("gdal-config.txt", "w") as gcfg:
        subprocess.call([gdal_config, "--cflags"], stdout=gcfg)
        subprocess.call([gdal_config, "--libs"], stdout=gcfg)
        subprocess.call([gdal_config, "--datadir"], stdout=gcfg)
    with open("gdal-config.txt", "r") as gcfg:
        cflags = gcfg.readline().strip()
        libs = gcfg.readline().strip()
        datadir = gcfg.readline().strip()
    for item in cflags.split():
        if item.startswith("-I"):
            include_dirs.extend(item[2:].split(":"))
    for item in libs.split():
        if item.startswith("-L"):
            library_dirs.extend(item[2:].split(":"))
        elif item.startswith("-l"):
            libraries.append(item[2:])
        else:
            # e.g. -framework GDAL
            extra_link_args.append(item)

    # Conditionally copy the GDAL data. To be used in conjunction with
    # the bdist_wheel command to make self-contained binary wheels.
    if os.environ.get('PACKAGE_DATA'):
        try:
            shutil.rmtree('fiona/gdal_data')
        except OSError:
            pass
        shutil.copytree(datadir, 'fiona/gdal_data')

except Exception as e:
    log.warning("Failed to get options via gdal-config: %s", str(e))

# Conditionally copy PROJ.4 data.
if os.environ.get('PACKAGE_DATA'):
    projdatadir = os.environ.get('PROJ_LIB', '/usr/local/share/proj')
    if os.path.exists(projdatadir):
        try:
            shutil.rmtree('fiona/proj_data')
        except OSError:
            pass
        shutil.copytree(projdatadir, 'fiona/proj_data')

ext_options = dict(
    include_dirs=include_dirs,
    library_dirs=library_dirs,
    libraries=libraries,
    extra_link_args=extra_link_args)

# When building from a repo, Cython is required.
if os.path.exists("MANIFEST.in"):
    log.info("MANIFEST.in found, presume a repo, cythonizing...")
    if not cythonize:
        log.critical(
            "Cython.Build.cythonize not found. "
            "Cython is required to build from a repo.")
        sys.exit(1)
    ext_modules = cythonize([
        Extension('fiona._geometry', ['fiona/_geometry.pyx'], **ext_options),
        Extension('fiona._transform', ['fiona/_transform.pyx'], **ext_options),
        Extension('fiona._drivers', ['fiona/_drivers.pyx'], **ext_options),
        Extension('fiona._err', ['fiona/_err.pyx'], **ext_options),
        Extension('fiona.ogrext', ['fiona/ogrext.pyx'], **ext_options)])
# If there's no manifest template, as in an sdist, we just specify .c files.
else:
    ext_modules = [
        Extension('fiona._transform', ['fiona/_transform.cpp'], **ext_options),
        Extension('fiona._geometry', ['fiona/_geometry.c'], **ext_options),
        Extension('fiona._drivers', ['fiona/_drivers.c'], **ext_options),
        Extension('fiona._err', ['fiona/_err.c'], **ext_options),
        Extension('fiona.ogrext', ['fiona/ogrext.c'], **ext_options)]

requirements = ['cligj', 'six']
if sys.version_info < (2, 7):
    requirements.append('argparse')
    requirements.append('ordereddict')

setup_args = dict(
    metadata_version='1.2',
    name='Fiona',
    version=version,
    requires_python = '>=2.6',
    requires_external = 'GDAL (>=1.8)',
    description="Fiona reads and writes spatial data files",
    license='BSD',
    keywords='gis vector feature data',
    author='Sean Gillies',
    author_email='sean.gillies@gmail.com',
    maintainer='Sean Gillies',
    maintainer_email='sean.gillies@gmail.com',
    url='http://github.com/Toblerity/Fiona',
    long_description=readme + "\n" + changes + "\n" + credits,
    package_dir={'': '.'},
    packages=['fiona', 'fiona.fio'],
    entry_points='''
        [console_scripts]
        fio=fiona.fio.main:cli

        [fiona.fio_commands]
        bounds=fiona.fio.fio:bounds
        cat=fiona.fio.fio:cat
        collect=fiona.fio.fio:collect
        distrib=fiona.fio.fio:distrib
        dump=fiona.fio.fio:dump
        env=fiona.fio.fio:env
        info=fiona.fio.fio:info
        insp=fiona.fio.fio:insp
        load=fiona.fio.fio:load
        ''',
    install_requires=requirements,
    tests_require=['nose'],
    test_suite='nose.collector',
    ext_modules=ext_modules,
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Topic :: Scientific/Engineering :: GIS',
    ])

if os.environ.get('PACKAGE_DATA'):
    setup_args['package_data'] = {'fiona': ['gdal_data/*', 'proj_data/*']}

setup(**setup_args)
