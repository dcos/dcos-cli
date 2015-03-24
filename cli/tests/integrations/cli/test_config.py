import os

from dcos.api import constants

import pytest
from common import exec_command


@pytest.fixture
def env():
    return {
        constants.PATH_ENV: os.environ[constants.PATH_ENV],
        constants.DCOS_CONFIG_ENV: os.path.join("tests", "data", "Dcos.toml")
    }


def test_help():
    returncode, stdout, stderr = exec_command(['dcos', 'config', '--help'])

    assert returncode == 0
    assert stdout == b"""Get and set DCOS command line options

Usage:
    dcos config info
    dcos config set <name> <value>
    dcos config unset <name>
    dcos config show [<name>]

Options:
    -h, --help            Show this screen
    --version             Show version
"""
    assert stderr == b''


def test_info():
    returncode, stdout, stderr = exec_command(['dcos', 'config', 'info'])

    assert returncode == 0
    assert stdout == b'Get and set DCOS command line options\n'
    assert stderr == b''


def test_version():
    returncode, stdout, stderr = exec_command(['dcos', 'config', '--version'])

    assert returncode == 0
    assert stdout == b'dcos-config version 0.1.0\n'
    assert stderr == b''


def test_list_property(env):
    returncode, stdout, stderr = exec_command(
        ['dcos', 'config', 'show'],
        env)

    assert returncode == 0
    assert stdout == b"""foo.bar=True
marathon.host=localhost
marathon.port=8080
package.cache=tmp/cache
package.sources=['git://github.com/mesosphere/universe.git', \
'https://github.com/mesosphere/universe/archive/master.zip']
subcommand.pip_find_links=../dist
"""
    assert stderr == b''


def test_get_existing_string_property(env):
    _get_value('marathon.host', 'localhost', env)


def test_get_existing_integral_property(env):
    _get_value('marathon.port', 8080, env)


def test_get_existing_boolean_property(env):
    _get_value('foo.bar', True, env)


def test_get_missing_property(env):
    _get_missing_value('missing.property', env)


def test_get_top_property(env):
    returncode, stdout, stderr = exec_command(
        ['dcos', 'config', 'show', 'marathon'],
        env)

    assert returncode == 1
    assert stdout == b''
    assert stderr == (
        b"Property 'marathon' doesn't fully specify a value - "
        b"possible properties are:\n"
        b"marathon.host\n"
        b"marathon.port\n"
    )


def test_set_existing_property(env):
    _set_value('marathon.host', 'newhost', env)
    _get_value('marathon.host', 'newhost', env)
    _set_value('marathon.host', 'localhost', env)


def test_unset_property(env):
    _unset_value('marathon.host', env)
    _get_missing_value('marathon.host', env)
    _set_value('marathon.host', 'localhost', env)


def test_unset_missing_property(env):
    returncode, stdout, stderr = exec_command(
        ['dcos', 'config', 'unset', 'missing.property'],
        env)

    assert returncode == 1
    assert stdout == b''
    assert stderr == b"Property 'missing.property' doesn't exist\n"


def test_unset_top_property(env):
    returncode, stdout, stderr = exec_command(
        ['dcos', 'config', 'unset', 'marathon'],
        env)

    assert returncode == 1
    assert stdout == b''
    assert stderr == (
        b"Property 'marathon' doesn't fully specify a value - "
        b"possible properties are:\n"
        b"marathon.host\n"
        b"marathon.port\n"
    )


def test_set_missing_property(env):
    _set_value('path.to.value', 'cool new value', env)
    _get_value('path.to.value', 'cool new value', env)
    _unset_value('path.to.value', env)


def _set_value(key, value, env):
    returncode, stdout, stderr = exec_command(
        ['dcos', 'config', 'set', key, value],
        env)

    assert returncode == 0
    assert stdout == b''
    assert stderr == b''


def _get_value(key, value, env):
    returncode, stdout, stderr = exec_command(
        ['dcos', 'config', 'show', key],
        env)

    assert returncode == 0
    assert stdout == '{}\n'.format(value).encode('utf-8')
    assert stderr == b''


def _unset_value(key, env):
    returncode, stdout, stderr = exec_command(
        ['dcos', 'config', 'unset', key],
        env)

    assert returncode == 0
    assert stdout == b''
    assert stderr == b''


def _get_missing_value(key, env):
    returncode, stdout, stderr = exec_command(
        ['dcos', 'config', 'show', key],
        env)

    assert returncode == 1
    assert stdout == b''
    assert (stderr.decode('utf-8') ==
            "Property {!r} doesn't exist\n".format(key))
