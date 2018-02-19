import os

import pytest

from dcoscli.test.common import exec_command, update_config


@pytest.fixture
def env():
    return os.environ.copy()


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


def _ssl_error_msg():
    return (
        "An SSL error occurred. To configure your SSL settings, please run: "
        "`dcos config set core.ssl_verify <value>`\n"
        "<value>: Whether to verify SSL certs for HTTPS or path to certs. "
        "Valid values are a path to a CA_BUNDLE, "
        "True (will then use CA Certificates from certifi), "
        "or False (will then send insecure requests).\n")
