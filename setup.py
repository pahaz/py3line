"""A setuptools based setup module.

See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject
"""

import re
from os import path
from codecs import open  # To use a consistent encoding

import sys
from setuptools import setup  # Always prefer setuptools over distutils

here = path.abspath(path.dirname(__file__))
name = 'py3line'
description = 'UNIX command-line tool for python line-based stream processing'
url = 'https://github.com/pahaz/py3line'
ppa = 'https://pypi.python.org/packages/source/s/{0}/{0}-'.format(name)

# Get the long description from the README file
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

with open(path.join(here, name + '.py'), encoding='utf-8') as f:
    data = f.read()
    version = eval(re.search("__version__[ ]*=[ ]*([^\r\n]+)", data).group(1))

if sys.version_info[0] != 3:
    raise RuntimeError("Only python 3.x is supported")

setup(
    name=name,

    # Versions should comply with PEP440.  For a discussion on single-sourcing
    # the version across setup.py and the project code, see
    # https://packaging.python.org/en/latest/single_source_version.html
    version=version,

    description=description,
    long_description=long_description,

    # The project's main homepage.
    url=url,
    download_url=ppa + version + '.zip',  # noqa

    # Author details
    author='Pahaz Blinov',
    author_email='pahaz.blinov@gmail.com',

    # Choose your license
    license='MIT',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 3 - Alpha',

        # Indicate who your project is intended for
        'Intended Audience :: Developers',
        'Topic :: Utilities',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: MIT License',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],

    platforms=['unix', 'macos', 'windows'],

    # What does your project relate to?
    keywords='google spreadsheet api util helper',

    # You can just specify the packages manually here if your project is
    # simple. Or you can use find_packages().
    # packages=find_packages(exclude=['contrib', 'docs', 'tests']),

    # Alternatively, if you want to distribute just a my_module.py, uncomment
    # this:
    py_modules=["%s" % name],

    # List run-time dependencies here.  These will be installed by pip when
    # your project is installed. For an analysis of "install_requires" vs pip's
    # requirements files see:
    # https://packaging.python.org/en/latest/requirements.html
    install_requires=[
    ],

    # List additional groups of dependencies here (e.g. development
    # dependencies). You can install these using the following syntax,
    # for example:
    # $ pip install -e .[dev,test]
    extras_require={
        'dev': ['check-manifest', 'docutils', 'Pygments'],
        # 'test': [
        #     'tox>=1.8.1',
        # ],
        # 'build_sphinx': [
        #     'sphinx',
        #     'sphinxcontrib-napoleon',
        # ],
    },

    # If there are data files included in your packages that need to be
    # installed, specify them here.  If using Python 2.6 or less, then these
    # have to be included in MANIFEST.in as well.
    # package_data={
    #     'tests': ['testrsa.key'],
    # },

    # To provide executable scripts, use entry points in preference to the
    # "scripts" keyword. Entry points provide cross-platform support and allow
    # pip to create the appropriate form of executable for the target platform.
    entry_points={
        'console_scripts': [
            'py3line=py3line:main',
        ]
    },

    # Integrate tox with setuptools
    # cmdclass={'test': Tox},
)
