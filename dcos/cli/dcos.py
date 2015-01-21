"""
Usage:
    dcos [--mesos=<uri>] <command> [<args>...]
    dcos --help
    dcos --version

Options:
    -h, --help           Show this screen
    --version            Show version
    --mesos=<uri>        URI for the Mesos master
"""


import os
import subprocess

import docopt

from .. import constants, options


def main():
    if not _is_valid_configuration():
        return 1

    subcommands = _list_external_subcommands(os.environ['DCOS_PATH'])
    subcommand_summaries = _external_command_documentation(subcommands)

    args = docopt.docopt(
        options.extend_usage_docopt(__doc__, subcommand_summaries),
        version='dcos version {}'.format(constants.version),
        options_first=True)

    argv = [args['<command>']] + args['<args>']

    if args['<command>'] in subcommands:
        command = 'dcos-{}'.format(args['<command>'])
        return subprocess.call([command] + argv)
    else:
        print(
            '{!r} is not a dcos command. See "dcos --help".'.format(
                args['<command>']))
        return 1


def _list_external_subcommands(dcos_path):
    prefix = 'dcos-'

    return [filename[len(prefix):]

            for dirpath, _, filenames
            in os.walk(os.path.join(dcos_path, "bin"))

            for filename in filenames

            if filename.startswith(prefix)
            and os.access(os.path.join(dirpath, filename), os.X_OK)
            ]


def _external_command_documentation(commands):
    def info(commnand):
        return subprocess.check_output(
            ['dcos-{}'.format(command), command, 'info'])

    return [(command, info(command)) for command in commands]


def _is_valid_configuration():
    dcos_path = os.environ.get(constants.DCOS_PATH_ENV)
    if dcos_path is None:
        msg = 'Environment variable {!r} not set to the DCOS CLI path.'
        print(msg.format(constants.DCOS_PATH_ENV))
        return False

    if not os.path.isdir(dcos_path):
        msg = 'Evironment variable {!r} maps to {!r} which is not a directory.'
        print(msg.format(constants.DCOS_PATH_ENV, dcos_path))
        return False

    dcos_config = os.environ.get(constants.DCOS_CONFIG_ENV)
    if dcos_config is None:
        msg = 'Environment variable {!r} must be set to the DCOS config file.'
        print(msg.format(constants.DCOS_CONFIG_ENV))
        return False

    if not os.path.isfile(dcos_config):
        msg = 'Evironment variable {!r} maps to {!r} and it is not a file.'
        print(msg.format(constants.DCOS_CONFIG_ENV, dcos_config))
        return False

    return True
