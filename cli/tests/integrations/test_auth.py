import os

from dcos import constants

import pytest

from .common import assert_command, config_set, exec_command


@pytest.fixture
def env():
    r = os.environ.copy()
    r.update({
        constants.PATH_ENV: os.environ[constants.PATH_ENV],
        constants.DCOS_CONFIG_ENV: os.path.join("tests", "data", "dcos.toml"),
    })

    return r


def test_info():
    stdout = b'Authenticate to DCOS cluster\n'
    assert_command(['dcos', 'auth', '--info'],
                   stdout=stdout)


def test_version():
    stdout = b'dcos-auth version SNAPSHOT\n'
    assert_command(['dcos', 'auth', '--version'],
                   stdout=stdout)


def test_logout_no_token(env):
    exec_command(['dcos', 'config', 'unset', 'core.dcos_acs_token'], env=env)

    returncode, _, stderr = exec_command(
        ['dcos', 'config', 'show', 'core.dcos_acs_token'], env=env)
    assert returncode == 1
    assert stderr == b"Property 'core.dcos_acs_token' doesn't exist\n"


def test_logout_with_token(env):
    config_set('core.dcos_acs_token', "foobar", env=env)
    stderr = b"[core.dcos_acs_token]: changed\n"
    assert_command(
        ['dcos', 'config', 'set', 'core.dcos_acs_token', 'faketoken'],
        stderr=stderr,
        env=env)

    stderr = b'Removed [core.dcos_acs_token]\n'
    assert_command(['dcos', 'auth', 'logout'],
                   stderr=stderr,
                   env=env)
