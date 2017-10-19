import requests
from mock import create_autospec, patch

from dcoscli.cluster.main import _needs_cluster_cert


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
