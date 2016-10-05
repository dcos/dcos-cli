import os

import pytest

from dcos import constants

from .common import config_set, exec_command, update_config


@pytest.fixture
def env():
    r = os.environ.copy()
    r.update({
        constants.PATH_ENV: os.environ[constants.PATH_ENV],
        constants.DCOS_CONFIG_ENV: os.path.join("tests", "data", "dcos.toml"),
        'DCOS_SNAKEOIL_CRT_PATH': os.environ.get(
            "DCOS_SNAKEOIL_CRT_PATH", "/dcos-cli/adminrouter/snakeoil.crt")
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
    env['DCOS_SSL_VERIFY'] = 'false'

    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'app', 'list'], env)
    assert returncode == 0
    assert stderr == b''

    env.pop('DCOS_SSL_VERIFY')


def test_dont_verify_ssl_with_config(env):
    with update_config('core.ssl_verify', 'false', env):
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'app', 'list'], env)
        assert returncode == 0
        assert stderr == b''


def test_verify_ssl_without_cert_env_var(env):
    env['DCOS_SSL_VERIFY'] = 'true'
    with update_config('core.ssl_verify', None, env):
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'app', 'list'], env)
        assert returncode == 1
        assert stderr.decode('utf-8') == _ssl_error_msg()

    env.pop('DCOS_SSL_VERIFY')


def test_verify_ssl_without_cert_config(env):
    with update_config('core.ssl_verify', 'true', env):
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'app', 'list'], env)
        assert returncode == 1
        assert stderr.decode('utf-8') == _ssl_error_msg()


def test_verify_ssl_with_bad_cert_env_var(env):
    env['DCOS_SSL_VERIFY'] = 'tests/data/ssl/fake.pem'

    with update_config('core.ssl_verify', None, env):
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'app', 'list'], env)
        assert returncode == 1
        assert stderr.decode('utf-8') == _ssl_error_msg()

    env.pop('DCOS_SSL_VERIFY')


def test_verify_ssl_with_bad_cert_config(env):
    with update_config('core.ssl_verify', 'tests/data/ssl/fake.pem', env):
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'app', 'list'], env)
        assert returncode == 1
        assert stderr.decode('utf-8') == _ssl_error_msg()


@pytest.mark.skipif(True, reason='Need to resolve DCOS-9273 to validate certs')
def test_verify_ssl_with_good_cert_env_var(env):
    env['DCOS_SSL_VERIFY'] = env['DCOS_SNAKEOIL_CRT_PATH']

    with update_config('core.ssl_verify', None, env):
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'app', 'list'], env)
        assert returncode == 0
        assert stderr == b''

    env.pop('DCOS_SSL_VERIFY')


@pytest.mark.skipif(True, reason='Need to resolve DCOS-9273 to validate certs')
def test_verify_ssl_with_good_cert_config(env):
    with update_config(
            'core.ssl_verify', env['DCOS_SNAKEOIL_CRT_PATH'], env):
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'app', 'list'], env)
        assert returncode == 0
        assert stderr == b''


def _ssl_error_msg():
    return (
        "An SSL error occurred. To configure your SSL settings, please run: "
        "`dcos config set core.ssl_verify <value>`\n"
        "<value>: Whether to verify SSL certs for HTTPS or path to certs\n")
