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
    _assert_rpc_client_http_req_converts_exception_for_400_status_non_json(
        method='FOO',
        url='http://request/url',
        reason='Something Bad')

    _assert_rpc_client_http_req_converts_exception_for_400_status_non_json(
        method='BAR',
        url='https://another/url',
        reason='Another Reason')


def test_rpc_client_http_req_converts_exception_for_400_status_with_json():
    printed_json1 = (
        '{\n'
        '  "x": "err",\n'
        '  "y": 3.14,\n'
        '  "z": [\n'
        '    1,\n'
        '    2,\n'
        '    3\n'
        '  ]\n'
        '}')
    _assert_rpc_client_http_req_converts_400_status_exception_with_json(
        response_json={"z": [1, 2, 3], "y": 3.14, "x": "err"},
        printed_json=printed_json1)

    printed_json2 = (
        '[\n'
        '  "something",\n'
        '  "completely",\n'
        '  "different"\n'
        ']')
    _assert_rpc_client_http_req_converts_400_status_exception_with_json(
        response_json=["something", "completely", "different"],
        printed_json=printed_json2)


def test_rpc_client_http_req_converts_401_status_exception():
    _assert_rpc_client_http_req_converts_401_status_exception(
        request_url='http://request/url',
        status_reason='Something Bad')

    _assert_rpc_client_http_req_converts_401_status_exception(
        request_url='https://another/url',
        status_reason='Another Reason')


def _assert_rpc_client_http_req_converts_401_status_exception(
        request_url, status_reason):
    response = _mock_response(
        request_method='ANY',
        request_url=request_url,
        status_code=401,
        status_reason=status_reason)
    response.json.side_effect = ValueError()

    exception = _assert_rpc_client_raises_exception_from_response(response)

    pattern = r'Error decoding response from \[(.*)\]: HTTP 401: (.*)'
    match = re.fullmatch(pattern, str(exception))
    assert match
    assert match.groups() == (request_url, status_reason)


def _assert_rpc_client_http_req_converts_400_status_exception_with_json(
        response_json, printed_json):
    response = _mock_response(
        request_method='POST',
        request_url='http://some/url',
        status_code=400,
        status_reason='Some Reason')
    response.json.return_value = response_json

    exception = _assert_rpc_client_raises_exception_from_response(response)

    message = str(exception)
    error_line, json_lines = message.split('\n', 1)

    pattern = r'Error on request \[(.*) (.*)\]: HTTP 400: (.*):'
    match = re.fullmatch(pattern, error_line)
    assert match.groups() == ('POST', 'http://some/url', 'Some Reason')

    assert json_lines == printed_json


def _assert_rpc_client_http_req_converts_exception_for_400_status_non_json(
        method, url, reason):
    response = _mock_response(method, url, 400, reason)
    response.json.side_effect = ValueError()

    exception = _assert_rpc_client_raises_exception_from_response(response)

    pattern = r'Error on request \[(.*) (.*)\]: HTTP 400: (.*)'
    match = re.fullmatch(pattern, str(exception))
    assert match.groups() == (method, url, reason)


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


def _assert_rpc_client_raises_exception_from_response(response):
    def bad_method(*args, **kwargs):
        raise DCOSHTTPException(response)

    rpc_client = marathon.RpcClient('http://does/not/matter')
    with pytest.raises(DCOSException) as exception_info:
        rpc_client.http_req(method_fn=bad_method, path='arbitrary/path')

    return exception_info.value


def _mock_response(request_method, request_url, status_code, status_reason):
    request = requests.Request(request_method, request_url)
    response = mock.create_autospec(requests.Response)
    response.request = request.prepare()
    response.status_code = status_code
    response.reason = status_reason
    return response
