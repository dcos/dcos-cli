"""
Usage:
    dcos subcommand info
    dcos subcommand install python <uri>
    dcos subcommand -h | --help

Options:
    -h, --help              Show this screen
"""

import subprocess

import docopt
from dcos.api import constants, util


def main():
    error = util.configure_logger_from_environ()
    if error is not None:
        print(error.error())
        return 1

    args = docopt.docopt(
        __doc__,
        version='dcos-subcommand version {}'.format(constants.version))

    if args['subcommand'] and args['info']:
        print('Manage external DCOS commands')
    elif args['subcommand'] and args['install'] and args['python']:
        print('Trying to install a python subcommand')
        command = ['pip', 'install', args['<uri>']]
        print('Running: {!r}'.format(command))
        # For now we are just going to call pip and see if it works
        exit_status = subprocess.call(command)

        print(
            'Using pip returned the following exit status: {!r}'.format(
                exit_status))
    else:
        print(args)
