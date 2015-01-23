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

from ..api import constants, options

_dcos_command_prefix = 'dcos-'


def main():
    if not _is_valid_configuration():
        return 1

    subcommands = _extract_subcommands(
        _list_subcommand_programs(os.environ[constants.DCOS_PATH_ENV]))
    subcommand_summaries = _external_command_documentation(subcommands)

    args = docopt.docopt(
        options.extend_usage_docopt(__doc__, subcommand_summaries),
        version='dcos version {}'.format(constants.version),
        options_first=True)

    argv = [args['<command>']] + args['<args>']

    if args['<command>'] in subcommands:
        command = '{}{}'.format(_dcos_command_prefix, args['<command>'])
        return subprocess.call([command] + argv)
    else:
        print(
            '{!r} is not a dcos command. See "dcos --help".'.format(
                args['<command>']))
        return 1


def _extract_subcommands(sub_programs):
    """List external subcommands

    :param sub_programs: List of the dcos program names
    :type sub_programs: list of str
    :returns: List of subcommands
    :rtype: list of str
    """

    return [filename[len(_dcos_command_prefix):] for filename in sub_programs]


def _list_subcommand_programs(dcos_path):
    """List executable programs in the dcos path that start with the dcos
    prefix

    :param dcos_path: Path to the dcos cli directory
    :type dcos_path: str
    :returns: List of all the dcos program names
    :rtype: list of str
    """

    return [
        filename

        for dirpath, _, filenames
        in os.walk(_binary_directory(dcos_path))

        for filename in filenames

        if filename.startswith(_dcos_command_prefix)
        and os.access(os.path.join(dirpath, filename), os.X_OK)
    ]


def _binary_directory(dcos_path):
    """Construct dcos binary directory

    :param dcos_path: Path to the dcos cli directory
    :type dcos_path: str
    :returns: Path to binary directory
    :rtype: str
    """

    return os.path.join(dcos_path, "bin")


def _external_command_documentation(commands):
    """Gather sub-command summary

    :param commands: List of subcommand
    :type comands: list of str
    :returns: Returns a list of subcommand and their summary
    :rtype: list of (str, str)
    """
    def info(commnand):
        return subprocess.check_output(
            ['{}{}'.format(_dcos_command_prefix, command), command, 'info'])

    return [(command, info(command)) for command in commands]


def _is_valid_configuration():
    """Validates running environment

    :returns: True if the environment is configure correctly, False otherwise.
    :rtype: bool
    """

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
