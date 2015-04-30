from codecs import open
from os import path

import dcoscli
from setuptools import find_packages, setup

here = path.abspath(path.dirname(__file__))

# Get the long description from the relevant file
with open(path.join(here, 'DESCRIPTION.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='dcoscli',

    # Versions should comply with PEP440.  For a discussion on single-sourcing
    # the version across setup.py and the project code, see
    # https://packaging.python.org/en/latest/single_source_version.html
    version=dcoscli.version,

    description='DCOS Command Line Interface',
    long_description=long_description,

    # The project's main homepage.
    url='https://github.com/mesosphere/dcos-cli',

    # Author details
    author='Mesosphere, Inc.',
    author_email='team@mesosphere.io',


    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 4 - Beta',

        # Indicate who your project is intended for
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Topic :: Software Development :: User Interfaces',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: Apache Software License',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
    ],

    # What does your project relate to?
    keywords='mesos apache marathon mesosphere command datacenter',

    # You can just specify the packages manually here if your project is
    # simple. Or you can use find_packages().
    packages=find_packages(exclude=['tests', 'bin']),

    # List run-time dependencies here.  These will be installed by pip when
    # your project is installed. For an analysis of "install_requires" vs pip's
    # requirements files see:
    # https://packaging.python.org/en/latest/requirements.html
    install_requires=[
        'dcos=={}'.format(dcoscli.version),
        'docopt>=0.6, <1.0',
        'pkginfo>=1.2, <2.0',
        'toml>=0.9, <1.0',
        'virtualenv>=12.1, <13.0',
        'rollbar>=0.9, <1.0',
        'futures>=3.0, <4.0',
        'oauth2client>=1.4, <2.0'
    ],

    # If there are data files included in your packages that need to be
    # installed, specify them here.  If using Python 2.6 or less, then these
    # have to be included in MANIFEST.in as well.
    package_data={
        'dcoscli': [
            'data/*.json',
            'data/config-schema/*.json',
        ],
    },

    # To provide executable scripts, use entry points in preference to the
    # "scripts" keyword. Entry points provide cross-platform support and allow
    # pip to create the appropriate form of executable for the target platform.
    entry_points={
        'console_scripts': [
            'dcos=dcoscli.main:main',
            'dcos-help=dcoscli.help.main:main',
            'dcos-config=dcoscli.config.main:main',
            'dcos-marathon=dcoscli.marathon.main:main',
            'dcos-package=dcoscli.package.main:main',
        ],
    },

    scripts=[
        'bin/env-setup',
    ]
)
