"""Install and manage DCOS CLI Subcommands

Usage:
    dcos subcommand --config-schema
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
import json
import os
import shutil
import subprocess

import dcoscli
import docopt
import pkg_resources
import pkginfo
from dcos.api import (cmds, config, constants, emitting, errors, options,
                      subcommand, util)

logger = util.get_logger(__name__)
emitter = emitting.FlatEmitter()


def main():
    err = util.configure_logger_from_environ()
    if err is not None:
        emitter.publish(err)
        return 1

    args = docopt.docopt(
        __doc__,
        version='dcos-subcommand version {}'.format(dcoscli.version))

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

        cmds.Command(
            hierarchy=['subcommand'],
            arg_keys=['--config-schema'],
            function=_subcommand),
    ]


def _subcommand(config_schema):
    """
    :returns: Process status
    :rtype: int
    """

    if config_schema:
        schema = json.loads(
            pkg_resources.resource_string(
                'dcoscli',
                'data/config-schema/subcommand.json').decode('utf-8'))
        emitter.publish(schema)
    else:
        emitter.publish(options.make_generic_usage_message(__doc__))
        return 1

    return 0


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

    dcos_config = config.load_from_path(os.environ[constants.DCOS_CONFIG_ENV])

    bin_directory = os.path.dirname(util.process_executable_path())

    subcommand_directory = os.path.join(
        os.path.dirname(bin_directory),
        constants.DCOS_SUBCOMMAND_SUBDIR)
    if not os.path.exists(subcommand_directory):
        logger.info('Creating directory: %r', subcommand_directory)
        os.mkdir(subcommand_directory, 0o775)

    distribution_name, err = _distribution_name(package)
    if err is not None:
        emitter.publish(err)
        return 1

    package_directory = os.path.join(subcommand_directory, distribution_name)

    err = _install_subcommand(
        bin_directory,
        package_directory,
        package,
        dcos_config.get('subcommand.pip_find_links'))
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
    :rtype: (str, dcos.api.errors.Error)
    """

    try:
        return (pkginfo.Wheel(package_path).name, None)
    except ValueError as error:
        logger.error('Failed to read wheel (%s): %r', package_path, error)
        return (
            None,
            errors.DefaultError(
                'Failed to read file: {}'.format(error))
        )


def _install_subcommand(
        bin_directory,
        package_directory,
        package,
        wheel_cache):
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

    new_package_dir = not os.path.exists(package_directory)

    if not os.path.exists(os.path.join(package_directory, 'bin', 'pip')):
        cmd = [os.path.join(bin_directory, 'virtualenv'), package_directory]

        if _execute_command(cmd) != 0:
            return _generic_error(package)

    cmd = [
        os.path.join(package_directory, 'bin', 'pip'),
        'install',
        '--upgrade',
        '--force-reinstall',
    ]

    if wheel_cache is not None:
        cmd.append('--find-links')
        cmd.append(wheel_cache)

    cmd.append(package)

    if _execute_command(cmd) != 0:
        # We should remove the diretory that we just created
        if new_package_dir:
            shutil.rmtree(package_directory)

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
    distribution_name, err = _distribution_name(package)
    if err is not None:
        return err

    return errors.DefaultError(
        'Error installing {!r} package'.format(distribution_name))
