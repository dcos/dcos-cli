"""
Usage:
    dcos package info
    dcos package --help

Options:
    -h, --help            Show this screen
"""

import docopt

from ..api import constants


def main():
    args = docopt.docopt(
        __doc__,
        version='dcos-package version {}'.format(constants.version))

    if args['package'] and args['info']:
        print('Work with DCOS packages.')

    else:
        print(args)
