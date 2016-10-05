import copy

import pytest
from mock import Mock, patch
from requests.auth import HTTPBasicAuth
from six.moves.urllib.parse import urlparse

from dcos import http
from dcos.errors import DCOSException


def test_get_auth_scheme_basic():
    with patch('requests.Response') as mock:
        mock.headers = {'www-authenticate': 'Basic realm="Restricted"'}
        auth_scheme, realm = http.get_auth_scheme(mock)
        assert auth_scheme == "basic"
        assert realm == "restricted"


def test_get_auth_scheme_acs():
    with patch('requests.Response') as mock:
        mock.headers = {'www-authenticate': 'acsjwt'}
        auth_scheme, realm = http.get_auth_scheme(mock)
        assert auth_scheme == "acsjwt"
        assert realm == "acsjwt"


def test_get_auth_scheme_oauth():
    with patch('requests.Response') as mock:
        mock.headers = {'www-authenticate': 'oauthjwt'}
        auth_scheme, realm = http.get_auth_scheme(mock)
        assert auth_scheme == "oauthjwt"
        assert realm == "oauthjwt"


def test_get_auth_scheme_bad_request():
    with patch('requests.Response') as mock:
        mock.headers = {'www-authenticate': ''}
        res = http.get_auth_scheme(mock)
        assert res == (None, None)


@patch('requests.Response')
def test_get_http_auth_not_supported(mock):
    mock.headers = {'www-authenticate': 'test'}
    mock.url = ''
    with pytest.raises(DCOSException) as e:
        http._get_http_auth(mock, url=urlparse(''), auth_scheme='foo')

    msg = ("Server responded with an HTTP 'www-authenticate' field of "
           "'test', DC/OS only supports 'Basic'")
    assert e.exconly().split(':')[1].strip() == msg


@patch('requests.Response')
def test_get_http_auth_bad_response(mock):
    mock.headers = {}
    mock.url = ''
    with pytest.raises(DCOSException) as e:
        http._get_http_auth(mock, url=urlparse(''), auth_scheme='')

    msg = ("Invalid HTTP response: server returned an HTTP 401 response "
           "with no 'www-authenticate' field")
    assert e.exconly().split(':', 1)[1].strip() == msg


@patch('dcos.http._get_auth_credentials')
def test_get_http_auth_credentials_basic(auth_mock):
    m = Mock()
    m.url = 'http://domain.com'
    m.headers = {'www-authenticate': 'Basic realm="Restricted"'}
    auth_mock.return_value = ("username", "password")

    returned_auth = http._get_http_auth(m, urlparse(m.url), "basic")
    assert type(returned_auth) == HTTPBasicAuth
    assert returned_auth.username == "username"
    assert returned_auth.password == "password"


@patch('dcos.http._get_auth_credentials')
@patch('dcos.http._request')
def test_get_http_auth_credentials_acl(req_mock, auth_mock):
    m = Mock()
    m.url = 'http://domain.com'
    m.headers = {'www-authenticate': 'acsjwt"'}
    auth_mock.return_value = ("username", "password")
    req_mock.status_code = 404

    returned_auth = http._get_http_auth(m, urlparse(m.url), "acsjwt")
    assert type(returned_auth) == http.DCOSAcsAuth


@patch('requests.Response')
@patch('dcos.http._request')
@patch('dcos.http._get_http_auth')
def test_request_with_bad_auth_basic(mock, req_mock, auth_mock):
    mock.url = 'http://domain.com'
    mock.headers = {'www-authenticate': 'Basic realm="Restricted"'}
    mock.status_code = 401

    auth_mock.return_value = HTTPBasicAuth("username", "password")

    req_mock.return_value = mock

    with pytest.raises(DCOSException) as e:
        http._request_with_auth(mock, "method", mock.url)
    assert e.exconly().split(':')[1].strip() == "Authentication failed"


@patch('requests.Response')
@patch('dcos.http._request')
@patch('dcos.http._get_http_auth')
def test_request_with_bad_auth_acl(mock, req_mock, auth_mock):
    mock.url = 'http://domain.com'
    mock.headers = {'www-authenticate': 'acsjwt'}
    mock.status_code = 401

    auth_mock.return_value = http.DCOSAcsAuth("token")

    req_mock.return_value = mock

    with pytest.raises(DCOSException) as e:
        http._request_with_auth(mock, "method", mock.url)
    msg = "Your core.dcos_acs_token is invalid. Please run: `dcos auth login`"
    assert e.exconly().split(':', 1)[1].strip() == msg


@patch('requests.Response')
@patch('dcos.http._request')
@patch('dcos.http._get_http_auth')
def test_request_with_bad_oauth(mock, req_mock, auth_mock):
    mock.url = 'http://domain.com'
    mock.headers = {'www-authenticate': 'oauthjwt'}
    mock.status_code = 401

    auth_mock.return_value = http.DCOSAcsAuth("token")

    req_mock.return_value = mock

    with pytest.raises(DCOSException) as e:
        http._request_with_auth(mock, "method", mock.url)
    msg = "Your core.dcos_acs_token is invalid. Please run: `dcos auth login`"
    assert e.exconly().split(':', 1)[1].strip() == msg


@patch('requests.Response')
@patch('dcos.http._request')
@patch('dcos.http._get_http_auth')
def test_request_with_auth_basic(mock, req_mock, auth_mock):
    mock.url = 'http://domain.com'
    mock.headers = {'www-authenticate': 'Basic realm="Restricted"'}
    mock.status_code = 401

    auth = HTTPBasicAuth("username", "password")
    auth_mock.return_value = auth

    mock2 = copy.deepcopy(mock)
    mock2.status_code = 200
    req_mock.return_value = mock2

    response = http._request_with_auth(mock, "method", mock.url)
    assert response.status_code == 200


@patch('requests.Response')
@patch('dcos.http._request')
@patch('dcos.http._get_http_auth')
def test_request_with_auth_acl(mock, req_mock, auth_mock):
    mock.url = 'http://domain.com'
    mock.headers = {'www-authenticate': 'acsjwt'}
    mock.status_code = 401

    auth = http.DCOSAcsAuth("token")
    auth_mock.return_value = auth

    mock2 = copy.deepcopy(mock)
    mock2.status_code = 200
    req_mock.return_value = mock2

    response = http._request_with_auth(mock, "method", mock.url)
    assert response.status_code == 200


@patch('requests.Response')
@patch('dcos.http._request')
@patch('dcos.http._get_http_auth')
def test_request_with_auth_oauth(mock, req_mock, auth_mock):
    mock.url = 'http://domain.com'
    mock.headers = {'www-authenticate': 'oauthjwt'}
    mock.status_code = 401

    auth = http.DCOSAcsAuth("token")
    auth_mock.return_value = auth

    mock2 = copy.deepcopy(mock)
    mock2.status_code = 200
    req_mock.return_value = mock2

    response = http._request_with_auth(mock, "method", mock.url)
    assert response.status_code == 200
