import json
import os

import pytest
import six

from dcos import constants

from .common import (assert_command, config_set, config_unset,
                     exec_command, update_config)


@pytest.fixture
def env():
    r = os.environ.copy()
    r.update({
        constants.PATH_ENV: os.environ[constants.PATH_ENV],
        constants.DCOS_CONFIG_ENV: os.path.join("tests", "data", "dcos.toml"),
    })

    return r


def test_help():
    with open('tests/data/help/config.txt') as content:
        assert_command(['dcos', 'config', '--help'],
                       stdout=content.read().encode('utf-8'))


def test_info():
    stdout = b'Manage the DC/OS configuration file\n'
    assert_command(['dcos', 'config', '--info'],
                   stdout=stdout)


def test_version():
    stdout = b'dcos-config version SNAPSHOT\n'
    assert_command(['dcos', 'config', '--version'],
                   stdout=stdout)


def _test_list_property(env):
    stdout = b"""core.dcos_url http://dcos.snakeoil.mesosphere.com
core.reporting False
core.ssl_verify false
core.timeout 5
"""
    assert_command(['dcos', 'config', 'show'],
                   stdout=stdout,
                   env=env)


def test_get_existing_string_property(env):
    _get_value('core.dcos_url', 'http://dcos.snakeoil.mesosphere.com', env)


def test_get_existing_boolean_property(env):
    _get_value('core.reporting', False, env)


def test_get_existing_number_property(env):
    _get_value('core.timeout', 5, env)


def test_get_missing_property(env):
    _get_missing_value('missing.property', env)


def test_invalid_dcos_url(env):
    stderr = b'Please check url \'abc.com\'. Missing http(s)://\n'
    assert_command(['dcos', 'config', 'set', 'core.dcos_url', 'abc.com'],
                   stderr=stderr,
                   returncode=1,
                   env=env)


def test_get_top_property(env):
    returncode, stdout, stderr = exec_command(
        ['dcos', 'config', 'show', 'core'], env=env)

    assert returncode == 1
    assert stdout == b''
    assert stderr.startswith(
        b"Property 'core' doesn't fully specify a value - "
        b"possible properties are:\n")


def test_set_package_sources_property():
    notice = (b"This config property has been deprecated. "
              b"Please add your repositories with `dcos package repo add`\n")
    assert_command(['dcos', 'config', 'set', 'package.sources', '[\"foo\"]'],
                   stderr=notice,
                   returncode=1)


def test_set_core_email_property():
    notice = (b"This config property has been deprecated.\n")
    assert_command(['dcos', 'config', 'set', 'core.email', 'foo@bar.com'],
                   stderr=notice,
                   returncode=1)


def test_set_existing_string_property(env):
    config_set('core.dcos_url',
               'http://dcos.snakeoil.mesosphere.com:5081', env)
    _get_value('core.dcos_url',
               'http://dcos.snakeoil.mesosphere.com:5081', env)
    config_set('core.dcos_url', 'http://dcos.snakeoil.mesosphere.com', env)


def test_set_existing_boolean_property(env):
    config_set('core.reporting', 'true', env)
    _get_value('core.reporting', True, env)
    config_set('core.reporting', 'true', env)


def test_set_existing_number_property(env):
    config_set('core.timeout', '5', env)
    _get_value('core.timeout', 5, env)
    config_set('core.timeout', '5', env)


def test_set_change_output(env):
    assert_command(
        ['dcos', 'config', 'set', 'core.dcos_url',
         'http://dcos.snakeoil.mesosphere.com:5081'],
        stderr=(b"[core.dcos_url]: changed from "
                b"'http://dcos.snakeoil.mesosphere.com' to "
                b"'http://dcos.snakeoil.mesosphere.com:5081'\n"),
        env=env)
    config_set('core.dcos_url', 'http://dcos.snakeoil.mesosphere.com', env)


def test_set_same_output(env):
    assert_command(
        ['dcos', 'config', 'set', 'core.dcos_url',
            'http://dcos.snakeoil.mesosphere.com'],
        stderr=(b"[core.dcos_url]: already set to "
                b"'http://dcos.snakeoil.mesosphere.com'\n"),
        env=env)


def test_set_new_output(env):
    config_unset('core.dcos_url', env)
    assert_command(
        ['dcos', 'config', 'set', 'core.dcos_url',
         'http://dcos.snakeoil.mesosphere.com:5081'],
        stderr=(b"[core.dcos_url]: set to "
                b"'http://dcos.snakeoil.mesosphere.com:5081'\n"),
        env=env)
    config_set('core.dcos_url', 'http://dcos.snakeoil.mesosphere.com', env)


def test_set_nonexistent_subcommand(env):
    assert_command(
        ['dcos', 'config', 'set', 'foo.bar', 'baz'],
        stdout=b'',
        stderr=b"'foo' is not a dcos command.\n",
        returncode=1,
        env=env)


def test_set_when_extra_section():
    env = os.environ.copy()
    path = os.path.join('tests', 'data', 'config', 'invalid_section.toml')
    env['DCOS_CONFIG'] = path
    os.chmod(path, 0o600)

    config_set('core.dcos_url', 'http://dcos.snakeoil.mesosphere.com', env)
    config_unset('core.dcos_url', env)


def test_unset_property(env):
    config_unset('core.reporting', env)
    _get_missing_value('core.reporting', env)
    config_set('core.reporting', 'false', env)


def test_unset_missing_property(env):
    assert_command(
        ['dcos', 'config', 'unset', 'missing.property'],
        returncode=1,
        stderr=b"Property 'missing.property' doesn't exist\n",
        env=env)


def test_unset_output(env):
    assert_command(['dcos', 'config', 'unset', 'core.reporting'],
                   stderr=b'Removed [core.reporting]\n',
                   env=env)
    config_set('core.reporting', 'false', env)


def test_unset_top_property(env):
    returncode, stdout, stderr = exec_command(
        ['dcos', 'config', 'unset', 'core'], env=env)

    assert returncode == 1
    assert stdout == b''
    assert stderr.startswith(
        b"Property 'core' doesn't fully specify a value - "
        b"possible properties are:\n")


def test_validate(env):
    stdout = b'Congratulations, your configuration is valid!\n'
    assert_command(['dcos', 'config', 'validate'],
                   env=env, stdout=stdout)


def test_set_property_key(env):
    assert_command(
        ['dcos', 'config', 'set', 'path.to.value', 'cool new value'],
        returncode=1,
        stderr=b"'path' is not a dcos command.\n",
        env=env)


def test_set_missing_property(env):
    with update_config("core.dcos_url", None, env=env):
        config_set('core.dcos_url', 'http://localhost:8080', env)
        _get_value('core.dcos_url', 'http://localhost:8080', env)


def test_set_core_property(env):
    config_set('core.reporting', 'true', env)
    _get_value('core.reporting', True, env)
    config_set('core.reporting', 'false', env)


def test_url_validation(env):
    key = 'core.dcos_url'
    default_value = 'http://dcos.snakeoil.mesosphere.com'

    key2 = 'package.cosmos_url'

    config_set(key, 'http://localhost', env)
    config_set(key, 'https://localhost', env)
    config_set(key, 'http://dcos-1234', env)
    config_set(key2, 'http://dcos-1234.mydomain.com', env)

    config_set(key, 'http://localhost:5050', env)
    config_set(key, 'https://localhost:5050', env)
    config_set(key, 'http://mesos-1234:5050', env)
    config_set(key2, 'http://mesos-1234.mydomain.com:5050', env)

    config_set(key, 'http://localhost:8080', env)
    config_set(key, 'https://localhost:8080', env)
    config_set(key, 'http://marathon-1234:8080', env)
    config_set(key2, 'http://marathon-1234.mydomain.com:5050', env)

    config_set(key, 'http://user@localhost:8080', env)
    config_set(key, 'http://u-ser@localhost:8080', env)
    config_set(key, 'http://user123_@localhost:8080', env)
    config_set(key, 'http://user:p-ssw_rd@localhost:8080', env)
    config_set(key, 'http://user123:password321@localhost:8080', env)
    config_set(key2, 'http://us%r1$3:pa#sw*rd321@localhost:8080', env)

    config_set(key, default_value, env)
    config_unset(key2, env)


def test_fail_url_validation(env):
    _fail_url_validation('set', 'core.dcos_url', 'http://bad_domain/', env)
    _fail_url_validation('set', 'core.dcos_url', 'http://@domain/', env)
    _fail_url_validation('set', 'core.dcos_url', 'http://user:pass@/', env)
    _fail_url_validation('set', 'core.dcos_url', 'http://us:r:pass@url', env)


def test_bad_port_fail_url_validation(env):
    _fail_url_validation('set', 'core.dcos_url',
                         'http://localhost:bad_port/', env)


def test_dcos_url_env_var(env):
    env['DCOS_URL'] = 'http://foobar'

    returncode, stdout, stderr = exec_command(
        ['dcos', 'service'], env=env)
    assert returncode == 1
    assert stdout == b''
    assert stderr.startswith(
        b'URL [http://foobar/mesos/master/state.json] is unreachable')

    env.pop('DCOS_URL')


def test_dcos_dcos_url_env_var(env):
    env['DCOS_DCOS_URL'] = 'http://foobar'

    returncode, stdout, stderr = exec_command(
        ['dcos', 'service'], env=env)
    assert returncode == 1
    assert stdout == b''
    assert stderr.startswith(
        b'URL [http://foobar/mesos/master/state.json] is unreachable')

    env.pop('DCOS_DCOS_URL')


@pytest.mark.skipif(
    True, reason='Network tests are unreliable')
def test_timeout(env):
    with update_config('marathon.url', 'http://1.2.3.4', env):
        with update_config('core.timeout', '1', env):
            returncode, stdout, stderr = exec_command(
                ['dcos', 'marathon', 'app', 'list'], env=env)

            assert returncode == 1
            assert stdout == b''
            assert "(connect timeout=1)".encode('utf-8') in stderr


def test_parse_error():
    env = os.environ.copy()
    path = os.path.join('tests', 'data', 'config', 'parse_error.toml')
    os.chmod(path, 0o600)
    env['DCOS_CONFIG'] = path

    assert_command(['dcos', 'config', 'show'],
                   returncode=1,
                   stderr=six.b(("Error parsing config file at [{}]: Found "
                                 "invalid character in key name: ']'. "
                                 "Try quoting the key name.\n").format(path)),
                   env=env)


def _fail_url_validation(command, key, value, env):
    returncode_, stdout_, stderr_ = exec_command(
        ['dcos', 'config', command, key, value], env=env)

    assert returncode_ == 1
    assert stdout_ == b''
    assert stderr_.startswith(str(
        'Unable to parse {!r} as a url'.format(value)).encode('utf-8'))


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


def _get_missing_value(key, env):
    returncode, stdout, stderr = exec_command(
        ['dcos', 'config', 'show', key],
        env)

    assert returncode == 1
    assert stdout == b''
    assert (stderr.decode('utf-8') ==
            "Property {!r} doesn't exist\n".format(key))
