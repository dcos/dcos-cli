import contextlib
import json
import os

import pytest

from dcos import config, constants, util

from .helpers.common import assert_command, exec_command


@pytest.fixture(scope="module")
def acs_token():
    return config.get_config().get('core.dcos_acs_token')


@pytest.fixture
def temp_dcos_dir():
    with util.tempdir() as tempdir:
        old_dcos_dir = os.environ.get(constants.DCOS_DIR_ENV)
        os.environ[constants.DCOS_DIR_ENV] = tempdir
        yield tempdir
        if old_dcos_dir is None:
            os.environ.pop(constants.DCOS_DIR_ENV)
        else:
            os.environ[constants.DCOS_DIR_ENV] = old_dcos_dir


def test_dcos_dir_env_with_acs_token(acs_token, temp_dcos_dir):
    _copy_config_to_dir('dcos.toml', temp_dcos_dir)

    config.set_val('core.dcos_acs_token', acs_token)

    returncode, stdout, _ = exec_command(['dcos', 'cluster', 'list', '--json'])
    assert returncode == 0

    cluster_list = json.loads(stdout.decode('utf-8'))
    assert len(cluster_list) == 1
    assert cluster_list[0]['url'] == "http://dcos.snakeoil.mesosphere.com"


def test_dcos_dir_env_without_acs_token(acs_token, temp_dcos_dir):
    _copy_config_to_dir('dcos.toml', temp_dcos_dir)

    stderr = (
        b"No clusters are currently configured. "
        b"To configure one, run `dcos cluster setup <dcos_url>`\n"
    )

    # Without an ACS token, the migration shouldn't occur
    assert_command(['dcos', 'cluster', 'list'], returncode=1, stderr=stderr)


def test_dcos_config_env_with_acs_token(acs_token, temp_dcos_dir):
    with _temp_dcos_config('dcos.toml', temp_dcos_dir):

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
        assert cluster_list[0]['url'] == "http://dcos.snakeoil.mesosphere.com"


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
    returncode, _, stderr = exec_command(
        ['dcos',
         'config',
         'set',
         'core.dcos_url',
         'http://dcos.snakeoil.mesosphere.com'])
    assert returncode == 0
    assert stderr == (
        b"[core.dcos_url]: set to 'http://dcos.snakeoil.mesosphere.com'\n"
        b"Setting-up a cluster through this command is being deprecated. "
        b"To setup the CLI to talk to your cluster, please run "
        b"`dcos cluster setup <dcos_url>`.\n")

    returncode, _, _ = exec_command(
        ['dcos', 'config', 'set', 'core.dcos_acs_token', acs_token])
    assert returncode == 0

    returncode, stdout, _ = exec_command(
        ['dcos', 'cluster', 'list', '--json'])
    assert returncode == 0

    cluster_list = json.loads(stdout.decode('utf-8'))
    assert len(cluster_list) == 1
    assert cluster_list[0]['url'] == "http://dcos.snakeoil.mesosphere.com"


def test_setup_cluster_through_auth_command(temp_dcos_dir):
    if 'DCOS_ADMIN_USERNAME' not in os.environ:
        pytest.skip('DCOS_ADMIN_USERNAME is not set.')

    if 'DCOS_ADMIN_PASSWORD' not in os.environ:
        pytest.skip('DCOS_ADMIN_PASSWORD is not set.')

    returncode, _, stderr = exec_command(
        ['dcos',
         'config',
         'set',
         'core.dcos_url',
         'http://dcos.snakeoil.mesosphere.com'])
    assert returncode == 0
    assert stderr == (
        b"[core.dcos_url]: set to 'http://dcos.snakeoil.mesosphere.com'\n"
        b"Setting-up a cluster through this command is being deprecated. "
        b"To setup the CLI to talk to your cluster, please run "
        b"`dcos cluster setup <dcos_url>`.\n")

    returncode, _, _ = exec_command(
        ['dcos',
         'auth',
         'login',
         '--username',
         os.environ['DCOS_ADMIN_USERNAME'],
         '--password-env=DCOS_ADMIN_PASSWORD'])
    assert returncode == 0

    returncode, stdout, _ = exec_command(
        ['dcos', 'cluster', 'list', '--json'])
    assert returncode == 0

    cluster_list = json.loads(stdout.decode('utf-8'))
    assert len(cluster_list) == 1
    assert cluster_list[0]['url'] == "http://dcos.snakeoil.mesosphere.com"


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
