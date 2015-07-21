import json
import os

import dcoscli.constants as cli_constants
import six
from dcos import constants

import pytest

from .common import assert_command, exec_command


@pytest.fixture
def env():
    r = os.environ.copy()
    r.update({
        constants.PATH_ENV: os.environ[constants.PATH_ENV],
        constants.DCOS_CONFIG_ENV: os.path.join("tests", "data", "dcos.toml"),
        cli_constants.DCOS_PRODUCTION_ENV: 'false'
    })
    return r


@pytest.fixture
def missing_env():
    r = os.environ.copy()
    r.update({
        constants.PATH_ENV: os.environ[constants.PATH_ENV],
        constants.DCOS_CONFIG_ENV:
            os.path.join("tests", "data", "missing_params_dcos.toml")
    })
    return r


def test_help():
    stdout = b"""Get and set DCOS CLI configuration properties

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
    assert_command(['dcos', 'config', '--help'],
                   stdout=stdout)


def test_info():
    stdout = b'Get and set DCOS CLI configuration properties\n'
    assert_command(['dcos', 'config', '--info'],
                   stdout=stdout)


def test_version():
    stdout = b'dcos-config version SNAPSHOT\n'
    assert_command(['dcos', 'config', '--version'],
                   stdout=stdout)


def test_list_property(env):
    stdout = b"""core.dcos_url=http://change.dcos.url
core.email=test@mail.com
core.reporting=False
core.timeout=5
package.cache=tmp/cache
package.sources=['https://github.com/mesosphere/universe/archive/\
version-1.x.zip']
"""
    assert_command(['dcos', 'config', 'show'],
                   stdout=stdout,
                   env=env)


def test_get_existing_string_property(env):
    _get_value('core.dcos_url', 'http://change.dcos.url', env)


def test_get_existing_boolean_property(env):
    _get_value('core.reporting', False, env)


def test_get_existing_number_property(env):
    _get_value('core.timeout', 5, env)


def test_get_missing_property(env):
    _get_missing_value('missing.property', env)


def test_get_top_property(env):
    stderr = (
        b"Property 'package' doesn't fully specify a value - "
        b"possible properties are:\n"
        b"package.cache\n"
        b"package.sources\n"
    )

    assert_command(['dcos', 'config', 'show', 'package'],
                   stderr=stderr,
                   returncode=1)


def test_set_existing_string_property(env):
    _set_value('core.dcos_url', 'http://change.dcos.url:5081', env)
    _get_value('core.dcos_url', 'http://change.dcos.url:5081', env)
    _set_value('core.dcos_url', 'http://change.dcos.url', env)


def test_set_existing_boolean_property(env):
    _set_value('core.reporting', 'true', env)
    _get_value('core.reporting', True, env)
    _set_value('core.reporting', 'true', env)


def test_set_existing_number_property(env):
    _set_value('core.timeout', '5', env)
    _get_value('core.timeout', 5, env)
    _set_value('core.timeout', '5', env)


def test_append_empty_list(env):
    _set_value('package.sources', '[]', env)
    _append_value(
        'package.sources',
        'https://github.com/mesosphere/universe/archive/version-1.x.zip',
        env)
    _get_value(
        'package.sources',
        ['https://github.com/mesosphere/universe/archive/version-1.x.zip'],
        env)


def test_prepend_empty_list(env):
    _set_value('package.sources', '[]', env)
    _prepend_value(
        'package.sources',
        'https://github.com/mesosphere/universe/archive/version-1.x.zip',
        env)
    _get_value(
        'package.sources',
        ['https://github.com/mesosphere/universe/archive/version-1.x.zip'],
        env)


def test_append_list(env):
    _append_value(
        'package.sources',
        'https://github.com/mesosphere/universe/archive/version-2.x.zip',
        env)
    _get_value(
        'package.sources',
        ['https://github.com/mesosphere/universe/archive/version-1.x.zip',
         'https://github.com/mesosphere/universe/archive/version-2.x.zip'],
        env)
    _unset_value('package.sources', '1', env)


def test_prepend_list(env):
    _prepend_value(
        'package.sources',
        'https://github.com/mesosphere/universe/archive/version-2.x.zip',
        env)
    _get_value(
        'package.sources',
        ['https://github.com/mesosphere/universe/archive/version-2.x.zip',
         'https://github.com/mesosphere/universe/archive/version-1.x.zip'],
        env)
    _unset_value('package.sources', '0', env)


def test_append_non_list(env):
    stderr = (b"Append/Prepend not supported on 'core.dcos_url' "
              b"properties - use 'dcos config set core.dcos_url new_uri'\n")

    assert_command(
        ['dcos', 'config', 'append', 'core.dcos_url', 'new_uri'],
        returncode=1,
        stderr=stderr,
        env=env)


def test_prepend_non_list(env):
    stderr = (b"Append/Prepend not supported on 'core.dcos_url' "
              b"properties - use 'dcos config set core.dcos_url new_uri'\n")

    assert_command(
        ['dcos', 'config', 'prepend', 'core.dcos_url', 'new_uri'],
        returncode=1,
        stderr=stderr,
        env=env)


def test_unset_property(env):
    _unset_value('core.reporting', None, env)
    _get_missing_value('core.reporting', env)
    _set_value('core.reporting', 'false', env)


def test_unset_missing_property(env):
    assert_command(
        ['dcos', 'config', 'unset', 'missing.property'],
        returncode=1,
        stderr=b"Property 'missing.property' doesn't exist\n",
        env=env)


def test_set_whole_list(env):
    _set_value(
        'package.sources',
        '["https://github.com/mesosphere/universe/archive/version-1.x.zip"]',
        env)


def test_unset_top_property(env):
    stderr = (
        b"Property 'package' doesn't fully specify a value - "
        b"possible properties are:\n"
        b"package.cache\n"
        b"package.sources\n"
    )

    assert_command(
        ['dcos', 'config', 'unset', 'package'],
        returncode=1,
        stderr=stderr,
        env=env)


def test_unset_list_index(env):
    _unset_value('package.sources', '0', env)
    _get_value(
        'package.sources',
        [],
        env)
    _prepend_value(
        'package.sources',
        'https://github.com/mesosphere/universe/archive/version-1.x.zip',
        env)


def test_unset_outbound_index(env):
    stderr = (
        b'Index (3) is out of bounds - possible values are '
        b'between 0 and 0\n'
    )

    assert_command(
        ['dcos', 'config', 'unset', '--index=3', 'package.sources'],
        returncode=1,
        stderr=stderr,
        env=env)


def test_unset_bad_index(env):
    stderr = b'Error parsing string as int\n'

    assert_command(
        ['dcos', 'config', 'unset', '--index=number', 'package.sources'],
        returncode=1,
        stderr=stderr,
        env=env)


def test_unset_index_from_string(env):
    stderr = b'Unsetting based on an index is only supported for lists\n'

    assert_command(
        ['dcos', 'config', 'unset', '--index=0', 'core.dcos_url'],
        returncode=1,
        stderr=stderr,
        env=env)


def test_validate(env):
    stdout = b'Congratulations, your configuration is valid!\n'
    assert_command(['dcos', 'config', 'validate'],
                   env=env, stdout=stdout)


def test_validation_error(env):
    source = ["https://github.com/mesosphere/universe/archive/version-1.x.zip"]
    assert_command(['dcos', 'config', 'unset', 'package.sources'], env=env)

    stdout = b"Error: missing required property 'sources'.\n"
    assert_command(['dcos', 'config', 'validate'],
                   returncode=1,
                   stdout=stdout,
                   env=env)

    assert_command(['dcos', 'config', 'set', 'package.sources',
                   json.dumps(source)],
                   env=env)
    _get_value(
        'package.sources',
        source,
        env)


def test_set_property_key(env):
    assert_command(
        ['dcos', 'config', 'set', 'path.to.value', 'cool new value'],
        returncode=1,
        stderr=b"'path' is not a dcos command.\n",
        env=env)


def test_set_missing_property(missing_env):
    _set_value('core.dcos_url', 'http://localhost:8080', missing_env)
    _get_value('core.dcos_url', 'http://localhost:8080', missing_env)
    _unset_value('core.dcos_url', None, missing_env)


def test_set_core_property(env):
    _set_value('core.reporting', 'true', env)
    _get_value('core.reporting', True, env)
    _set_value('core.reporting', 'false', env)


def test_url_validation(env):
    key = 'core.dcos_url'
    default_value = 'http://change.dcos.url'

    _set_value(key, 'http://localhost', env)
    _set_value(key, 'https://localhost', env)
    _set_value(key, 'http://dcos-1234', env)
    _set_value(key, 'http://dcos-1234.mydomain.com', env)

    _set_value(key, 'http://localhost:5050', env)
    _set_value(key, 'https://localhost:5050', env)
    _set_value(key, 'http://mesos-1234:5050', env)
    _set_value(key, 'http://mesos-1234.mydomain.com:5050', env)

    _set_value(key, 'http://localhost:8080', env)
    _set_value(key, 'https://localhost:8080', env)
    _set_value(key, 'http://marathon-1234:8080', env)
    _set_value(key, 'http://marathon-1234.mydomain.com:5050', env)

    _set_value(key, default_value, env)


def test_append_url_validation(env):
    default_value = ('["https://github.com/mesosphere/universe/archive/'
                     'version-1.x.zip"]')

    _set_value('package.sources', '[]', env)
    _append_value(
        'package.sources',
        'https://github.com/mesosphere/universe/archive/version-1.x.zip',
        env)
    _append_value(
        'package.sources',
        'git@github.com:mesosphere/test.git',
        env)
    _append_value(
        'package.sources',
        'https://github.com/mesosphere/test.git',
        env)
    _append_value(
        'package.sources',
        'file://some-domain.com/path/to/file.extension',
        env)
    _append_value(
        'package.sources',
        'file:///path/to/file.extension',
        env)
    _set_value('package.sources', default_value, env)


def test_prepend_url_validation(env):
    default_value = ('["https://github.com/mesosphere/universe/archive/'
                     'version-1.x.zip"]')

    _set_value('package.sources', '[]', env)
    _prepend_value(
        'package.sources',
        'https://github.com/mesosphere/universe/archive/version-1.x.zip',
        env)
    _prepend_value(
        'package.sources',
        'git@github.com:mesosphere/test.git',
        env)
    _prepend_value(
        'package.sources',
        'https://github.com/mesosphere/test.git',
        env)
    _prepend_value(
        'package.sources',
        'file://some-domain.com/path/to/file.extension',
        env)
    _prepend_value(
        'package.sources',
        'file:///path/to/file.extension',
        env)
    _set_value('package.sources', default_value, env)


def test_fail_url_validation(env):
    _fail_url_validation('set', 'core.dcos_url', 'http://bad_domain/', env)


def test_bad_port_fail_url_validation(env):
    _fail_url_validation('set', 'core.dcos_url',
                         'http://localhost:bad_port/', env)


def test_append_fail_url_validation(env):
    _fail_url_validation('append', 'package.sources', 'bad_url', env)


def test_prepend_fail_url_validation(env):
    _fail_url_validation('prepend', 'package.sources', 'bad_url', env)


def test_timeout(missing_env):
    _set_value('marathon.url', 'http://1.2.3.4', missing_env)
    _set_value('core.timeout', '1', missing_env)

    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'app', 'list'], env=missing_env)

    assert returncode == 1
    assert stdout == b''
    assert "(connect timeout=1)".encode('utf-8') in stderr

    _unset_value('core.timeout', None, missing_env)
    _unset_value('marathon.url', None, missing_env)


def _fail_url_validation(command, key, value, env):
    returncode_, stdout_, stderr_ = exec_command(
        ['dcos', 'config', command, key, value], env=env)

    assert returncode_ == 1
    assert stdout_ == b''
    assert stderr_.startswith(str(
        'Error: {!r} does not match'.format(value)).encode('utf-8'))


def _set_value(key, value, env):
    assert_command(
        ['dcos', 'config', 'set', key, value],
        env=env)


def _append_value(key, value, env):
    assert_command(
        ['dcos', 'config', 'append', key, value],
        env=env)


def _prepend_value(key, value, env):
    assert_command(
        ['dcos', 'config', 'prepend', key, value],
        env=env)


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

    assert_command(cmd, env=env)


def _get_missing_value(key, env):
    returncode, stdout, stderr = exec_command(
        ['dcos', 'config', 'show', key],
        env)

    assert returncode == 1
    assert stdout == b''
    assert (stderr.decode('utf-8') ==
            "Property {!r} doesn't exist\n".format(key))
