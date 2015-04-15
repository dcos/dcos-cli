import json
import os

import six
from dcos.api import constants

import pytest
from common import exec_command


@pytest.fixture
def env():
    config_path = os.path.join("tests", "data", "config", "dcos.toml")
    return {
        constants.PATH_ENV: os.environ[constants.PATH_ENV],
        constants.DCOS_CONFIG_ENV: config_path
    }


def test_help():
    returncode, stdout, stderr = exec_command(['dcos', 'config', '--help'])

    assert returncode == 0
    assert stdout == b"""Get and set DCOS command line options

Usage:
    dcos config --info
    dcos config append <name> <value>
    dcos config prepend <name> <value>
    dcos config set <name> <value>
    dcos config show [<name>]
    dcos config unset [--index=<index>] <name>
    dcos config validate

Options:
    -h, --help       Show this screen
    --info           Show a short description of this subcommand
    --version        Show version
    --index=<index>  Index into the list. The first element in the list has an
                     index of zero

Positional Arguments:
    <name>           The name of the property
    <value>          The value of the property
"""
    assert stderr == b''


def test_info():
    returncode, stdout, stderr = exec_command(['dcos', 'config', '--info'])

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
    assert stdout == b"""marathon.host=localhost
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


def test_set_existing_string_property(env):
    _set_value('marathon.host', 'newhost', env)
    _get_value('marathon.host', 'newhost', env)
    _set_value('marathon.host', 'localhost', env)


def test_set_existing_integral_property(env):
    _set_value('marathon.port', '8181', env)
    _get_value('marathon.port', 8181, env)
    _set_value('marathon.port', '8080', env)


def test_append_empty_list(env):
    _unset_value('package.sources', None, env)
    _append_value(
        'package.sources',
        'git://github.com/mesosphere/universe.git',
        env)
    _get_value(
        'package.sources',
        ['git://github.com/mesosphere/universe.git'],
        env)
    _append_value(
        'package.sources',
        'https://github.com/mesosphere/universe/archive/master.zip',
        env)
    _get_value(
        'package.sources',
        ['git://github.com/mesosphere/universe.git',
         'https://github.com/mesosphere/universe/archive/master.zip'],
        env)


def test_prepend_empty_list(env):
    _unset_value('package.sources', None, env)
    _prepend_value(
        'package.sources',
        'https://github.com/mesosphere/universe/archive/master.zip',
        env)
    _get_value(
        'package.sources',
        ['https://github.com/mesosphere/universe/archive/master.zip'],
        env)
    _prepend_value(
        'package.sources',
        'git://github.com/mesosphere/universe.git',
        env)
    _get_value(
        'package.sources',
        ['git://github.com/mesosphere/universe.git',
         'https://github.com/mesosphere/universe/archive/master.zip'],
        env)


def test_append_list(env):
    _append_value(
        'package.sources',
        'new_uri',
        env)
    _get_value(
        'package.sources',
        ['git://github.com/mesosphere/universe.git',
         'https://github.com/mesosphere/universe/archive/master.zip',
         'new_uri'],
        env)
    _unset_value('package.sources', '2', env)


def test_prepend_list(env):
    _prepend_value(
        'package.sources',
        'new_uri',
        env)
    _get_value(
        'package.sources',
        ['new_uri',
         'git://github.com/mesosphere/universe.git',
         'https://github.com/mesosphere/universe/archive/master.zip'],
        env)
    _unset_value('package.sources', '0', env)


def test_append_non_list(env):
    returncode, stdout, stderr = exec_command(
        ['dcos', 'config', 'append', 'marathon.host', 'new_uri'],
        env)

    assert returncode == 1
    assert stdout == b''
    assert (stderr ==
            b"Append/Prepend not supported on 'marathon.host' "
            b"properties - use 'dcos config set marathon.host new_uri'\n")


def test_prepend_non_list(env):
    returncode, stdout, stderr = exec_command(
        ['dcos', 'config', 'prepend', 'marathon.host', 'new_uri'],
        env)

    assert returncode == 1
    assert stdout == b''
    assert (stderr ==
            b"Append/Prepend not supported on 'marathon.host' "
            b"properties - use 'dcos config set marathon.host new_uri'\n")


def test_unset_property(env):
    _unset_value('marathon.host', None, env)
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


def test_unset_whole_list(env):
    _unset_value('package.sources', None, env)
    _get_missing_value('package.sources', env)
    _set_value(
        'package.sources',
        '["git://github.com/mesosphere/universe.git", '
        '"https://github.com/mesosphere/universe/archive/master.zip"]',
        env)


def test_unset_list_index(env):
    _unset_value('package.sources', '0', env)
    _get_value(
        'package.sources',
        ['https://github.com/mesosphere/universe/archive/master.zip'],
        env)
    _prepend_value(
        'package.sources',
        'git://github.com/mesosphere/universe.git',
        env)


def test_unset_outbound_index(env):
    returncode, stdout, stderr = exec_command(
        ['dcos', 'config', 'unset', '--index=3', 'package.sources'],
        env)

    assert returncode == 1
    assert stdout == b''
    assert (stderr ==
            b'Index (3) is out of bounds - possible values are '
            b'between 0 and 1\n')


def test_unset_bad_index(env):
    returncode, stdout, stderr = exec_command(
        ['dcos', 'config', 'unset', '--index=number', 'package.sources'],
        env)

    assert returncode == 1
    assert stdout == b''
    assert stderr == b'Error parsing string as int\n'


def test_unset_index_from_string(env):
    returncode, stdout, stderr = exec_command(
        ['dcos', 'config', 'unset', '--index=0', 'marathon.host'],
        env)

    assert returncode == 1
    assert stdout == b''
    assert (stderr ==
            b'Unsetting based on an index is only supported for lists\n')


def test_validate(env):
    returncode, stdout, stderr = exec_command(
        ['dcos', 'config', 'validate'],
        env)

    assert returncode == 0
    assert stdout == b''
    assert stderr == b''


def test_validation_error(env):
    _unset_value('marathon.host', None, env)

    returncode, stdout, stderr = exec_command(
        ['dcos', 'config', 'validate'],
        env)

    assert returncode == 1
    assert stdout == b''
    assert stderr == b"""Error: 'host' is a required property
Path: marathon
Value: {"port": 8080}
"""

    _set_value('marathon.host', 'localhost', env)


def test_set_property_key(env):
    returncode, stdout, stderr = exec_command(
        ['dcos', 'config', 'set', 'path.to.value', 'cool new value'],
        env)

    assert returncode == 1
    assert stdout == b''
    assert stderr == b"'path' is not a dcos command.\n"


def test_set_missing_property(env):
    _unset_value('marathon.host', None, env)
    _set_value('marathon.host', 'localhost', env)
    _get_value('marathon.host', 'localhost', env)


def _set_value(key, value, env):
    returncode, stdout, stderr = exec_command(
        ['dcos', 'config', 'set', key, value],
        env)

    assert returncode == 0
    assert stdout == b''
    assert stderr == b''


def _append_value(key, value, env):
    returncode, stdout, stderr = exec_command(
        ['dcos', 'config', 'append', key, value],
        env)

    assert returncode == 0
    assert stdout == b''
    assert stderr == b''


def _prepend_value(key, value, env):
    returncode, stdout, stderr = exec_command(
        ['dcos', 'config', 'prepend', key, value],
        env)

    assert returncode == 0
    assert stdout == b''
    assert stderr == b''


def _get_value(key, value, env):
    returncode, stdout, stderr = exec_command(
        ['dcos', 'config', 'show', key],
        env)

    if isinstance(value, six.string_types):
        result = json.loads('"' + stdout.decode('utf-8').strip() + '"')
    else:
        result = json.loads(stdout.decode('utf-8').strip())

    assert returncode == 0
    assert result == value
    assert stderr == b''


def _unset_value(key, index, env):
    cmd = ['dcos', 'config', 'unset', key]
    if index is not None:
        cmd.append('--index={}'.format(index))

    returncode, stdout, stderr = exec_command(cmd, env)

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
