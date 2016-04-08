from __future__ import print_function

import json
import os
import shutil
import subprocess
import sys
from subprocess import PIPE, Popen

from dcos import constants, emitting, util
from dcos.errors import DCOSException

logger = util.get_logger(__name__)
emitter = emitting.FlatEmitter()


def command_executables(subcommand):
    """List the real path to executable dcos program for specified subcommand.

    :param subcommand: name of subcommand. E.g. marathon
    :type subcommand: str
    :returns: the dcos program path
    :rtype: str
    """

    executables = []
    if subcommand in default_subcommands():
        executables += [default_list_paths()]

    executables += [
        command_path
        for command_path in list_paths()
        if noun(command_path) == subcommand
    ]

    if len(executables) > 1:
        msg = 'Found more than one executable for command {!r}.'
        raise DCOSException(msg.format(subcommand))

    if len(executables) == 0:
        msg = "{!r} is not a dcos command."
        raise DCOSException(msg.format(subcommand))

    return executables[0]


def get_package_commands(package_name):
    """List the real path(s) to executables for a specific dcos subcommand

    :param package_name: package name
    :type package_name: str
    :returns: list of all the dcos program paths in package
    :rtype: [str]
    """
    bin_dir = os.path.join(_package_dir(package_name),
                           constants.DCOS_SUBCOMMAND_VIRTUALENV_SUBDIR,
                           BIN_DIRECTORY)

    executables = []
    for filename in os.listdir(bin_dir):
        path = os.path.join(bin_dir, filename)

        if (filename.startswith(constants.DCOS_COMMAND_PREFIX) and
                _is_executable(path)):

            executables.append(path)

    return executables


def default_list_paths():
    """List the real path to dcos executable

    :returns: list dcos program path
    :rtype: str
    """

    # Let's get all the default subcommands
    binpath = util.dcos_bin_path()
    return os.path.join(binpath, "dcos")


def list_paths():
    """List the real path to executable dcos subcommand programs.

    :returns: list of all the dcos program paths
    :rtype: [str]
    """

    subcommands = []
    for package in distributions():
        subcommands += get_package_commands(package)

    return subcommands


def _is_executable(path):
    """
    :param path: the path to a program
    :type path: str
    :returns: True if the path is an executable; False otherwise
    :rtype: bool
    """

    return os.access(path, os.X_OK) and (
        not util.is_windows_platform() or path.endswith('.exe'))


def distributions():
    """List all of the installed subcommand packages

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


def default_subcommands():
    """List the default dcos cli subcommands

    :returns: list of all the default dcos cli subcommands
    :rtype: [str]
    """
    return ["auth", "config", "help", "marathon",
            "node", "package", "service", "task"]


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


def config_schema(executable_path, noun=None):
    """Collects subcommand config schema

    :param executable_path: real path to the dcos subcommand
    :type executable_path: str
    :param noun: name of subcommand
    :type noun: str
    :returns: the subcommand config schema
    :rtype: dict
    """
    if noun is None:
        noun = noun(executable_path)
    out = subprocess.check_output(
        [executable_path, noun, '--config-schema'])

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


def _write_package_json(pkg):
    """ Write package.json locally.

    :param pkg: the package being installed
    :type pkg: PackageVersion
    :rtype: None
    """

    pkg_dir = _package_dir(pkg.name())

    package_path = os.path.join(pkg_dir, 'package.json')

    package_json = pkg.package_json()

    with util.open_file(package_path, 'w') as package_file:
        json.dump(package_json, package_file)


def _install_env(pkg, options):
    """ Install subcommand virtual env.

    :param pkg: the package to install
    :type pkg: PackageVersion
    :param options: package parameters
    :type options: dict
    :rtype: None
    """

    pkg_dir = _package_dir(pkg.name())

    install_operation = pkg.command_json(options)

    env_dir = os.path.join(pkg_dir,
                           constants.DCOS_SUBCOMMAND_VIRTUALENV_SUBDIR)

    if 'pip' in install_operation:
        _install_with_pip(
            pkg.name(),
            env_dir,
            install_operation['pip'])
    else:
        raise DCOSException("Installation methods '{}' not supported".format(
            install_operation.keys()))


def install(pkg, options):
    """Installs the dcos cli subcommand

    :param pkg: the package to install
    :type pkg: Package
    :param options: package parameters
    :type options: dict
    :rtype: None
    """

    pkg_dir = _package_dir(pkg.name())
    util.ensure_dir_exists(pkg_dir)

    _write_package_json(pkg)

    _install_env(pkg, options)


def _subcommand_dir():
    """ Returns ~/.dcos/subcommands """
    return os.path.expanduser(os.path.join("~",
                                           constants.DCOS_DIR,
                                           constants.DCOS_SUBCOMMAND_SUBDIR))


def _package_dir(name):
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

    pkg_dir = _package_dir(package_name)

    if os.path.isdir(pkg_dir):
        shutil.rmtree(pkg_dir)
        return True

    return False

BIN_DIRECTORY = 'Scripts' if util.is_windows_platform() else 'bin'


def _find_virtualenv(bin_directory):
    """
    :param bin_directory: directory to first use to find virtualenv
    :type bin_directory: str
    :returns: Absolute path to virutalenv program
    :rtype: str
    """

    virtualenv_path = os.path.join(bin_directory, 'virtualenv')
    if not os.path.exists(virtualenv_path):
        virtualenv_path = util.which('virtualenv')

    if virtualenv_path is None:
        raise DCOSException('Unable to find the virtualenv program')

    return virtualenv_path


def _install_with_pip(
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
    :rtype: None
    """

    bin_directory = util.dcos_bin_path()
    new_package_dir = not os.path.exists(env_directory)

    pip_path = os.path.join(env_directory, BIN_DIRECTORY, 'pip')
    if not os.path.exists(pip_path):
        cmd = [_find_virtualenv(bin_directory), env_directory]

        if _execute_install(cmd) != 0:
            raise _generic_error(package_name)

    # Do not replace util.temptext NamedTemporaryFile
    # otherwise bad things will happen on Windows
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

        if _execute_install(cmd) != 0:
            # We should remove the directory that we just created
            if new_package_dir:
                shutil.rmtree(env_directory)

            raise _generic_error(package_name)

    return None


def _execute_install(command):
    """
    :param command: the install command to execute
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
    :rtype: DCOSException
    """

    return DCOSException(
        ('Error installing {!r} package.\n'
         'Run with `dcos --log-level=ERROR` to see the full output.').format(
            package_name))


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
        :rtype: str
        """

        return _package_dir(self.name)

    def package_revision(self):
        """
        :returns: this subcommand's version.
        :rtype: str
        """

        version_path = os.path.join(self._dir(), 'version')
        return util.read_file(version_path)

    def package_source(self):
        """
        :returns: this subcommand's source.
        :rtype: str
        """

        source_path = os.path.join(self._dir(), 'source')
        return util.read_file(source_path)

    def package_json(self):
        """
        :returns: contents of this subcommand's package.json file.
        :rtype: dict
        """

        package_json_path = os.path.join(self._dir(), 'package.json')
        with util.open_file(package_json_path) as package_json_file:
            return util.load_json(package_json_file)


class SubcommandProcess():

    def __init__(self, executable, command, args):
        """Representes a subcommand running by a forked process

        :param executable: executable to run
        :type executable: executable
        :param command: command to run by executable
        :type command: str
        :param args: arguments for command
        :type args: [str]
        """

        self._executable = executable
        self._command = command
        self._args = args

    def run_and_capture(self):
        """
        Run a command and capture exceptions. This is a blocking call
        :returns: tuple of exitcode, error (or None)
        :rtype: int, str | None
        """

        subproc = Popen([self._executable,  self._command] + self._args,
                        stderr=PIPE)
        err = ''
        while subproc.poll() is None:
            line = subproc.stderr.readline().decode('utf-8')
            err += line
            sys.stderr.write(line)
            sys.stderr.flush()

        exitcode = subproc.poll()
        # We only want to catch exceptions, not other stderr messages
        # (such as "task does not exist", so we look for the 'Traceback'
        # string.  This only works for python, so we'll need to revisit
        # this in the future when we support subcommands written in other
        # languages.
        err = ('Traceback' in err and err) or None

        return exitcode, err
