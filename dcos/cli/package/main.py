"""
Usage:
    dcos package info
    dcos package --help

Options:
    -h, --help            Show this screen
"""

import docopt
from dcos.api import constants


def main():
    args = docopt.docopt(
        __doc__,
        version='dcos-package version {}'.format(constants.version))

    if args['package'] and args['info']:
        print('Manage DCOS packages and upstream registries')

    else:
        print(args)
