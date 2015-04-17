import os

from dcos.api import constants, util

from common import exec_command


def test_default():
    dcos_path = os.path.dirname(os.path.dirname(util.which('dcos')))
    returncode, stdout, stderr = exec_command(['dcos'])

    assert returncode == 0
    assert stdout == """\
Command line utility for the Mesosphere Datacenter Operating
System (DCOS). The Mesosphere DCOS is a distributed operating
system built around Apache Mesos. This utility provides tools
for easy management of a DCOS installation.

Available DCOS commands in '{}':

\tauth           \tStore user authentication information
\tconfig         \tGet and set DCOS command line options
\thelp           \tDisplay command line usage information
\tmarathon       \tDeploy and manage applications on the DCOS
\tpackage        \tInstall and manage DCOS software packages
\tsubcommand     \tInstall and manage DCOS CLI subcommands

Get detailed command description with 'dcos <command> --help'.
""".format(dcos_path).encode('utf-8')
    assert stderr == b''


def test_help():
    returncode, stdout, stderr = exec_command(['dcos', '--help'])

    assert returncode == 0
    assert stdout == b"""Usage:
    dcos [options] [<command>] [<args>...]

Options:
    --help                      Show this screen
    --version                   Show version
    --log-level=<log-level>     If set then print supplementary messages to
                                stderr at or above this level. The severity
                                levels in the order of severity are: debug,
                                info, warning, error, and critical. E.g.
                                Setting the option to warning will print
                                warning, error and critical messages to stderr.
                                Note: that this does not affect the output sent
                                to stdout by the command.

Environment Variables:
    DCOS_LOG_LEVEL              If set then it specifies that message should be
                                printed to stderr at or above this level. See
                                the --log-level option for details.

    DCOS_CONFIG                 This environment variable points to the
                                location of the DCOS configuration file.

'dcos help' lists all available subcommands. See 'dcos <command> --help'
to read about a specific subcommand.
"""
    assert stderr == b''


def test_version():
    returncode, stdout, stderr = exec_command(['dcos', '--version'])

    assert returncode == 0
    assert stdout == b'dcos version 0.1.0\n'
    assert stderr == b''


def test_missing_dcos_config():
    env = {
        constants.PATH_ENV: os.environ[constants.PATH_ENV],
    }

    returncode, stdout, stderr = exec_command(['dcos'], env=env)

    assert returncode == 1
    assert stdout == (b"Environment variable 'DCOS_CONFIG' must be set "
                      b"to the DCOS config file.\n")
    assert stderr == b''


def test_dcos_config_not_a_file():
    env = {
        constants.PATH_ENV: os.environ[constants.PATH_ENV],
        'DCOS_CONFIG': 'missing/file',
    }

    returncode, stdout, stderr = exec_command(['dcos'], env=env)

    assert returncode == 1
    assert stdout == (b"Environment variable 'DCOS_CONFIG' maps to "
                      b"'missing/file' and it is not a file.\n")
    assert stderr == b''


def test_log_level_flag():
    returncode, stdout, stderr = exec_command(
        ['dcos', '--log-level=info', 'config', '--info'])

    assert returncode == 0
    assert stdout == b"Get and set DCOS command line options\n"
    assert stderr == b''


def test_capital_log_level_flag():
    returncode, stdout, stderr = exec_command(
        ['dcos', '--log-level=INFO', 'config', '--info'])

    assert returncode == 0
    assert stdout == b"Get and set DCOS command line options\n"
    assert stderr == b''


def test_invalid_log_level_flag():
    returncode, stdout, stderr = exec_command(
        ['dcos', '--log-level=blah', 'config', '--info'])

    assert returncode == 1
    assert stdout == (b"Log level set to an unknown value 'blah'. Valid "
                      b"values are ['debug', 'info', 'warning', 'error', "
                      b"'critical']\n")
    assert stderr == b''
