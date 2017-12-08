import pytest
import requests
from mock import create_autospec, patch

from dcos.errors import DCOSException
from dcoscli.cluster.main import (_needs_cluster_cert,
                                  _prompt_for_login_provider)


@patch('requests.get')
def test_needs_cluster_cert_because_ssl_error(req_mock):
    req_mock.side_effect = requests.exceptions.SSLError()

    assert _needs_cluster_cert('https://example.com')


@patch('requests.get')
def test_needs_cluster_cert_because_other_error(req_mock):
    req_mock.side_effect = Exception

    assert _needs_cluster_cert('https://example.com')


@patch('requests.get')
def test_does_not_need_cluster_cert_because_non_https(req_mock):
    resp = create_autospec(requests.Response)
    resp.status_code = 200
    req_mock.return_value = resp

    assert _needs_cluster_cert('http://example.com') is False


@patch('requests.get')
def test_does_not_need_cluster_cert_because_https_works(req_mock):
    resp = create_autospec(requests.Response)
    resp.status_code = 200
    req_mock.return_value = resp

    assert _needs_cluster_cert('https://example.com') is False


def test_prompt_for_login_provider_with_no_supported_provider():
    providers = {
        "dcos-services": {
            "authentication-type": "dcos-uid-servicekey",
            "description": "Default DC/OS authenticator",
            "client-method": "dcos-servicecredential-post-receive-authtoken",
            "config": {
                "start_flow_url": "/acs/api/v1/auth/login"}}}

    with pytest.raises(DCOSException):
        _prompt_for_login_provider(providers)


def test_prompt_for_login_provider_with_single_supported_provider():
    providers = {
        "dcos-users": {
            "authentication-type": "dcos-uid-password",
            "description": "Default DC/OS authenticator",
            "client-method": "dcos-usercredential-post-receive-authtoken",
            "config": {
                "start_flow_url": "/acs/api/v1/auth/login"}},
        "dcos-services": {
            "authentication-type": "dcos-uid-servicekey",
            "description": "Default DC/OS authenticator",
            "client-method": "dcos-servicecredential-post-receive-authtoken",
            "config": {
                "start_flow_url": "/acs/api/v1/auth/login"}}}

    (provider_id, provider_type) = _prompt_for_login_provider(providers)

    assert provider_id == 'dcos-users'
    assert provider_type == "dcos-uid-password"
