import re

import jsonschema
import mock
import pytest
import requests
from requests.structures import CaseInsensitiveDict

from dcos import http, marathon
from dcos.errors import DCOSException, DCOSHTTPException


def test_add_pod_puts_json_in_request_body():
    _assert_add_pod_puts_json_in_request_body(pod_json={"some": "json"})
    _assert_add_pod_puts_json_in_request_body(
        pod_json=["another", {"json": "value"}])


def test_add_pod_returns_parsed_response_body():
    _assert_add_pod_returns_parsed_response_body({"id": "i-am-a-pod"})
    _assert_add_pod_returns_parsed_response_body(["another", "pod", "json"])


def test_add_pod_raises_dcos_exception_for_json_parse_errors():
    _assert_method_raises_dcos_exception_for_json_parse_errors(
        lambda marathon_client: marathon_client.add_pod({'some': 'json'}))


def test_remove_pod_has_default_force_value():
    marathon_client, rpc_client = _create_fixtures()
    marathon_client.remove_pod('foo')
    rpc_client.http_req.assert_called_with(
        http.delete, 'v2/pods/foo', params=None)


def test_remove_pod_builds_rpc_correctly():
    _assert_remove_pod_builds_rpc_correctly(
        pod_id='foo', force=False, path='v2/pods/foo', params=None)
    _assert_remove_pod_builds_rpc_correctly(
        pod_id='foo', force=True, path='v2/pods/foo', params={'force': 'true'})
    _assert_remove_pod_builds_rpc_correctly(
        pod_id='/foo bar/', force=False, path='v2/pods/foo%20bar', params=None)


def test_remove_pod_propagates_dcos_exception():
    _assert_method_propagates_rpc_dcos_exception(
        lambda marathon_client: marathon_client.remove_pod('bad'))


def test_show_pod_builds_rpc_correctly():
    _assert_show_pod_builds_rpc_correctly(pod_id='foo', path='v2/pods/foo')
    _assert_show_pod_builds_rpc_correctly(pod_id='/bar', path='v2/pods/bar')
    _assert_show_pod_builds_rpc_correctly(pod_id='baz/', path='v2/pods/baz')
    _assert_show_pod_builds_rpc_correctly(pod_id='foo bar',
                                          path='v2/pods/foo%20bar')


def test_show_pod_returns_response_json():
    _assert_show_pod_returns_response_json({'some': 'json'})
    _assert_show_pod_returns_response_json(['another', 'json', 'value'])


def test_show_pod_propagates_dcos_exception():
    _assert_method_propagates_rpc_dcos_exception(
        lambda marathon_client: marathon_client.show_pod('bad-req'))


def test_show_pod_raises_dcos_exception_for_json_parse_errors():
    _assert_method_raises_dcos_exception_for_json_parse_errors(
        lambda marathon_client: marathon_client.show_pod('bad-json'))


def test_list_pod_builds_rpc_correctly():
    marathon_client, rpc_client = _create_fixtures()
    marathon_client.list_pod()
    rpc_client.http_req.assert_called_with(http.get, 'v2/pods/::status')


def test_list_pod_returns_success_response_json():
    _assert_list_pod_returns_success_response_json(body_json={'some': 'json'})
    _assert_list_pod_returns_success_response_json(body_json=['a', 'b', 'c'])


def test_list_pod_propagates_rpc_dcos_exception():
    _assert_method_propagates_rpc_dcos_exception(
        lambda marathon_client: marathon_client.list_pod())


def test_list_pod_raises_dcos_exception_for_json_parse_errors():
    _assert_method_raises_dcos_exception_for_json_parse_errors(
        lambda marathon_client: marathon_client.list_pod())


def test_update_pod_executes_successfully():
    _assert_update_pod_executes_successfully(
        pod_id='foo',
        pod_json={'some', 'json'},
        force=False,
        path='v2/pods/foo',
        params=None,
        deployment_id='pod-deployment-id')
    _assert_update_pod_executes_successfully(
        pod_id='/foo bar/',
        pod_json={'some', 'json'},
        force=False,
        path='v2/pods/foo%20bar',
        params=None,
        deployment_id='pod-deployment-id')
    _assert_update_pod_executes_successfully(
        pod_id='foo',
        pod_json={'some', 'json'},
        force=True,
        path='v2/pods/foo',
        params={'force': 'true'},
        deployment_id='pod-deployment-id')
    _assert_update_pod_executes_successfully(
        pod_id='foo',
        pod_json={'something', 'different'},
        force=False,
        path='v2/pods/foo',
        params=None,
        deployment_id='pod-deployment-id')
    _assert_update_pod_executes_successfully(
        pod_id='foo',
        pod_json={'some', 'json'},
        force=False,
        path='v2/pods/foo',
        params=None,
        deployment_id='an-arbitrary-value')


def test_update_pod_has_default_force_value():
    marathon_client, rpc_client = _create_fixtures()
    marathon_client.update_pod('foo', {'some': 'json'})
    rpc_client.http_req.assert_called_with(
        http.put, 'v2/pods/foo', params=None, json={'some': 'json'})


def test_update_pod_propagates_rpc_dcos_exception():
    _assert_method_propagates_rpc_dcos_exception(
        lambda marathon_client:
            marathon_client.update_pod('foo', {'some': 'json'}))


def test_update_pod_raises_dcos_exception_if_deployment_id_missing():
    _assert_update_pod_raises_dcos_exception_if_deployment_id_missing(
        headers={'foo': 'bar'})
    _assert_update_pod_raises_dcos_exception_if_deployment_id_missing(
        headers={'marathon-deployment_ID': 'misspelled-field', 'zzz': 'aaa'})


@mock.patch('dcos.http.head')
def test_pod_feature_supported_gets_success_response(head_fn):
    def invoke_test_case(status_code):
        mock_response = mock.create_autospec(requests.Response)
        mock_response.status_code = status_code
        head_fn.return_value = mock_response

        rpc_client = marathon.RpcClient('http://base/url', timeout=42)
        marathon_client = marathon.Client(rpc_client)
        is_supported = marathon_client.pod_feature_supported()

        head_fn.assert_called_with('http://base/url/v2/pods', timeout=42)

        return is_supported

    assert invoke_test_case(status_code=200)
    assert invoke_test_case(status_code=204)

    assert not invoke_test_case(status_code=100)
    assert not invoke_test_case(status_code=302)


@mock.patch('dcos.http.head')
def test_pod_feature_supported_gets_404_response(head_fn):
    mock_response = mock.create_autospec(requests.Response)
    mock_response.status_code = 404
    head_fn.side_effect = DCOSHTTPException(mock_response)

    rpc_client = marathon.RpcClient('http://base/url', timeout=24)
    marathon_client = marathon.Client(rpc_client)

    assert not marathon_client.pod_feature_supported()
    head_fn.assert_called_with('http://base/url/v2/pods', timeout=24)


def test_pod_feature_supported_converts_http_exceptions_to_dcos_exceptions():
    @mock.patch('dcos.http.head')
    def test_case(head_fn, status_code):
        request = requests.Request(method='ANY', url='http://arbitrary/url')
        mock_response = mock.create_autospec(requests.Response)
        mock_response.status_code = status_code
        mock_response.reason = 'Arbitrary Reason'
        mock_response.request = request
        mock_response.json.side_effect = ValueError('empty body')
        head_fn.side_effect = DCOSHTTPException(mock_response)

        rpc_client = marathon.RpcClient('http://does/not/matter')
        marathon_client = marathon.Client(rpc_client)

        with pytest.raises(DCOSException) as exception_info:
            marathon_client.pod_feature_supported()

        message = marathon.RpcClient.response_error_message(
            status_code,
            reason='Arbitrary Reason',
            request_method='ANY',
            request_url='http://arbitrary/url',
            json_body=None)
        assert str(exception_info.value).endswith(message)

    test_case(status_code=400)
    test_case(status_code=401)
    test_case(status_code=403)
    test_case(status_code=409)
    test_case(status_code=422)
    test_case(status_code=500)


def test_pod_feature_supported_propagates_other_exceptions():
    _assert_pod_feature_supported_raises_exception(
        exception=DCOSException("BOOM!"))
    _assert_pod_feature_supported_raises_exception(
        exception=Exception("Uh oh"))


def test_rpc_client_http_req_calls_method_fn():
    def test_case(base_url, path, full_url):
        method_fn = mock.Mock()

        rpc_client = marathon.RpcClient(base_url)
        rpc_client.http_req(method_fn, path)

        method_fn.assert_called_with(full_url,
                                     timeout=http.DEFAULT_TIMEOUT)

    test_case(
        base_url='http://base/url',
        path='some/path',
        full_url='http://base/url/some/path')
    test_case(
        base_url='http://base/url',
        path='different/thing',
        full_url='http://base/url/different/thing')
    test_case(
        base_url='gopher://different/thing',
        path='some/path',
        full_url='gopher://different/thing/some/path')
    test_case(
        base_url='http://base/without/slash',
        path='/path/with/slash',
        full_url='http://base/without/slash/path/with/slash')
    test_case(
        base_url='http://base/with/slash/',
        path='path/without/slash',
        full_url='http://base/with/slash/path/without/slash')
    test_case(
        base_url='http://base/with/slash/',
        path='/path/with/slash',
        full_url='http://base/with/slash/path/with/slash')


def test_rpc_client_http_req_passes_args_to_method_fn():
    method_fn = mock.Mock()

    rpc_client = marathon.RpcClient('http://base/url')
    rpc_client.http_req(method_fn, 'some/path', 'foo', 42)

    method_fn.assert_called_with('http://base/url/some/path',
                                 'foo',
                                 42,
                                 timeout=http.DEFAULT_TIMEOUT)


def test_rpc_client_http_req_passes_kwargs_to_method_fn():
    method_fn = mock.Mock()

    rpc_client = marathon.RpcClient('http://base/url')
    rpc_client.http_req(method_fn, 'some/path', foo='bar', baz=42)

    method_fn.assert_called_with('http://base/url/some/path',
                                 foo='bar',
                                 baz=42,
                                 timeout=http.DEFAULT_TIMEOUT)


def test_rpc_client_http_req_kwarg_timeout_overrides_default():
    method_fn = mock.Mock()

    rpc_client = marathon.RpcClient('http://base/url')
    rpc_client.http_req(method_fn, 'some/path', timeout=42)

    method_fn.assert_called_with('http://base/url/some/path', timeout=42)


def test_rpc_client_http_req_set_timeout_in_constructor():
    method_fn = mock.Mock()

    rpc_client = marathon.RpcClient('http://base/url', 24)
    rpc_client.http_req(method_fn, 'some/path')

    method_fn.assert_called_with('http://base/url/some/path', timeout=24)


def test_rpc_client_http_req_returns_method_fn_result():
    def test_case(expected):

        def method_fn(*args, **kwargs):
            return expected

        rpc_client = marathon.RpcClient('http://base/url')
        actual = rpc_client.http_req(method_fn, 'some/path')

        assert actual == expected

    test_case(['the', 'result'])
    test_case({'another': 'result'})


def test_rpc_client_http_req_propagates_method_fn_exception_1():
    request = requests.Request(method='ANY', url='http://arbitrary/url')
    response = requests.Response()
    response.status_code = 403
    response.reason = 'Forbidden'
    response.request = request

    def method_fn(*args, **kwargs):
        raise DCOSHTTPException(response)

    rpc_client = marathon.RpcClient('http://base/url')
    with pytest.raises(DCOSException) as e:
        rpc_client.http_req(method_fn, 'some/path')

    expected_message = marathon.RpcClient.response_error_message(
        status_code=403,
        reason='Forbidden',
        request_method='ANY',
        request_url='http://arbitrary/url',
        json_body=None)
    assert str(e).endswith(expected_message)


def test_rpc_client_http_req_propagates_method_fn_exception_2():
    request = requests.Request(method='NONE', url='http://host/path')
    # Need the mock so that the json() method can be overridden
    response = mock.create_autospec(requests.Response)
    response.status_code = 422
    response.reason = 'Something Bad'
    response.request = request
    response.json.return_value = {'message': 'BOOM!'}

    def method_fn(*args, **kwargs):
        raise DCOSHTTPException(response)

    rpc_client = marathon.RpcClient('http://base/url')
    with pytest.raises(DCOSException) as e:
        rpc_client.http_req(method_fn, 'some/path')

    expected_message = marathon.RpcClient.response_error_message(
        status_code=422,
        reason='Something Bad',
        request_method='None',
        request_url='http://host/path',
        json_body={'message': 'BOOM!'})
    assert str(e).endswith(expected_message)


def test_error_json_schema_is_valid():
    error_json_schema = marathon.load_error_json_schema()
    jsonschema.Draft4Validator.check_schema(error_json_schema)


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


def test_res_err_msg_with_409_status():
    def test_case(request_url, expected_resource):
        actual = marathon.RpcClient.response_error_message(
            status_code=409,
            reason=_REASON_X,
            request_method=_METHOD_X,
            request_url=request_url,
            json_body=None)

        pattern = r'Changes blocked: deployment already in progress for (.*)\.'
        _assert_matches_with_groups(pattern, actual, (expected_resource,))

    test_case('http://marathon/v2/apps', 'app')
    test_case('http://marathon/v2/groups/group-id', 'group')
    test_case('http://marathon/v2/pods/', 'pod')
    test_case('http://marathon/v2/thingies/foo', 'resource')
    test_case('http://dcos/service/marathon/v2/apps/bar', 'app')
    test_case('http://pods-app.com/service/marathon/v2/groups/baz', 'group')


def test_response_error_message_with_other_status_no_json():
    _assert_response_error_message_with_other_status_no_json(
        status_code=401,
        reason=_REASON_1,
        request_url=_URL_1)

    _assert_response_error_message_with_other_status_no_json(
        status_code=401,
        reason=_REASON_2,
        request_url=_URL_2)

    _assert_response_error_message_with_other_status_no_json(
        status_code=403,
        reason=_REASON_X,
        request_url=_URL_X)

    _assert_response_error_message_with_other_status_no_json(
        status_code=404,
        reason=_REASON_X,
        request_url=_URL_X)

    _assert_response_error_message_with_other_status_no_json(
        status_code=422,
        reason=_REASON_X,
        request_url=_URL_X)


def test_response_error_message_with_other_status_json_has_message():
    _assert_response_error_message_with_other_status_json_has_message(
        status_code=401,
        json_message=_MESSAGE_1)

    _assert_response_error_message_with_other_status_json_has_message(
        status_code=401,
        json_message=_MESSAGE_2)

    _assert_response_error_message_with_other_status_json_has_message(
        status_code=403,
        json_message=_MESSAGE_X)

    _assert_response_error_message_with_other_status_json_has_message(
        status_code=404,
        json_message=_MESSAGE_X)

    _assert_response_error_message_with_other_status_json_has_message(
        status_code=422,
        json_message=_MESSAGE_X)


def test_res_err_msg_with_other_status_json_no_message_has_valid_errors():
    _assert_res_err_msg_with_other_status_json_no_message_has_valid_errors(
        status_code=401,
        errors_json=[{'error': 'err1'}, {'error': 'err2'}],
        errors_str='err1\nerr2')

    _assert_res_err_msg_with_other_status_json_no_message_has_valid_errors(
        status_code=401,
        errors_json=[{'error': 'foo'}, {'error': 'bar'}, {'error': 'baz'}],
        errors_str='foo\nbar\nbaz')

    _assert_res_err_msg_with_other_status_json_no_message_has_valid_errors(
        status_code=403,
        errors_json=[{'error': 'foo'}, {'error': 'bar'}, {'error': 'baz'}],
        errors_str='foo\nbar\nbaz')

    _assert_res_err_msg_with_other_status_json_no_message_has_valid_errors(
        status_code=404,
        errors_json=[{'error': 'foo'}, {'error': 'bar'}, {'error': 'baz'}],
        errors_str='foo\nbar\nbaz')

    _assert_res_err_msg_with_other_status_json_no_message_has_valid_errors(
        status_code=422,
        errors_json=[{'error': 'foo'}, {'error': 'bar'}, {'error': 'baz'}],
        errors_str='foo\nbar\nbaz')


def test_res_err_msg_with_other_status_invalid_error_json():
    # Is not an object
    _assert_res_err_msg_with_other_status_invalid_json(401, 'Error!')
    _assert_res_err_msg_with_other_status_invalid_json(401, ['Error!'])
    # Missing both message and errors fields
    _assert_res_err_msg_with_other_status_invalid_json(401, {})
    _assert_res_err_msg_with_other_status_invalid_json(
        401, {'foo': 5, 'bar': 'x'})
    # Has non-str message
    _assert_res_err_msg_with_other_status_invalid_json(401, {'message': 42})
    _assert_res_err_msg_with_other_status_invalid_json(
        401, {'message': ['Oops!']})
    # Has non-array errors
    _assert_res_err_msg_with_other_status_invalid_json(401, {'errors': 42})
    _assert_res_err_msg_with_other_status_invalid_json(
        401, {'errors': {'error': 5}})
    # Errors array has non-object elements
    _assert_res_err_msg_with_other_status_invalid_json(
        401, {'errors': [42, True]})
    _assert_res_err_msg_with_other_status_invalid_json(
        401, {'errors': [{'error': 'BOOM!'}, 'not_an_error']})
    # Errors array has objects without `error` field
    _assert_res_err_msg_with_other_status_invalid_json(
        401, {'errors': [{'error': 'BOOM!'}, {'foo': 'bar'}]})
    # Errors array has objects with non-str `error` field
    _assert_res_err_msg_with_other_status_invalid_json(
        401, {'errors': [{'error': 'BOOM!'}, {'error': 42}]})
    # Other status codes
    _assert_res_err_msg_with_other_status_invalid_json(
        403, {'errors': [{'error': 'BOOM!'}, {'error': 42}]})
    _assert_res_err_msg_with_other_status_invalid_json(
        404, {'errors': [{'error': 'BOOM!'}, {'error': 42}]})
    _assert_res_err_msg_with_other_status_invalid_json(
        422, {'errors': [{'error': 'BOOM!'}, {'error': 42}]})


def _assert_add_pod_puts_json_in_request_body(pod_json):
    rpc_client = mock.create_autospec(marathon.RpcClient)

    client = marathon.Client(rpc_client)
    client.add_pod(pod_json)

    rpc_client.http_req.assert_called_with(http.post, 'v2/pods', json=pod_json)


def _assert_add_pod_returns_parsed_response_body(response_json):
    mock_response = mock.create_autospec(requests.Response)
    mock_response.json.return_value = response_json

    marathon_client, rpc_client = _create_fixtures()
    rpc_client.http_req.return_value = mock_response

    assert marathon_client.add_pod({'some': 'json'}) == response_json


def _assert_remove_pod_builds_rpc_correctly(pod_id, force, path, params):
    marathon_client, rpc_client = _create_fixtures()
    marathon_client.remove_pod(pod_id, force)
    rpc_client.http_req.assert_called_with(http.delete, path, params=params)


def _assert_show_pod_builds_rpc_correctly(pod_id, path):
    marathon_client, rpc_client = _create_fixtures()
    marathon_client.show_pod(pod_id)
    rpc_client.http_req.assert_called_with(http.get, path)


def _assert_show_pod_returns_response_json(expected):
    marathon_client, rpc_client = _create_fixtures()
    mock_response = mock.create_autospec(requests.Response)
    mock_response.json.return_value = expected
    rpc_client.http_req.return_value = mock_response

    response_json = marathon_client.show_pod('arbitrary-id')

    assert response_json == expected


def _assert_list_pod_returns_success_response_json(body_json):
    marathon_client, rpc_client = _create_fixtures()
    mock_response = mock.create_autospec(requests.Response)
    mock_response.json.return_value = body_json
    rpc_client.http_req.return_value = mock_response

    assert marathon_client.list_pod() == body_json


def _assert_update_pod_executes_successfully(
        pod_id, pod_json, force, path, params, deployment_id):
    headers = {'Marathon-Deployment-Id': deployment_id}
    mock_response = _update_pod_response_fixture(headers)

    marathon_client, rpc_client = _create_fixtures()
    rpc_client.http_req.return_value = mock_response

    actual_return = marathon_client.update_pod(pod_id, pod_json, force)

    rpc_client.http_req.assert_called_with(
        http.put, path, params=params, json=pod_json)
    assert actual_return == deployment_id


def _assert_method_raises_dcos_exception_for_json_parse_errors(invoke_method):
    def assert_test_case(non_json):
        mock_response = mock.create_autospec(requests.Response)
        mock_response.json.side_effect = Exception()
        mock_response.text = non_json

        marathon_client, rpc_client = _create_fixtures()
        rpc_client.http_req.return_value = mock_response

        with pytest.raises(DCOSException) as exception_info:
            invoke_method(marathon_client)

        pattern = ('Error: Response from Marathon was not in expected JSON '
                   'format:\n(.*)')
        actual_error = str(exception_info.value)
        _assert_matches_with_groups(pattern, actual_error, (non_json,))

    assert_test_case('not-json')
    assert_test_case('{"oops"}')


def _assert_update_pod_raises_dcos_exception_if_deployment_id_missing(headers):
    marathon_client, rpc_client = _create_fixtures()
    rpc_client.http_req.return_value = _update_pod_response_fixture(headers)

    with pytest.raises(DCOSException) as exception_info:
        marathon_client.update_pod('foo', {'some': 'json'})

    expected_error = ('Error: missing "Marathon-Deployment-Id" header from '
                      'Marathon response')
    assert str(exception_info.value) == expected_error


def _assert_method_propagates_rpc_dcos_exception(invoke_method):
    marathon_client, rpc_client = _create_fixtures()
    rpc_client.http_req.side_effect = DCOSException('BOOM!')

    with pytest.raises(DCOSException) as exception_info:
        invoke_method(marathon_client)

    assert str(exception_info.value) == 'BOOM!'


@mock.patch('dcos.http.head')
def _assert_pod_feature_supported_raises_exception(head_fn, exception):
    rpc_client = marathon.RpcClient('http://base/url', timeout=22)
    marathon_client = marathon.Client(rpc_client)
    head_fn.side_effect = exception

    with pytest.raises(exception.__class__) as exception_info:
        marathon_client.pod_feature_supported()

    assert exception_info.value == exception


def _assert_response_error_message_with_400_status_no_json(
        reason, request_method, request_url):
    message = marathon.RpcClient.response_error_message(
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
    message = marathon.RpcClient.response_error_message(
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


def _assert_response_error_message_with_other_status_no_json(
        status_code, reason, request_url):
    message = marathon.RpcClient.response_error_message(
        status_code=status_code,
        reason=reason,
        request_method=_METHOD_X,
        request_url=request_url,
        json_body=None)

    pattern = r'Error decoding response from \[(.*)\]: HTTP (.*): (.*)'
    groups = (request_url, str(status_code), reason)
    _assert_matches_with_groups(pattern, message, groups)


def _assert_response_error_message_with_other_status_json_has_message(
        status_code, json_message):
    error_message = marathon.RpcClient.response_error_message(
        status_code=status_code,
        reason=_REASON_X,
        request_method=_METHOD_X,
        request_url=_URL_X,
        json_body={'message': json_message})

    pattern = r'Error: (.*)'
    _assert_matches_with_groups(pattern, error_message, (json_message,))


def _assert_res_err_msg_with_other_status_json_no_message_has_valid_errors(
        status_code, errors_json, errors_str):
    message = marathon.RpcClient.response_error_message(
        status_code=status_code,
        reason=_REASON_X,
        request_method=_METHOD_X,
        request_url=_URL_X,
        json_body={'errors': errors_json})

    pattern = (r'Marathon likely misconfigured\. Please check your proxy or '
               r'Marathon URL settings\. See dcos config --help\. (.*)')
    _assert_matches_with_groups(pattern, message, (errors_str,))


def _assert_res_err_msg_with_other_status_invalid_json(status_code, json_body):
    actual = marathon.RpcClient.response_error_message(
        status_code=status_code,
        reason=_REASON_X,
        request_method=_METHOD_X,
        request_url=_URL_X,
        json_body=json_body)

    expected = ('Marathon likely misconfigured. Please check your proxy or '
                'Marathon URL settings. See dcos config --help. ')
    assert actual == expected


def _assert_matches_with_groups(pattern, text, groups):
    match = re.fullmatch(pattern, text, flags=re.DOTALL)
    assert match
    assert match.groups() == groups


def _create_fixtures():
    rpc_client = mock.create_autospec(marathon.RpcClient)
    marathon_client = marathon.Client(rpc_client)

    return marathon_client, rpc_client


def _update_pod_response_fixture(headers=None):
    mock_response = mock.create_autospec(requests.Response)

    headers = CaseInsensitiveDict({} if headers is None else headers)
    mock_response.headers = headers

    return mock_response


_MESSAGE_1 = 'Oops!'
_MESSAGE_2 = 'Uh oh!'
_MESSAGE_X = "D'oh!"

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
