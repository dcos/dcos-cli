"""
Setup script for DC/OS CLI.
"""

from setuptools import setup

from dcos_cli import __version__

with open('requirements.txt') as requirements:
    INSTALL_REQUIRES = []
    for line in requirements.readlines():
        if not line.startswith('#'):
            INSTALL_REQUIRES.append(line)

with open('requirements-dev.txt') as dev_requirements:
    DEV_REQUIRES = []
    for line in dev_requirements.readlines():
        if not line.startswith('#'):
            DEV_REQUIRES.append(line)

with open('README.md') as f:
    LONG_DESCRIPTION = f.read()

setup(
    name='DC/OS CLI',
    version=__version__,
    author='Bilal Amarni',
    author_email='bamarni@mesosphere.com',
    description='A command-line interface for DC/OS.',
    long_description=LONG_DESCRIPTION,
    packages=['dcos_cli'],
    zip_safe=False,
    install_requires=INSTALL_REQUIRES,
    extras_require={
        'dev': DEV_REQUIRES,
    },
    entry_points={
        'console_scripts': [
            'dcos = dcos_cli.cli.dcos:dcos',
        ],
    },
    classifiers=[
        'Operating System :: POSIX',
        'Operating System :: MacOS',
        'Operating System :: Microsoft :: Windows',
        'Environment :: Console',
        'Programming Language :: Python :: 3.6',
    ],
)
