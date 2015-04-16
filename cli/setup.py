from setuptools import setup, find_packages
from os import path

import dcoscli

here = path.abspath(path.dirname(__file__))

setup(
    name='dcoscli',

    # Versions should comply with PEP440.  For a discussion on single-sourcing
    # the version across setup.py and the project code, see
    # https://packaging.python.org/en/latest/single_source_version.html
    version=dcoscli.version,

    description='DCOS Command Line Interface',

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
        'Development Status :: 3 - Alpha',

        # Indicate who your project is intended for
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Topic :: Software Development :: User Interfaces',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: TODO License',

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

    # List run-time dependencies here.  These will be installed by pip when your
    # project is installed. For an analysis of "install_requires" vs pip's
    # requirements files see:
    # https://packaging.python.org/en/latest/requirements.html
    install_requires=[
        'dcos',
        'docopt',
        'pkginfo',
        'toml',
        'virtualenv',
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
            'dcos-subcommand=dcoscli.subcommand.main:main',
        ],
    },

    scripts=[
        'bin/env-setup',
    ]
)
