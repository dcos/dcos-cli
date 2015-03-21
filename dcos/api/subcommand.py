import json
import os
import subprocess

from dcos.api import constants, errors


def command_executables(subcommand, dcos_path):
    """List the real path to executable dcos program for specified subcommand.

    :param subcommand: name of subcommand. E.g. marathon
    :type subcommand: str
    :param dcos_path: path to the dcos cli directory
    :type dcos_path: str
    :returns: the dcos program path
    :rtype: (str, dcos.api.errors.Error)
    """

    executables = [
        command_path
        for command_path in list_paths(dcos_path)
        if noun(command_path) == subcommand
    ]

    if len(executables) > 1:
        msg = 'Found more than one executable for command {!r}.'
        return (None, errors.DefaultError(msg.format(subcommand)))

    if len(executables) == 0:
        msg = "{!r} is not a dcos command."
        return (None, errors.DefaultError(msg.format(subcommand)))

    return (executables[0], None)


def list_paths(dcos_path):
    """List the real path to executable dcos subcommand programs.

    :param dcos_path: path to the dcos cli directory
    :type dcos_path: str
    :returns: list of all the dcos program paths
    :rtype: list of str
    """

    # Let's get all the default subcommands
    binpath = os.path.join(dcos_path, 'bin')
    commands = [
        os.path.join(binpath, filename)
        for filename in os.listdir(binpath)
        if (filename.startswith(constants.DCOS_COMMAND_PREFIX) and
            os.access(os.path.join(binpath, filename), os.X_OK))
    ]

    subcommand_directory = os.path.join(
        dcos_path,
        constants.DCOS_SUBCOMMAND_SUBDIR)

    subcommands = [
        os.path.join(subcommand_directory, package, 'bin', filename)


        for package in distributions(dcos_path)

        for filename in os.listdir(
            os.path.join(subcommand_directory, package, 'bin'))

        if (filename.startswith(constants.DCOS_COMMAND_PREFIX) and
            os.access(
                os.path.join(
                    subcommand_directory,
                    package,
                    'bin',
                    filename),
                os.X_OK))
    ]

    return commands + subcommands


def distributions(dcos_path):
    """List all of the installed subcommand packages

    :param dcos_path: path to the dcos cli directory
    :type dcos_path: str
    :returns: a list of packages
    :rtype: list of str
    """

    subcommand_directory = os.path.join(
        dcos_path,
        constants.DCOS_SUBCOMMAND_SUBDIR)

    if os.path.isdir(subcommand_directory):
        return os.listdir(subcommand_directory)
    else:
        return []


def documentation(executable_path):
    """Gather subcommand summary

    :param executable_path: real path to the dcos subcommands
    :type executable_path: str
    :returns: subcommand and its summary
    :rtype: (str, str)
    """

    return (noun(executable_path), info(executable_path))


def info(executable_path):
    """Collects subcommand information

    :param executable_path: real path to the dcos subcommand
    :type executable_path: str
    :returns: the subcommand information
    :rtype: str
    """

    out = subprocess.check_output(
        [executable_path, noun(executable_path), 'info'])

    return out.decode('utf-8').strip()


def config_schema(executable_path):
    """Collects subcommand config schema

    :param executable_path: real path to the dcos subcommand
    :type executable_path: str
    :returns: the subcommand config schema
    :rtype: dict
    """

    out = subprocess.check_output(
        [executable_path, noun(executable_path), '--config-schema'])

    return json.loads(out.decode('utf-8'))


def noun(executable_path):
    """Extracts the subcommand single noun from the path to the executable.
    E.g for :code:`bin/dcos-subcommand` this method returns :code:`subcommand`.

    :param executable_path: real pth to the dcos subcommand
    :type executable_path: str
    :returns: the subcommand
    :rtype: str
    """

    basename = os.path.basename(executable_path)
    return basename[len(constants.DCOS_COMMAND_PREFIX):]
