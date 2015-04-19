from __future__ import print_function

import json
import os
import shutil
import subprocess

from dcos.api import constants, errors, util

logger = util.get_logger(__name__)

BIN_DIRECTORY = 'Scripts' if util.is_windows_platform() else 'bin'


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
    binpath = os.path.join(dcos_path, BIN_DIRECTORY)
    if util.is_windows_platform():
        commands = [
            os.path.join(binpath, filename)
            for filename in os.listdir(binpath)
            if (filename.startswith(constants.DCOS_COMMAND_PREFIX) and
                (filename.endswith('.exe') and
                os.access(os.path.join(binpath, filename), os.X_OK)))
        ]
    else:
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
        os.path.join(subcommand_directory, package, BIN_DIRECTORY, filename)


        for package in distributions(dcos_path)

        for filename in os.listdir(
            os.path.join(subcommand_directory, package, BIN_DIRECTORY))

        if (filename.startswith(constants.DCOS_COMMAND_PREFIX) and
            os.access(
                os.path.join(
                    subcommand_directory,
                    package,
                    BIN_DIRECTORY,
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
        [executable_path, noun(executable_path), '--info'])

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
    if util.is_windows_platform():
        return basename[len(constants.DCOS_COMMAND_PREFIX):].replace('.exe', '')
    else:
        return basename[len(constants.DCOS_COMMAND_PREFIX):]


def install(distribution_name, install_operation, dcos_path):
    """Installs the dcos cli subcommand

    :param distribution_name: the name of the package
    :type distribution_name: str
    :param install_operation: operation to use to install subcommand
    :type install_operation: dict
    :param dcos_path: path to the dcos cli directory
    :type dcos_path: str
    :returns: an error if the subcommand failed; None otherwise
    :rtype: dcos.api.errors.Error
    """

    subcommand_directory = os.path.join(
        dcos_path,
        constants.DCOS_SUBCOMMAND_SUBDIR)
    if not os.path.exists(subcommand_directory):
        logger.info('Creating directory: %r', subcommand_directory)
        os.mkdir(subcommand_directory, 0o775)

    package_directory = os.path.join(subcommand_directory, distribution_name)

    if 'pip' in install_operation:
        return _install_with_pip(
            distribution_name,
            os.path.join(dcos_path, BIN_DIRECTORY),
            package_directory,
            install_operation['pip'])
    else:
        return errors.DefaultError(
            "Installation methods '{}' not supported".format(
                install_operation.keys()))


def uninstall(distribution_name, dcos_path):
    """Uninstall the dcos cli subcommand

    :param distribution_name: the name of the package
    :type distribution_name: str
    :param dcos_path: the path to the dcos cli directory
    :type dcos_path: str
    """

    subcommand_directory = os.path.join(
        dcos_path,
        constants.DCOS_SUBCOMMAND_SUBDIR,
        distribution_name)

    if os.path.isdir(subcommand_directory):
        shutil.rmtree(subcommand_directory)


def _install_with_pip(
        distribution_name,
        bin_directory,
        package_directory,
        requirements):
    """
    :param distribution_name: the name of the package
    :type distribution_name: str
    :param bin_directory: the path to the directory containing the
                           executables (virtualenv, etc).
    :type bin_directory: str
    :param package_directory: the path to the directory for the package
    :type package_directory: str
    :param requirements: the list of pip requirements
    :type requirements: list of str
    :returns: an Error if it failed to install the package; None otherwise
    :rtype: dcos.api.errors.Error
    """

    new_package_dir = not os.path.exists(package_directory)

    if not os.path.exists(os.path.join(package_directory, BIN_DIRECTORY, 'pip')):
        cmd = [os.path.join(bin_directory, 'virtualenv'), package_directory]
        print(cmd)
        if _execute_command(cmd) != 0:
            return _generic_error(distribution_name)

    with util.temptext() as text_file:
        fd, requirement_path = text_file

        # Write the requirements to the file
        with os.fdopen(fd, 'w') as requirements_file:
            for line in requirements:
                print(line, file=requirements_file)

        cmd = [
            os.path.join(package_directory, BIN_DIRECTORY, 'pip'),
            'install',
            '--requirement',
            requirement_path,
        ]

        if _execute_command(cmd) != 0:
            # We should remove the diretory that we just created
            if new_package_dir:
                shutil.rmtree(package_directory)

            return _generic_error(distribution_name)

    return None


def _execute_command(command):
    """
    :param command: the command to execute
    :type command: list of str
    :returns: the process return code
    :rtype: int
    """

    logger.info('Calling: %r', command)

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)

    stdout, stderr = process.communicate()

    if process.returncode != 0:
        logger.error("Install script's stdout: %s", stdout)
        logger.error("Install script's stderr: %s", stderr)
    else:
        logger.info("Install script's stdout: %s", stdout)
        logger.info("Install script's stderr: %s", stderr)

    return process.returncode


def _generic_error(distribution_name):
    """
    :param package: package name
    :type: str
    :returns: generic error when installing package
    :rtype: dcos.api.errors.Error
    """

    return errors.DefaultError(
        'Error installing {!r} package'.format(distribution_name))
