import json
import os

import pytest
from common import exec_command


@pytest.fixture
def package():
    return os.environ['DCOS_TEST_WHEEL']


def test_help():
    returncode, stdout, stderr = exec_command(['dcos', 'subcommand', '--help'])

    assert returncode == 0
    assert stdout == b"""Install and manage DCOS CLI subcommands

Usage:
    dcos subcommand --config-schema
    dcos subcommand --info
    dcos subcommand info
    dcos subcommand install <package>
    dcos subcommand list
    dcos subcommand uninstall <package_name>

Options:
    --help     Show this screen
    --info     Show a short description of this subcommand
    --version  Show version

Positional arguments:
    <package>          The subcommand package wheel
    <package_name>     The name of the subcommand package
"""
    assert stderr == b''


def test_info():
    returncode, stdout, stderr = exec_command(['dcos', 'subcommand', '--info'])

    assert returncode == 0
    assert stdout == b'Install and manage DCOS CLI subcommands\n'
    assert stderr == b''


def test_list_empty_subcommand():
    _list_subcommands(0)


def test_install_package(package):
    _install_subcommand(package)
    _list_subcommands(1)
    _uninstall_subcommand('dcos-helloworld')


def test_install_existing_package(package):
    _install_subcommand(package)
    _install_subcommand(package)
    _list_subcommands(1)
    _uninstall_subcommand('dcos-helloworld')


def test_list_subcommand(package):
    _install_subcommand(package)
    _list_subcommands(1)
    _uninstall_subcommand('dcos-helloworld')


def test_uninstall_missing_subcommand(package):
    _uninstall_subcommand('missing-package')


def test_uninstall_helloworld(package):
    _install_subcommand(package)
    _list_subcommands(1)
    _uninstall_subcommand('dcos-helloworld')
    _list_subcommands(0)


def test_missing_wheel():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'subcommand', 'install', 'missing_file.whl'])

    assert returncode == 1
    assert stdout == b''
    assert stderr.decode('utf-8').startswith(
        'Failed to read file: No such file: ')

    _list_subcommands(0)


def _list_subcommands(size):
    returncode, stdout, stderr = exec_command(['dcos', 'subcommand', 'list'])

    result = json.loads(stdout.decode('utf-8'))

    assert returncode == 0
    assert len(result) == size
    assert stderr == b''

    return result


def _install_subcommand(package):
    returncode, stdout, stderr = exec_command(
        ['dcos', 'subcommand', 'install', package])

    assert returncode == 0
    assert stdout == b''
    assert stderr == b''


def _uninstall_subcommand(package):
    returncode, stdout, stderr = exec_command(
        ['dcos', 'subcommand', 'uninstall', package])

    assert returncode == 0
    assert stdout == b''
    assert stderr == b''
