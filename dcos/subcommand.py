from __future__ import print_function

import json
import os
import shutil
import subprocess

from dcos import constants, errors, util

logger = util.get_logger(__name__)


def command_executables(subcommand, dcos_path):
    """List the real path to executable dcos program for specified subcommand.

    :param subcommand: name of subcommand. E.g. marathon
    :type subcommand: str
    :param dcos_path: path to the dcos cli directory
    :type dcos_path: str
    :returns: the dcos program path
    :rtype: (str, dcos.errors.Error)
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
    commands = [
        os.path.join(binpath, filename)
        for filename in os.listdir(binpath)
        if (filename.startswith(constants.DCOS_COMMAND_PREFIX) and
            _is_executable(os.path.join(binpath, filename)))
    ]

    subcommands = []
    for package in distributions(dcos_path):
        bin_dir = os.path.join(package_dir(package),
                               constants.DCOS_SUBCOMMAND_VIRTUALENV_SUBDIR,
                               BIN_DIRECTORY)

        for filename in os.listdir(bin_dir):
            path = os.path.join(bin_dir, filename)

            if (filename.startswith(constants.DCOS_COMMAND_PREFIX) and
                    _is_executable(path)):

                subcommands.append(path)

    return commands + subcommands


def _is_executable(path):
    """
    :param path: the path to a program
    :type path: str
    :returns: True if the path is an executable; False otherwise
    :rtype: bool
    """

    return os.access(path, os.X_OK) and (
        not util.is_windows_platform() or path.endswith('.exe'))


def distributions(dcos_path):
    """List all of the installed subcommand packages

    :param dcos_path: path to the dcos cli directory
    :type dcos_path: str
    :returns: a list of packages
    :rtype: list of str
    """

    subcommand_dir = _subcommand_dir()

    if os.path.isdir(subcommand_dir):
        return [
            subdir for subdir in os.listdir(subcommand_dir)
            if os.path.isdir(
                os.path.join(
                    subcommand_dir,
                    subdir,
                    constants.DCOS_SUBCOMMAND_VIRTUALENV_SUBDIR))
        ]
    else:
        return []


def documentation(executable_path):
    """Gather subcommand summary

    :param executable_path: real path to the dcos subcommands
    :type executable_path: str
    :returns: subcommand and its summary
    :rtype: (str, str)
    """

    path_noun = noun(executable_path)
    return (path_noun, info(executable_path, path_noun))


def info(executable_path, path_noun):
    """Collects subcommand information

    :param executable_path: real path to the dcos subcommand
    :type executable_path: str
    :param path_noun: subcommand
    :type path_noun: str
    :returns: the subcommand information
    :rtype: str
    """

    out = subprocess.check_output(
        [executable_path, path_noun, '--info'])

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
    noun = basename[len(constants.DCOS_COMMAND_PREFIX):].replace('.exe', '')
    return noun


def _write_package_json(pkg, version):
    """ Write package.json locally.

    :param pkg: the package being installed
    :type pkg: Package
    :param version: the package version to install
    :type version: str
    :rtype: Error
    """

    pkg_dir = package_dir(pkg.name())

    package_path = os.path.join(pkg_dir, 'package.json')

    package_json, err = pkg.package_json(version)
    if err is not None:
        return err

    with open(package_path, 'w') as package_file:
        json.dump(package_json, package_file)


def _write_package_version(pkg, version):
    """ Write package version locally.

    :param pkg: the package being installed
    :type pkg: Package
    :param version: the package version to install
    :type version: str
    :rtype: None
    """

    pkg_dir = package_dir(pkg.name())

    version_path = os.path.join(pkg_dir, 'version')

    with open(version_path, 'w') as version_file:
        version_file.write(version)


def _write_package_source(pkg):
    """ Write package source locally.

    :param pkg: the package being installed
    :type pkg: Package
    :rtype: None
    """

    pkg_dir = package_dir(pkg.name())

    source_path = os.path.join(pkg_dir, 'source')

    with open(source_path, 'w') as source_file:
        source_file.write(pkg.registry.source.url)


def _install_env(pkg, version, options):
    """ Install subcommand virtual env.

    :param pkg: the package to install
    :type pkg: Package
    :param version: the package version to install
    :type version: str
    :param options: package parameters
    :type options: dict
    :returns: an error if the subcommand failed; None otherwise
    :rtype: dcos.errors.Error
    """

    pkg_dir = package_dir(pkg.name())

    install_operation, err = pkg.command_json(version, options)
    if err is not None:
        return err

    env_dir = os.path.join(pkg_dir,
                           constants.DCOS_SUBCOMMAND_VIRTUALENV_SUBDIR)

    if 'pip' in install_operation:
        return install_with_pip(
            pkg.name(),
            env_dir,
            install_operation['pip'])
    else:
        return errors.DefaultError(
            "Installation methods '{}' not supported".format(
                install_operation.keys()))


def install(pkg, version, options):
    """Installs the dcos cli subcommand

    :param pkg: the package to install
    :type pkg: Package
    :param version: the package version to install
    :type version: str
    :param options: package parameters
    :type options: dict
    :returns: an error if the subcommand failed; None otherwise
    :rtype: dcos.errors.Error
    """

    pkg_dir = package_dir(pkg.name())
    util.ensure_dir(pkg_dir)

    err = _write_package_json(pkg, version)
    if err is not None:
        return err

    _write_package_version(pkg, version)

    _write_package_source(pkg)

    return _install_env(pkg, version, options)


def _subcommand_dir():
    """ Returns ~/.dcos/subcommands """
    return os.path.expanduser(os.path.join("~",
                                           constants.DCOS_DIR,
                                           constants.DCOS_SUBCOMMAND_SUBDIR))


# TODO(mgummelt): should be made private after "dcos subcommand" is removed
def package_dir(name):
    """ Returns ~/.dcos/subcommands/<name>

    :param name: package name
    :type name: str
    :rtype: str
    """
    return os.path.join(_subcommand_dir(),
                        name)


def uninstall(package_name):
    """Uninstall the dcos cli subcommand

    :param package_name: the name of the package
    :type package_name: str
    :returns: True if the subcommand was uninstalled
    :rtype: bool
    """

    pkg_dir = package_dir(package_name)

    if os.path.isdir(pkg_dir):
        shutil.rmtree(pkg_dir)
        return True

    return False

BIN_DIRECTORY = 'Scripts' if util.is_windows_platform() else 'bin'


# TODO (mgummelt): should be made private after "dcos subcommand" is removed
def install_with_pip(
        package_name,
        env_directory,
        requirements):
    """
    :param package_name: the name of the package
    :type package_name: str
    :param env_directory: the path to the directory in which to install the
                          package's virtual env
    :type env_directory: str
    :param requirements: the list of pip requirements
    :type requirements: list of str
    :returns: an Error if it failed to install the package; None otherwise
    :rtype: dcos.errors.Error
    """

    bin_directory = os.path.join(util.dcos_path(), BIN_DIRECTORY)
    new_package_dir = not os.path.exists(env_directory)

    pip_path = os.path.join(env_directory, BIN_DIRECTORY, 'pip')
    if not os.path.exists(pip_path):
        cmd = [os.path.join(bin_directory, 'virtualenv'), env_directory]

        if _execute_command(cmd) != 0:
            return _generic_error(package_name)

    with util.temptext() as text_file:
        fd, requirement_path = text_file

        # Write the requirements to the file
        with os.fdopen(fd, 'w') as requirements_file:
            for line in requirements:
                print(line, file=requirements_file)

        cmd = [
            os.path.join(env_directory, BIN_DIRECTORY, 'pip'),
            'install',
            '--requirement',
            requirement_path,
        ]

        if _execute_command(cmd) != 0:
            # We should remove the diretory that we just created
            if new_package_dir:
                shutil.rmtree(env_directory)

            return _generic_error(package_name)

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


def _generic_error(package_name):
    """
    :param package: package name
    :type: str
    :returns: generic error when installing package
    :rtype: dcos.errors.Error
    """

    return errors.DefaultError(
        'Error installing {!r} package'.format(package_name))


class InstalledSubcommand(object):
    """ Represents an installed subcommand.

    :param name: The name of the subcommand
    :type name: str
    """

    def __init__(self, name):
        self.name = name

    def _dir(self):
        """
        :returns: path to this subcommand's directory.
        :rtype: (str, Error)
        """

        return package_dir(self.name)

    def package_version(self):
        """
        :returns: this subcommand's version.
        :rtype: (str, Error)
        """

        version_path = os.path.join(self._dir(), 'version')
        return util.read_file(version_path)

    def package_source(self):
        """
        :returns: this subcommand's source.
        :rtype: (str, Error)
        """

        source_path = os.path.join(self._dir(), 'source')
        return util.read_file(source_path)

    def package_json(self):
        """
        :returns: contents of this subcommand's package.json file.
        :rtype: (dict, Error)
        """

        package_json_path = os.path.join(self._dir(), 'package.json')
        with open(package_json_path) as package_json_file:
            return util.load_json(package_json_file)
