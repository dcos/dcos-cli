import re

from dcos import http, marathon

import mock


def test_add_pod_puts_json_in_request_body():
    _assert_add_pod_puts_json_in_request_body(pod_json={"some": "json"})
    _assert_add_pod_puts_json_in_request_body(
        pod_json=["another", {"json": "value"}])


def test_add_pod_returns_parsed_response_body():
    _assert_add_pod_returns_parsed_response_body({"id": "i-am-a-pod"})
    _assert_add_pod_returns_parsed_response_body(["another", "pod", "json"])


def test_response_error_message_with_400_status_no_json():
    _assert_response_error_message_with_400_status_no_json(
        reason=_REASON_1,
        request_method=_METHOD_1,
        request_url=_URL_1)

    _assert_response_error_message_with_400_status_no_json(
        reason=_REASON_2,
        request_method=_METHOD_2,
        request_url=_URL_2)


def test_response_error_message_with_400_status_json():
    _assert_response_error_message_with_400_status_json(
        _RESPONSE_JSON_1, _PRINTED_JSON_1)

    _assert_response_error_message_with_400_status_json(
        _RESPONSE_JSON_2, _PRINTED_JSON_2)


def test_response_error_message_with_401_status_no_json():
    _assert_response_error_message_with_401_status_no_json(
        reason=_REASON_1,
        request_url=_URL_1)

    _assert_response_error_message_with_401_status_no_json(
        reason=_REASON_2,
        request_url=_URL_2)


def test_response_error_message_with_401_status_json_has_message():
    _assert_response_error_message_with_401_status_json_has_message(
        json_message=_MESSAGE_1)

    _assert_response_error_message_with_401_status_json_has_message(
        json_message=_MESSAGE_2)


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


def _assert_response_error_message_with_400_status_no_json(
        reason, request_method, request_url):
    message = marathon.response_error_message(
        status_code=400,
        reason=reason,
        request_method=request_method,
        request_url=request_url,
        json_body=None)

    pattern = r'Error on request \[(.*) (.*)\]: HTTP 400: (.*)'
    groups = (request_method, request_url, reason)
    _assert_matches_with_groups(pattern, message, groups)


def _assert_response_error_message_with_400_status_json(
        response_json, printed_json):
    message = marathon.response_error_message(
        status_code=400,
        reason=_REASON_X,
        request_method=_METHOD_X,
        request_url=_URL_X,
        json_body=response_json)

    error_line, json_lines = message.split('\n', 1)
    pattern = r'Error on request \[(.*) (.*)\]: HTTP 400: (.*):'
    groups = (_METHOD_X, _URL_X, _REASON_X)

    _assert_matches_with_groups(pattern, error_line, groups)
    assert json_lines == printed_json


def _assert_response_error_message_with_401_status_no_json(
        reason, request_url):
    message = marathon.response_error_message(
        status_code=401,
        reason=reason,
        request_method=_METHOD_X,
        request_url=request_url,
        json_body=None)

    pattern = r'Error decoding response from \[(.*)\]: HTTP 401: (.*)'
    _assert_matches_with_groups(pattern, message, (request_url, reason))


def _assert_response_error_message_with_401_status_json_has_message(
        json_message):
    error_message = marathon.response_error_message(
        status_code=401,
        reason=_REASON_X,
        request_method=_METHOD_X,
        request_url=_URL_X,
        json_body={'message': json_message})

    pattern = r'Error: (.*)'
    _assert_matches_with_groups(pattern, error_message, (json_message,))


def _assert_matches_with_groups(pattern, text, groups):
    match = re.fullmatch(pattern, text)
    assert match
    assert match.groups() == groups


_BASE_TEMPLATE_400 = r'Error on request \[(.*) (.*)\]: HTTP 400: (.*)'

_MESSAGE_1 = 'Oops!'
_MESSAGE_2 = 'Uh oh!'

_METHOD_1 = 'FOO'
_METHOD_2 = 'BAR'
_METHOD_X = 'ANY'

_PRINTED_JSON_1 = (
    '{\n'
    '  "x": "err",\n'
    '  "y": 3.14,\n'
    '  "z": [\n'
    '    1,\n'
    '    2,\n'
    '    3\n'
    '  ]\n'
    '}')
_PRINTED_JSON_2 = (
    '[\n'
    '  "something",\n'
    '  "completely",\n'
    '  "different"\n'
    ']')

_REASON_1 = 'Something Bad'
_REASON_2 = 'Another Reason'
_REASON_X = 'Arbitrary Reason'

_RESPONSE_JSON_1 = {"z": [1, 2, 3], "y": 3.14, "x": "err"}
_RESPONSE_JSON_2 = ["something", "completely", "different"]

_URL_1 = 'http://request/url'
_URL_2 = 'https://another/url'
_URL_X = 'http://does/not/matter'
