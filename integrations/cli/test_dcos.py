import os

from common import exec_command
from dcos.api import util


def test_help():
    returncode, stdout, stderr = exec_command(['dcos', '--help'])

    assert returncode == 0
    assert stdout == b"""Usage:
    dcos [--log-level=<log-level>] <command> [<args>...]

Options:
    -h, --help                  Show this screen
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

'dcos help --all' lists available subcommands. See 'dcos <command> --help' to
read about a specific subcommand.
"""
    assert stderr == b''


def test_version():
    returncode, stdout, stderr = exec_command(['dcos', '--version'])

    assert returncode == 0
    assert stdout == b'dcos version 0.1.0\n'
    assert stderr == b''


def test_missing_dcos_config():
    env = {
        'PATH': os.environ['PATH'],
        'DCOS_PATH': os.environ['DCOS_PATH'],
    }

    returncode, stdout, stderr = exec_command(['dcos'], env=env)

    assert returncode == 1
    assert stdout == (b"Environment variable 'DCOS_CONFIG' must be set "
                      b"to the DCOS config file.\n")
    assert stderr == b''


def test_dcos_config_not_a_file():
    env = {
        'PATH': os.environ['PATH'],
        'DCOS_PATH': os.environ['DCOS_PATH'],
        'DCOS_CONFIG': 'missing/file',
    }

    returncode, stdout, stderr = exec_command(['dcos'], env=env)

    assert returncode == 1
    assert stdout == (b"Environment variable 'DCOS_CONFIG' maps to "
                      b"'missing/file' and it is not a file.\n")
    assert stderr == b''


def test_missing_dcos_path():
    env = {
        'PATH': os.environ['PATH'],
        'DCOS_CONFIG': os.environ['DCOS_CONFIG'],
    }

    returncode, stdout, stderr = exec_command(['dcos'], env=env)

    assert returncode == 1
    assert stdout == (b"Environment variable 'DCOS_PATH' not set to the DCOS "
                      b"CLI path.\n")
    assert stderr == b''


def test_dcos_path_not_a_dir():
    env = {
        'PATH': os.environ['PATH'],
        'DCOS_CONFIG': os.environ['DCOS_CONFIG'],
        'DCOS_PATH': 'missing/dir',
    }

    returncode, stdout, stderr = exec_command(['dcos'], env=env)

    assert returncode == 1
    assert stdout == (b"Environment variable 'DCOS_PATH' maps to "
                      b"'missing/dir' which is not a directory.\n")
    assert stderr == b''


def test_missing_path():
    env = {
        'DCOS_CONFIG': os.environ['DCOS_CONFIG'],
        'DCOS_PATH': os.environ['DCOS_PATH'],
    }

    returncode, stdout, stderr = exec_command([util.which('dcos')], env=env)

    assert returncode == 1
    assert stdout == b"Environment variable 'PATH' not set.\n"
    assert stderr == b''


def test_log_level_flag():
    returncode, stdout, stderr = exec_command(
        ['dcos', '--log-level=info', 'config', 'info'])

    assert returncode == 0
    assert stdout == b"Get and set DCOS command line options\n"
    assert stderr == b''


def test_capital_log_level_flag():
    returncode, stdout, stderr = exec_command(
        ['dcos', '--log-level=INFO', 'config', 'info'])

    assert returncode == 0
    assert stdout == b"Get and set DCOS command line options\n"
    assert stderr == b''


def test_invalid_log_level_flag():
    returncode, stdout, stderr = exec_command(
        ['dcos', '--log-level=blah', 'config', 'info'])

    assert returncode == 1
    assert stdout == (b"Log level set to an unknown value 'blah'. Valid "
                      b"values are ['debug', 'info', 'warning', 'error', "
                      b"'critical']\n")
    assert stderr == b''
