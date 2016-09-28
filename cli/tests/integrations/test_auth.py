import os

import pytest

from dcos import constants

from .common import assert_command, exec_command, update_config


@pytest.fixture
def env():
    r = os.environ.copy()
    r.update({
        constants.PATH_ENV: os.environ[constants.PATH_ENV],
        constants.DCOS_CONFIG_ENV: os.path.join("tests", "data", "dcos.toml"),
    })

    return r


def test_info():
    stdout = b'Authenticate to DC/OS cluster\n'
    assert_command(['dcos', 'auth', '--info'],
                   stdout=stdout)


def test_version():
    stdout = b'dcos-auth version SNAPSHOT\n'
    assert_command(['dcos', 'auth', '--version'],
                   stdout=stdout)


def test_logout_no_token(env):
    with update_config("core.dcos_acs_token", None, env):
        returncode, _, stderr = exec_command(
            ['dcos', 'config', 'show', 'core.dcos_acs_token'], env=env)
        assert returncode == 1
        assert stderr == b"Property 'core.dcos_acs_token' doesn't exist\n"


def test_logout_with_token(env):
    with update_config("core.dcos_acs_token", "foobar", env):
        stderr = b"[core.dcos_acs_token]: changed\n"
        assert_command(
            ['dcos', 'config', 'set', 'core.dcos_acs_token', 'faketoken'],
            stderr=stderr,
            env=env)

        assert_command(['dcos', 'auth', 'logout'],
                       env=env)
