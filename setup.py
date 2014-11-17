from __future__ import absolute_import, print_function

import imp
import os
import sys

# Get the version without needing to install. Note that this must
# be deleted from sys.modules for nosetests to run correctly.
mod = imp.load_source(
    'dcos',
    os.path.join(os.path.dirname(__file__), "dcos", "__init__.py")
)
version = mod.__version__
del sys.modules["dcos"]

with open(os.path.join(os.path.dirname(__file__), "README.rst")) as f:
    readme = f.read()

requires = [
    "argcomplete>=0.8.0",
    "blessings>=1.5.1",
    "futures>=2.1.6",
    "importlib>=1.0.3",  # py26
    "mesos.cli>=0.1.4",
    "ordereddict>=1.1",  # py26
    "prettytable>=0.7.2",
    "pygments>=1.6",
    "requests>=2.3.0"
]

config = {
    'name': 'dcos',
    'version': version,
    'description': 'DCOS CLI',
    'long_description': readme,
    'author': 'Thomas Rampelberg',
    'author_email': 'thomas@mesosphere.io',
    'keywords': 'dcos',
    'classifiers': [],

    'packages': [
        'dcos',
        'dcos.cmds'
    ],
    'entry_points': {
        'console_scripts': [
            'dcos = dcos.cmds.main:main',

            # helpers
            'dcos-config = dcos.cmds.config:main',
            'dcos-help = dcos.cmds.help:main',

            # commands
            'dcos-install = dcos.cmds.install:main',
            'dcos-list = dcos.cmds.list:main',
            'dcos-overview = dcos.cmds.overview:main',
            'dcos-search = dcos.cmds.search:main',

            # sub-commands
            'dcos-marathon-config = dcos.cmds.marathon.config:main',
            'dcos-marathon-start = dcos.cmds.marathon.start:main',
            'dcos-marathon-scale = dcos.cmds.marathon.scale:main'
        ]
    },
    'setup_requires': [
        "nose>=1.3.3",
        "tox>=1.7.1"
    ],
    'install_requires': requires,
    'tests_require': [
        'coverage>=3.7.1',
        'flake8>=2.2.2',
        'isort>=3.9.0',
        'mock>=1.0.1',
        'pep8-naming>=0.2.2',
        'testtools>=0.9.35',  # py26
        'zake==0.0.20'
    ],
    'test_suite': 'nose.collector',
    'scripts': [
        'bin/dcos-zsh-completion.sh'
    ]
}

if __name__ == "__main__":
    from setuptools import setup

    setup(**config)
