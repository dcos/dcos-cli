import copy

from dcos import http
from dcos.errors import DCOSException
from requests.auth import HTTPBasicAuth

import pytest
from mock import Mock, patch


def test_get_realm_good_request():
    with patch('requests.Response') as mock:
        mock.headers = {'www-authenticate': 'Basic realm="Restricted"'}
        res = http._get_realm(mock)
        assert res == "restricted"


def test_get_realm_bad_request():
    with patch('requests.Response') as mock:
        mock.headers = {'www-authenticate': ''}
        res = http._get_realm(mock)
        assert res is None


@patch('requests.Response')
def test_get_http_auth_credentials_not_supported(mock):
    mock.headers = {'www-authenticate': 'test'}
    mock.url = ''
    with pytest.raises(DCOSException) as e:
        http._get_http_auth_credentials(mock)

    msg = ("Server responded with an HTTP 'www-authenticate' field of "
           "'test', DCOS only supports 'Basic'")
    assert e.exconly().split(':')[1].strip() == msg


@patch('requests.Response')
def test_get_http_auth_credentials_bad_response(mock):
    mock.headers = {}
    mock.url = ''
    with pytest.raises(DCOSException) as e:
        http._get_http_auth_credentials(mock)

    msg = ("Invalid HTTP response: server returned an HTTP 401 response "
           "with no 'www-authenticate' field")
    assert e.exconly().split(':', 1)[1].strip() == msg


@patch('dcos.http._get_basic_auth_credentials')
def test_get_http_auth_credentials_good_reponse(auth_mock):
    m = Mock()
    m.url = 'http://domain.com'
    m.headers = {'www-authenticate': 'Basic realm="Restricted"'}
    auth = HTTPBasicAuth("username", "password")
    auth_mock.return_value = auth

    returned_auth = http._get_http_auth_credentials(m)
    assert returned_auth == auth


@patch('requests.Response')
@patch('dcos.http._request')
@patch('dcos.http._get_basic_auth_credentials')
def test_request_with_bad_auth(mock, req_mock, auth_mock):
    mock.url = 'http://domain.com'
    mock.headers = {'www-authenticate': 'Basic realm="Restricted"'}
    mock.status_code = 401

    auth = HTTPBasicAuth("username", "password")
    auth_mock.return_value = auth

    req_mock.return_value = mock

    with pytest.raises(DCOSException) as e:
        http._request_with_auth(mock, "method", mock.url)
    assert e.exconly().split(':')[1].strip() == "Authentication failed"


@patch('requests.Response')
@patch('dcos.http._request')
@patch('dcos.http._get_basic_auth_credentials')
def test_request_with_auth(mock, req_mock, auth_mock):
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
