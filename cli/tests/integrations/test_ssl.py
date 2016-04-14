import os

from dcos import constants

import pytest

from .common import config_set, exec_command, update_config


@pytest.fixture
def env():
    r = os.environ.copy()
    r.update({
        constants.PATH_ENV: os.environ[constants.PATH_ENV],
        constants.DCOS_CONFIG_ENV: os.path.join("tests", "data", "dcos.toml"),
    })

    return r


@pytest.yield_fixture(autouse=True)
def setup_env(env):
    config_set("core.dcos_url", "https://dcos.snakeoil.mesosphere.com", env)
    try:
        yield
    finally:
        config_set("core.dcos_url", "http://dcos.snakeoil.mesosphere.com", env)


def test_dont_verify_ssl_with_env_var(env):
    env[constants.DCOS_SSL_VERIFY_ENV] = 'false'

    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'app', 'list'], env)
    assert returncode == 0
    assert stderr == b''

    env.pop(constants.DCOS_SSL_VERIFY_ENV)


def test_dont_verify_ssl_with_config(env):
    with update_config('core.ssl_verify', 'false', env):
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'app', 'list'], env)
        assert returncode == 0
        assert stderr == b''


def test_verify_ssl_without_cert_env_var(env):
    env[constants.DCOS_SSL_VERIFY_ENV] = 'true'
    with update_config('core.ssl_verify', None, env):
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'app', 'list'], env)
        assert returncode == 1
        assert "certificate verify failed" in stderr.decode('utf-8')

    env.pop(constants.DCOS_SSL_VERIFY_ENV)


def test_verify_ssl_without_cert_config(env):
    with update_config('core.ssl_verify', 'true', env):
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'app', 'list'], env)
        assert returncode == 1
        assert "certificate verify failed" in stderr.decode('utf-8')


def test_verify_ssl_with_bad_cert_env_var(env):
    env[constants.DCOS_SSL_VERIFY_ENV] = 'tests/data/ssl/fake.pem'

    with update_config('core.ssl_verify', None, env):
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'app', 'list'], env)
        assert returncode == 1
        assert "PEM lib" in stderr.decode('utf-8')  # wrong private key

    env.pop(constants.DCOS_SSL_VERIFY_ENV)


def test_verify_ssl_with_bad_cert_config(env):
    with update_config('core.ssl_verify', 'tests/data/ssl/fake.pem', env):
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'app', 'list'], env)
        assert returncode == 1
        assert "PEM lib" in stderr.decode('utf-8')  # wrong private key


def test_verify_ssl_with_good_cert_env_var(env):
    env[constants.DCOS_SSL_VERIFY_ENV] = '/dcos-cli/adminrouter/snakeoil.crt'

    with update_config('core.ssl_verify', None, env):
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'app', 'list'], env)
        assert returncode == 0
        assert stderr == b''

    env.pop(constants.DCOS_SSL_VERIFY_ENV)


def test_verify_ssl_with_good_cert_config(env):
    with update_config(
            'core.ssl_verify', '/dcos-cli/adminrouter/snakeoil.crt', env):
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'app', 'list'], env)
        assert returncode == 0
        assert stderr == b''
