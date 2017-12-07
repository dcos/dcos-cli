import pytest
from mock import patch

from dcos import constants, mesos, ssh_util
from dcos.errors import DCOSException


def test_get_ssh_user():
    username = 'test_user_name'
    ssh_config_file = '.ssh/special_config'
    assert ssh_util.get_ssh_user(ssh_config_file, None) is None
    assert ssh_util.get_ssh_user(ssh_config_file, username) is None
    assert ssh_util.get_ssh_user(None, username) == username
    with patch.object(ssh_util.config, 'get_config_val',
                      return_value=username):
        assert ssh_util.get_ssh_user(None, None) == username
    with patch.object(ssh_util.config, 'get_config_val',
                      return_value=None):
        assert ssh_util.get_ssh_user(None, None) == constants.DEFAULT_SSH_USER


def test_get_ssh_proxy_options():
    ssh_options = '-o special-ssh=options'
    proxy_ip = '1.1.1.1'
    master_public_ip = '2.2.2.2'
    config_proxy_ip = '3.3.3.3'
    master_metadata = {'PUBLIC_IPV4': master_public_ip}
    env_with_ssh = {'SSH_AUTH_SOCK': '/dummy/socket/address'}

    with patch.dict('os.environ', env_with_ssh, clear=True):
        with patch.object(ssh_util.config, 'get_config_val',
                          return_value=None):
            assert ssh_util.get_ssh_proxy_options('') == ''
            assert proxy_ip in ssh_util.get_ssh_proxy_options(
                '', proxy_ip=proxy_ip)
            assert ssh_options in ssh_util.get_ssh_proxy_options(
                ssh_options, proxy_ip=proxy_ip)
            assert proxy_ip in ssh_util.get_ssh_proxy_options(
                '', proxy_ip=proxy_ip, master_proxy=True)

            with patch.object(mesos, 'DCOSClient') as dcos_client:

                dcos_client().metadata.return_value = master_metadata
                assert master_public_ip in ssh_util.get_ssh_proxy_options(
                    '', master_proxy=True)

                dcos_client().metadata.return_value = {}
                with pytest.raises(DCOSException):
                    ssh_util.get_ssh_proxy_options('', master_proxy=True)

        with patch.object(ssh_util.config, 'get_config_val',
                          return_value=config_proxy_ip):
            assert config_proxy_ip in ssh_util.get_ssh_proxy_options('')
            assert proxy_ip in ssh_util.get_ssh_proxy_options(
                '', proxy_ip=proxy_ip)

    with patch.dict('os.environ', clear=True):
        with pytest.raises(DCOSException):
            ssh_util.get_ssh_proxy_options('', proxy_ip=proxy_ip)
        assert ssh_options in ssh_util.get_ssh_proxy_options(
            ssh_options, proxy_ip=proxy_ip)
