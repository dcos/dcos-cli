from mock import patch

from requests import Response

from dcos import config, http


def test_is_request_to_dcos():
    toml_config = config.Toml({
        'core': {'dcos_url': "https://example.com"}
    })

    assert http._is_request_to_dcos(
        "https://example.com/path", toml_config=toml_config)

    assert http._is_request_to_dcos(
        "https://EXAMPLE.com/path", toml_config=toml_config)

    assert not http._is_request_to_dcos(
        "https://foo.com/path", toml_config=toml_config)


@patch('requests.request')
def test_request_default_timeout_without_config(requests_mock):
    timeout = True
    toml_config = config.Toml({})
    expected_timeout = http.DEFAULT_TIMEOUT

    _assert_request_timeout(
        requests_mock,
        timeout,
        toml_config,
        expected_timeout)


@patch('requests.request')
def test_request_default_timeout_with_config(requests_mock):
    timeout = 5

    toml_config = config.Toml({
        'core': {'timeout': timeout}
    })

    expected_timeout = (http.DEFAULT_CONNECT_TIMEOUT, timeout)

    _assert_request_timeout(
        requests_mock,
        timeout,
        toml_config,
        expected_timeout)


@patch('requests.request')
def test_request_timeout_with_numeric_argument(requests_mock):
    timeout = 30
    toml_config = config.Toml({})
    expected_timeout = (http.DEFAULT_CONNECT_TIMEOUT, timeout)

    _assert_request_timeout(
        requests_mock,
        timeout,
        toml_config,
        expected_timeout)


@patch('requests.request')
def test_request_timeout_with_tuple_argument(requests_mock):
    timeout = (5, 30)
    toml_config = config.Toml({})

    _assert_request_timeout(requests_mock, timeout, toml_config, timeout)


def _assert_request_timeout(
        requests_mock, timeout, toml_config, expected_timeout):
    resp = Response()
    resp.status_code = 200
    requests_mock.return_value = resp

    method = 'GET'
    url = 'https://www.example.com'

    http.request(
        method,
        url,
        timeout=timeout,
        headers={},
        toml_config=toml_config)

    requests_mock.assert_called_once_with(
        method=method,
        url=url,
        auth=None,
        timeout=expected_timeout,
        headers={},
        verify=None)
