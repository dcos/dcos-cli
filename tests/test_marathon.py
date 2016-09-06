import re

import requests
from dcos import http, marathon
from dcos.errors import DCOSException, DCOSHTTPException

import mock
import pytest


def test_add_pod_puts_json_in_request_body():
    _assert_add_pod_puts_json_in_request_body(pod_json={"some": "json"})
    _assert_add_pod_puts_json_in_request_body(
        pod_json=["another", {"json": "value"}])


def test_add_pod_returns_parsed_response_body():
    _assert_add_pod_returns_parsed_response_body({"id": "i-am-a-pod"})
    _assert_add_pod_returns_parsed_response_body(["another", "pod", "json"])


def test_rpc_client_http_req_converts_exception_for_400_status():
    _assert_rpc_client_http_req_converts_exception_for_400_status(
        method='FOO',
        url='http://request/url',
        reason='Something Bad')

    _assert_rpc_client_http_req_converts_exception_for_400_status(
        method='BAR',
        url='https://another/url',
        reason='Another Reason')


def _assert_rpc_client_http_req_converts_exception_for_400_status(
        method, url, reason):
    request = requests.Request(method, url)
    response = requests.Response()
    response.request = request.prepare()
    response.status_code = 400
    response.reason = reason

    def bad_method(*args, **kwargs):
        raise DCOSHTTPException(response)

    rpc_client = marathon.RpcClient('http://does/not/matter')
    with pytest.raises(DCOSException) as exception_info:
        rpc_client.http_req(method_fn=bad_method, path='arbitrary/path')

    pattern = r'Error on request \[(.*) (.*)\]: HTTP 400: (.*)'
    match = re.fullmatch(pattern, str(exception_info.value))
    assert (method, url, reason) == match.groups()


def _assert_add_pod_puts_json_in_request_body(pod_json):
    rpc_client = mock.create_autospec(marathon.RpcClient)

    client = marathon.Client(rpc_client)
    client.add_pod(pod_json)

    rpc_client.http_req.assert_called_with(http.post, 'v2/pods', json=pod_json)


def _assert_add_pod_returns_parsed_response_body(response_json):
    rpc_client = mock.create_autospec(marathon.RpcClient)
    rpc_client.http_req.return_value = response_json

    client = marathon.Client(rpc_client)
    assert client.add_pod("arbitrary") == response_json
