import contextlib
import os

import pytest
from mock import patch

from dcos import constants, mesos, util
from dcos.errors import DCOSException


def test_open_file():
    path = 'nonexistant_file_name.txt'
    with pytest.raises(DCOSException) as excinfo:
        with util.open_file(path):
            pass
    assert 'Error opening file [{}]: No such file or directory'.format(path) \
        in str(excinfo.value)


def test_get_ssh_user():
    username = 'test_user_name'
    ssh_config_file = '.ssh/special_config'
    assert util.get_ssh_user(ssh_config_file, None) is None
    assert util.get_ssh_user(ssh_config_file, username) is None
    assert util.get_ssh_user(None, username) == username
    with patch.object(util.config, 'get_config_val', return_value=username):
        assert util.get_ssh_user(None, None) == username
    with patch.object(util.config, 'get_config_val', return_value=None):
        assert util.get_ssh_user(None, None) == constants.DEFAULT_SSH_USER


def test_get_ssh_proxy_options():
    ssh_options = '-o special-ssh=options'
    proxy_ip = '1.1.1.1'
    master_public_ip = '2.2.2.2'
    config_proxy_ip = '3.3.3.3'
    master_metadata = {'PUBLIC_IPV4': master_public_ip}

    with patch.object(util.config, 'get_config_val',
                      return_value=None):
        assert util.get_ssh_proxy_options('') == ''
        assert proxy_ip in util.get_ssh_proxy_options('',
                                                      proxy_ip=proxy_ip)
        assert ssh_options in util.get_ssh_proxy_options(ssh_options,
                                                         proxy_ip=proxy_ip)
        assert proxy_ip in util.get_ssh_proxy_options('',
                                                      proxy_ip=proxy_ip,
                                                      master_proxy=True)

        with patch.object(mesos, 'DCOSClient') as dcos_client:

            dcos_client().metadata.return_value = master_metadata
            assert master_public_ip in util.get_ssh_proxy_options(
                '', master_proxy=True)

            dcos_client().metadata.return_value = {}
            with pytest.raises(DCOSException):
                util.get_ssh_proxy_options('', master_proxy=True)

    with patch.object(util.config, 'get_config_val',
                      return_value=config_proxy_ip):
        assert config_proxy_ip in util.get_ssh_proxy_options('')
        assert proxy_ip in util.get_ssh_proxy_options('',
                                                      proxy_ip=proxy_ip)

    with patch.dict('os.environ', clear=True):
        with pytest.raises(DCOSException):
            util.get_ssh_proxy_options('', proxy_ip=proxy_ip)


@contextlib.contextmanager
def env():
    """Context manager for altering env vars in tests """

    try:
        old_env = dict(os.environ)
        yield
    finally:
        os.environ.clear()
        os.environ.update(old_env)


def add_cluster_dir(cluster_id, dcos_dir):
    clusters_dir = os.path.join(dcos_dir, constants.DCOS_CLUSTERS_SUBDIR)
    util.ensure_dir_exists(clusters_dir)

    cluster_path = os.path.join(clusters_dir, cluster_id)
    util.ensure_dir_exists(cluster_path)

    os.path.join(cluster_path, "dcos.toml")
    return cluster_path


def create_global_config(dcos_dir):
    global_toml = os.path.join(dcos_dir, "dcos.toml")
    util.ensure_file_exists(global_toml)
    return global_toml
