import os

from common import exec_command
from dcos.api import util


def test_help():
    returncode, stdout, stderr = exec_command(['dcos', '--help'])

    assert returncode == 0
    assert stdout == b"""Usage:
    dcos <command> [<args>...]

Options:
    -h, --help           Show this screen
    --version            Show version

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
