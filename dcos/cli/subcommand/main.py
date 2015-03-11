"""Install and manage DCOS CLI Subcommands

Usage:
    dcos subcommand info
    dcos subcommand install <package>
    dcos subcommand list
    dcos subcommand uninstall <package_name>

Options:
    --help             Show this screen
    --version          Show version

Positional arguments:
    <package>          The subcommand package wheel
    <package_name>     The name of the subcommand package
"""
import os
import shutil
import subprocess

import docopt
import pkginfo
from dcos.api import (cmds, constants, emitting, errors, options, subcommand,
                      util)

logger = util.get_logger(__name__)
emitter = emitting.FlatEmitter()


def main():
    err = util.configure_logger_from_environ()
    if err is not None:
        emitter.publish(err)
        return 1

    args = docopt.docopt(
        __doc__,
        version='dcos-subcommand version {}'.format(constants.version))

    returncode, err = cmds.execute(_cmds(), args)
    if err is not None:
        emitter.publish(err)
        emitter.publish(options.make_generic_usage_message(__doc__))
        return 1

    return returncode


def _cmds():
    """
    :returns: all the supported commands
    :rtype: dcos.api.cmds.Command
    """

    return [
        cmds.Command(
            hierarchy=['subcommand', 'install'],
            arg_keys=['<package>'],
            function=_install),

        cmds.Command(
            hierarchy=['subcommand', 'uninstall'],
            arg_keys=['<package_name>'],
            function=_uninstall),

        cmds.Command(
            hierarchy=['subcommand', 'list'],
            arg_keys=[],
            function=_list),

        cmds.Command(
            hierarchy=['subcommand', 'info'],
            arg_keys=[],
            function=_info),
    ]


def _info():
    """
    :returns: the process return code
    :rtype: int
    """

    emitter.publish(__doc__.split('\n')[0])

    return 0


def _list():
    """
    :returns: the process return code
    :rtype: int
    """

    emitter.publish(subcommand.distributions(util.dcos_path()))

    return 0


def _install(package):
    """
    :returns: the process return code
    :rtype: int
    """

    bin_directory = os.path.dirname(util.process_executable_path())

    subcommand_directory = os.path.join(
        os.path.dirname(bin_directory),
        constants.DCOS_SUBCOMMAND_SUBDIR)
    if not os.path.exists(subcommand_directory):
        logger.info('Creating directory: %r', subcommand_directory)
        os.mkdir(subcommand_directory, 0o775)

    package_directory = os.path.join(
        subcommand_directory,
        _distribution_name(package))
    if not os.path.exists(package_directory):
        logger.info('Creating directory: %r', package_directory)
        os.mkdir(package_directory, 0o775)

    err = _install_subcommand(bin_directory, package_directory, package)
    if err is not None:
        emitter.publish(err)
        return 1

    return 0


def _uninstall(package_name):
    """
    :returns: the process return code
    :rtype: int
    """

    subcommand_directory = os.path.join(
        util.dcos_path(),
        constants.DCOS_SUBCOMMAND_SUBDIR,
        package_name)

    if os.path.isdir(subcommand_directory):
        shutil.rmtree(subcommand_directory)

    return 0


def _distribution_name(package_path):
    """
    :returns: the distribution's name
    :rtype: str
    """

    distribution = pkginfo.Wheel(package_path)
    return distribution.name


def _install_subcommand(bin_directory, package_directory, package):
    """
    :param: bin_directory: the path to the directory containing the
                           executables (virtualenv, etc).
    :type: str
    :param package_directory: the path to the directory for the package
    :type: str
    :param package: the path to Python wheel package
    :type: str
    :returns: an Error if it failed to install the package; None otherwise
    :rtype: dcos.api.errors.Error
    """

    if not os.path.exists(os.path.join(package_directory, 'bin', 'activate')):
        cmd = [os.path.join(bin_directory, 'virtualenv'), package_directory]
        logger.info('Calling: %r', cmd)

        if _execute_command(cmd) != 0:
            return _generic_error(package)

    cmd = [
        os.path.join(package_directory, 'bin', 'pip'),
        'install',
        '--upgrade',
        '--force-reinstall',
        package,
    ]

    if _execute_command(cmd) != 0:
        return _generic_error(package)

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


def _generic_error(package):
    """
    :param package: path the subcommand package
    :type: str
    :returns: generic error when installing package
    :rtype: dcos.api.errors.Error
    """

    return errors.DefaultError(
        'Error installing {!r} package'.format(
            _distribution_name(package)))
