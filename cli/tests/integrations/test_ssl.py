import os

import dcoscli.constants as cli_constants
from dcos import constants

import pytest

from .common import config_set, config_unset, exec_command


@pytest.fixture
def env():
    r = os.environ.copy()
    r.update({
        constants.PATH_ENV: os.environ[constants.PATH_ENV],
        constants.DCOS_CONFIG_ENV: os.path.join("tests",
                                                "data", "ssl", "ssl.toml"),
        cli_constants.DCOS_PRODUCTION_ENV: 'false'
    })

    return r


def test_dont_verify_ssl_with_env_var(env):
    env[constants.DCOS_SSL_VERIFY_ENV] = 'false'

    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'app', 'list'], env)
    assert returncode == 0
    assert stderr == b''

    env.pop(constants.DCOS_SSL_VERIFY_ENV)


def test_dont_verify_ssl_with_config(env):
    config_set('core.ssl_verify', 'false', env)

    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'app', 'list'], env)
    assert returncode == 0
    assert stderr == b''

    config_unset('core.ssl_verify', None, env)


def test_verify_ssl_without_cert_env_var(env):
    env[constants.DCOS_SSL_VERIFY_ENV] = 'true'

    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'app', 'list'], env)
    assert returncode == 1
    assert "certificate verify failed" in stderr.decode('utf-8')

    env.pop(constants.DCOS_SSL_VERIFY_ENV)


def test_verify_ssl_without_cert_config(env):
    config_set('core.ssl_verify', 'true', env)

    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'app', 'list'], env)
    assert returncode == 1
    assert "certificate verify failed" in stderr.decode('utf-8')

    config_unset('core.ssl_verify', None, env)


def test_verify_ssl_with_bad_cert_env_var(env):
    env[constants.DCOS_SSL_VERIFY_ENV] = 'tests/data/ssl/fake.pem'

    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'app', 'list'], env)
    assert returncode == 1
    assert "PEM lib" in stderr.decode('utf-8')  # wrong private key

    env.pop(constants.DCOS_SSL_VERIFY_ENV)


def test_verify_ssl_with_bad_cert_config(env):
    config_set('core.ssl_verify', 'tests/data/ssl/fake.pem', env)

    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'app', 'list'], env)
    assert returncode == 1
    assert "PEM lib" in stderr.decode('utf-8')  # wrong private key

    config_unset('core.ssl_verify', None, env)


def test_verify_ssl_with_good_cert_env_var(env):
    env[constants.DCOS_SSL_VERIFY_ENV] = '/adminrouter/snakeoil.crt'

    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'app', 'list'], env)
    assert returncode == 0
    assert stderr == b''

    env.pop(constants.DCOS_SSL_VERIFY_ENV)


def test_verify_ssl_with_good_cert_config(env):
    config_set('core.ssl_verify', '/adminrouter/snakeoil.crt', env)

    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'app', 'list'], env)
    assert returncode == 0
    assert stderr == b''

    config_unset('core.ssl_verify', None, env)
