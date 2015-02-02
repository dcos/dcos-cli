"""
Usage:
    dcos help info
    dcos help --all

Options:
    -h, --help          Show this screen
    --version           Show version
    --all               Prints all the avaible commands to the standard output
"""

import os
import subprocess

import docopt
from dcos.api import constants, options, util


def main():
    error = util.configure_logger_from_environ()
    if error is not None:
        print(error.error())
        return 1

    args = docopt.docopt(
        __doc__,
        version='dcos-help version {}'.format(constants.version))

    if args['help'] and args['info']:
        print('Display help information about DCOS')
    elif args['help'] and args['--all']:
        directory = _binary_directory(os.environ[constants.DCOS_PATH_ENV])
        print("Available DCOS command in '{}':".format(directory))
        print(
            options.make_command_summary_string(
                _external_command_documentation(
                    _extract_subcommands(
                        _list_subcommand_programs(directory)))))
        print("\nGet detail command description with 'dcos <command> --help'.")

        return 0
    else:
        print(options.make_generic_usage_error(__doc__))
        return 1


def _extract_subcommands(sub_programs):
    """List external subcommands

    :param sub_programs: List of the dcos program names
    :type sub_programs: list of str
    :returns: List of subcommands
    :rtype: list of str
    """

    return sorted([
        filename[len(constants.DCOS_COMMAND_PREFIX):]
        for filename
        in sub_programs
    ])


def _list_subcommand_programs(dcos_bin_path):
    """List executable programs in the dcos path that start with the dcos
    prefix

    :param dcos_bin_path: Path to the dcos cli bin directory
    :type dcos_bin_path: str
    :returns: List of all the dcos program names
    :rtype: list of str
    """

    return [
        filename

        for dirpath, _, filenames
        in os.walk(dcos_bin_path)

        for filename in filenames

        if filename.startswith(constants.DCOS_COMMAND_PREFIX)
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
    def info(command):
        out = subprocess.check_output(
            ['{}{}'.format(
                constants.DCOS_COMMAND_PREFIX, command), command, 'info'])
        return out.decode('utf-8')

    return [(command, info(command)) for command in commands]
