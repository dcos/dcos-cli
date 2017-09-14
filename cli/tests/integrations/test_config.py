import json
import os

import pytest
import six

from dcos import config, constants

from .helpers.common import (assert_command, config_set, exec_command,
                             update_config)


@pytest.fixture
def env():
    r = os.environ.copy()
    r.update({constants.PATH_ENV: os.environ[constants.PATH_ENV]})

    return r


def test_info():
    stdout = b'Manage the DC/OS configuration file\n'
    assert_command(['dcos', 'config', '--info'],
                   stdout=stdout)


def test_version():
    stdout = b'dcos-config version SNAPSHOT\n'
    assert_command(['dcos', 'config', '--version'],
                   stdout=stdout)


def test_get_existing_boolean_property(env):
    with update_config("core.reporting", "false", env):
        _get_value('core.reporting', False, env)


def test_get_existing_number_property(env):
    with update_config("core.timeout", "5", env):
        _get_value('core.timeout', 5, env)


def test_get_missing_property(env):
    _get_missing_value('missing.property', env)


def test_get_top_property(env):
    returncode, stdout, stderr = exec_command(
        ['dcos', 'config', 'show', 'core'], env=env)

    assert returncode == 1
    assert stdout == b''
    assert stderr.startswith(
        b"Property 'core' doesn't fully specify a value - "
        b"possible properties are:\n")


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
        ['dcos', 'config', 'set', 'core.timeout', '10'],
        stderr=b"[core.timeout]: changed from '5' to '10'\n",
        env=env)
    config_set('core.timeout', '5', env)


def test_set_same_output(env):
    assert_command(
        ['dcos', 'config', 'set', 'core.timeout', '5'],
        stderr=b"[core.timeout]: already set to '5'\n",
        env=env)


def test_set_nonexistent_subcommand(env):
    assert_command(
        ['dcos', 'config', 'set', 'foo.bar', 'baz'],
        stdout=b'',
        stderr=(b"Config section 'foo' is invalid:"
                b" 'foo' is not a dcos command.\n"),
        returncode=1,
        env=env)


def test_set_nonconfigurable_subcommand(env):
    assert_command(
        ['dcos', 'config', 'set', 'help.bar', 'baz'],
        stdout=b'',
        stderr=(b"Subcommand 'help' is not configurable.\n"),
        returncode=1,
        env=env)


def test_unset_property(env):
    with update_config("core.reporting", None, env):
        _get_missing_value('core.reporting', env)


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
    stdout = 'Validating %s ...\n' % config.get_config_path() + \
             'Congratulations, your configuration is valid!\n'
    stdout = stdout.encode('utf-8')
    assert_command(['dcos', 'config', 'validate'],
                   env=env, stdout=stdout)


def test_set_property_key(env):
    assert_command(
        ['dcos', 'config', 'set', 'path.to.value', 'cool new value'],
        returncode=1,
        stderr=(b"Config section 'path' is invalid:"
                b" 'path' is not a dcos command.\n"),
        env=env)


def test_set_missing_property(env):
    with update_config("package.cosmos_url", None, env=env):
        config_set('package.cosmos_url', 'http://localhost:8080', env)
        _get_value('package.cosmos_url', 'http://localhost:8080', env)


def test_set_core_property(env):
    config_set('core.reporting', 'true', env)
    _get_value('core.reporting', True, env)
    config_set('core.reporting', 'false', env)


def test_url_validation(env):
    key = 'package.cosmos_url'
    with update_config(key, None, env):

        config_set(key, 'http://localhost', env)
        config_set(key, 'https://localhost', env)
        config_set(key, 'http://dcos-1234', env)
        config_set(key, 'http://dcos-1234.mydomain.com', env)

        config_set(key, 'http://localhost:5050', env)
        config_set(key, 'https://localhost:5050', env)
        config_set(key, 'http://mesos-1234:5050', env)
        config_set(key, 'http://mesos-1234.mydomain.com:5050', env)

        config_set(key, 'http://localhost:8080', env)
        config_set(key, 'https://localhost:8080', env)
        config_set(key, 'http://marathon-1234:8080', env)
        config_set(key, 'http://marathon-1234.mydomain.com:5050', env)

        config_set(key, 'http://user@localhost:8080', env)
        config_set(key, 'http://u-ser@localhost:8080', env)
        config_set(key, 'http://user123_@localhost:8080', env)
        config_set(key, 'http://user:p-ssw_rd@localhost:8080', env)
        config_set(key, 'http://user123:password321@localhost:8080', env)
        config_set(key, 'http://us%r1$3:pa#sw*rd321@localhost:8080', env)


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


def _fail_url_validation(command, key, value, env):
    returncode_, stdout_, stderr_ = exec_command(
        ['dcos', 'config', command, key, value], env=env)

    assert returncode_ == 1
    assert stdout_ == b''
    err = str('Unable to parse {!r} as a url'.format(value)).encode('utf-8')
    assert err in stderr_


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
