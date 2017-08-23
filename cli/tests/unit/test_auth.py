import pytest
import requests
from mock import create_autospec, patch

from dcos import auth
from dcos.errors import DCOSException


def test_get_auth_scheme():
    _get_auth_scheme({'WWW-Authenticate': 'acsjwt'}, scheme='acsjwt')
    _get_auth_scheme({'WWW-Authenticate': 'oauthjwt'}, scheme='oauthjwt')
    _get_auth_scheme({}, scheme=None)

    msg = ("Server responded with an HTTP 'www-authenticate' field of "
           "'foobar', DC/OS only supports ['oauthjwt', 'acsjwt']")
    _get_auth_scheme_exception({'WWW-Authenticate': 'foobar'}, msg)


def _get_auth_scheme(header, scheme):
    with patch('requests.Response') as mock:
        mock.headers = header
        auth_scheme = auth._get_auth_scheme(mock)
        assert auth_scheme == scheme


def _get_auth_scheme_exception(header, err_msg):
    with patch('requests.Response') as mock:
        mock.headers = header
        with pytest.raises(DCOSException) as e:
            auth._get_auth_scheme(mock)

    assert str(e.value) == err_msg


@patch('dcos.http._request')
@patch('dcos.config.set_val')
def test_get_dcostoken_by_post_with_creds(config, req):
    creds = {"foobar"}
    resp = create_autospec(requests.Response)
    resp.status_code = 200
    resp.json.return_value = {"token": "foo"}
    req.return_value = resp

    auth._get_dcostoken_by_post_with_creds("http://url", creds)
    req.assert_called_with(
        "post", "http://url/acs/api/v1/auth/login", json=creds)
    config.assert_called_with("core.dcos_acs_token", "foo")


@patch('dcos.http._request')
@patch('dcos.auth._get_dcostoken_by_oidc_implicit_flow')
@patch('dcos.auth._get_dcostoken_by_dcos_uid_password_auth')
def test_header_challenge_auth(cred_auth, oidc_auth, req):
    resp = create_autospec(requests.Response)
    resp.status_code = 401
    resp.headers = {"WWW-Authenticate": "oauthjwt"}
    req.return_value = resp

    auth.header_challenge_auth("url")
    oidc_auth.assert_called_once()

    resp2 = create_autospec(requests.Response)
    resp2.status_code = 401
    resp2.headers = {"WWW-Authenticate": "acsjwt"}
    req.return_value = resp2

    auth.header_challenge_auth("url")
    cred_auth.assert_called_once()


@patch('dcos.http.get')
@patch('dcos.config.get_config_val')
def test_get_providers(config, req_mock):
    resp = create_autospec(requests.Response)
    resp.return_value = {}
    req_mock.return_value = resp
    config.return_value = "http://localhost"

    auth.get_providers()
    req_mock.assert_called_with(
        "http://localhost/acs/api/v1/auth/providers")

    # test url construction valid with trailing slash
    config.return_value = "http://localhost/"

    auth.get_providers()
    req_mock.assert_called_with(
        "http://localhost/acs/api/v1/auth/providers")


@patch('dcos.http._request')
@patch('dcos.config.get_config_val')
def test_get_providers_errors(config, req):
    config.return_value = "http://localhost"

    resp = create_autospec(requests.Response)
    resp.status_code = 404
    req.return_value = resp

    with pytest.raises(DCOSException) as e:
        auth.get_providers()

    err_msg = "This command is not supported for your cluster"
    assert str(e.value) == err_msg
