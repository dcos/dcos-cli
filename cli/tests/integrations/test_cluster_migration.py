import contextlib
import json
import os

import pytest

from dcos import config, constants, util

from dcoscli.test.common import (assert_command, dcos_tempdir, exec_command,
                                 skip_if_env_missing)
from dcoscli.test.constants import (DCOS_TEST_PASS_ENV, DCOS_TEST_URL_ENV,
                                    DCOS_TEST_USER_ENV)


@pytest.fixture(scope="module")
def acs_token():
    return config.get_config().get('core.dcos_acs_token')


@pytest.fixture
def temp_dcos_dir():
    with dcos_tempdir() as tempdir:
        yield tempdir


def test_dcos_dir_env_with_acs_token(acs_token, temp_dcos_dir):
    skip_if_env_missing([DCOS_TEST_URL_ENV])

    _copy_config_to_dir('dcos.toml', temp_dcos_dir)

    config.set_val('core.dcos_url', os.environ.get(DCOS_TEST_URL_ENV))
    config.set_val('core.dcos_acs_token', acs_token)

    returncode, stdout, _ = exec_command(['dcos', 'cluster', 'list', '--json'])
    assert returncode == 0

    cluster_list = json.loads(stdout.decode('utf-8'))
    assert len(cluster_list) == 1
    assert cluster_list[0]['url'] == os.environ.get(DCOS_TEST_URL_ENV)


def test_dcos_dir_env_without_acs_token(acs_token, temp_dcos_dir):
    _copy_config_to_dir('dcos.toml', temp_dcos_dir)

    stderr = (
        b"No clusters are currently configured. "
        b"To configure one, run `dcos cluster setup <dcos_url>`\n"
    )

    # Without an ACS token, the migration shouldn't occur
    assert_command(['dcos', 'cluster', 'list'], returncode=1, stderr=stderr)


def test_dcos_config_env_with_acs_token(acs_token, temp_dcos_dir):
    skip_if_env_missing([DCOS_TEST_URL_ENV])

    with _temp_dcos_config('dcos.toml', temp_dcos_dir):

        config.set_val('core.dcos_url', os.environ.get(DCOS_TEST_URL_ENV))
        config.set_val('core.dcos_acs_token', acs_token)

        exp_stderr = (
            b"DCOS_CONFIG is deprecated, please consider using "
            b"`dcos cluster setup <dcos_url>`.\n"
        )

        returncode, stdout, stderr = exec_command(
            ['dcos', 'cluster', 'list', '--json'])
        assert returncode == 0
        assert exp_stderr == stderr

        cluster_list = json.loads(stdout.decode('utf-8'))
        assert len(cluster_list) == 1
        assert cluster_list[0]['url'] == os.environ.get(DCOS_TEST_URL_ENV)


def test_dcos_config_env_without_acs_token(temp_dcos_dir):
    with _temp_dcos_config('dcos.toml', temp_dcos_dir):

        stderr = (
            b"DCOS_CONFIG is deprecated, please consider using "
            b"`dcos cluster setup <dcos_url>`.\n"
            b"No clusters are currently configured. "
            b"To configure one, run `dcos cluster setup <dcos_url>`\n"
        )

        # Without an ACS token, the migration shouldn't occur
        assert_command(
            ['dcos', 'cluster', 'list'], returncode=1, stderr=stderr)


def test_setup_cluster_through_config_commands(acs_token, temp_dcos_dir):
    skip_if_env_missing([DCOS_TEST_URL_ENV])

    returncode, _, stderr = exec_command(
        ['dcos',
         'config',
         'set',
         'core.dcos_url',
         os.environ.get(DCOS_TEST_URL_ENV)])
    assert returncode == 0
    assert stderr == (
        b"[core.dcos_url]: set to '%s'\n"
        b"Setting-up a cluster through this command is being deprecated. "
        b"To setup the CLI to talk to your cluster, please run "
        b"`dcos cluster setup <dcos_url>`.\n"
        % (bytes(os.environ.get(DCOS_TEST_URL_ENV), 'utf-8'),))

    config.set_val('core.ssl_verify', "false")

    returncode, _, _ = exec_command(
        ['dcos', 'config', 'set', 'core.dcos_acs_token', acs_token])
    assert returncode == 0

    returncode, stdout, _ = exec_command(
        ['dcos', 'cluster', 'list', '--json'])
    assert returncode == 0

    cluster_list = json.loads(stdout.decode('utf-8'))
    assert len(cluster_list) == 1
    assert cluster_list[0]['url'] == os.environ.get(DCOS_TEST_URL_ENV)


def test_setup_cluster_through_auth_command(temp_dcos_dir):
    skip_if_env_missing(
        [DCOS_TEST_URL_ENV, DCOS_TEST_USER_ENV, DCOS_TEST_PASS_ENV])

    returncode, _, stderr = exec_command(
        ['dcos',
         'config',
         'set',
         'core.dcos_url',
         os.environ.get(DCOS_TEST_URL_ENV)])
    assert returncode == 0
    assert stderr == (
        b"[core.dcos_url]: set to '%s'\n"
        b"Setting-up a cluster through this command is being deprecated. "
        b"To setup the CLI to talk to your cluster, please run "
        b"`dcos cluster setup <dcos_url>`.\n"
        % (bytes(os.environ.get(DCOS_TEST_URL_ENV), 'utf-8'),))

    config.set_val('core.ssl_verify', "false")

    returncode, _, _ = exec_command(
        ['dcos',
         'auth',
         'login',
         '--username',
         os.environ.get(DCOS_TEST_USER_ENV),
         '--password-env='+DCOS_TEST_PASS_ENV])
    assert returncode == 0

    returncode, stdout, _ = exec_command(
        ['dcos', 'cluster', 'list', '--json'])
    assert returncode == 0

    cluster_list = json.loads(stdout.decode('utf-8'))
    assert len(cluster_list) == 1
    assert cluster_list[0]['url'] == os.environ.get(DCOS_TEST_URL_ENV)


def _copy_config_to_dir(name, dst_dir):
    """
    :param name: name of the config fixture to copy.
    :type name: str
    """

    fixture_config = os.path.join(
        os.path.dirname(__file__),
        '../data/cluster_migration/{}'.format(name))

    # make sure the config has the proper permission
    os.chmod(fixture_config, 0o600)

    dst = os.path.join(dst_dir, 'dcos.toml')

    util.sh_copy(fixture_config, dst)


@contextlib.contextmanager
def _temp_dcos_config(name, dst_dir):
    old_dcos_config = os.environ.get(constants.DCOS_CONFIG_ENV)
    _copy_config_to_dir(name, dst_dir)
    tempfile = os.path.join(dst_dir, name)
    try:
        os.environ[constants.DCOS_CONFIG_ENV] = tempfile
        yield tempfile
    finally:
        if old_dcos_config is None:
            os.environ.pop(constants.DCOS_CONFIG_ENV)
        else:
            os.environ[constants.DCOS_CONFIG_ENV] = old_dcos_config
