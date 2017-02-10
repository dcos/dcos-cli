import json
import mock
import requests

from dcos import packagemanager


describe_response_content_type = 'application/vnd.dcos.package.describe-response+json;charset=utf-8;version=v2'
install_request_content_type = 'application/vnd.dcos.package.install-request+json;charset=utf-8;version=v1'
install_response_content_type = 'application/vnd.dcos.package.install-response+json;charset=utf-8;version=v2'


def make_response(status_code, headers, body=None):
    mock_response = mock.create_autospec(requests.Response)
    mock_response.status_code = status_code
    mock_response.headers = headers
    if body is not None:
        mock_response.body = body
    return mock_response


def test_format_error_message_ambiguous_app_id():
    error_dict = {'type': 'AmbiguousAppId', 'message': '<fake message>'}
    ret = packagemanager._format_error_message(error_dict)
    assert '<fake message>' in ret
    assert 'Please use --app-id to specify the ID of the app to uninstall' in ret


def test_format_error_message_multiple_framework_ids():
    error_dict = {'type': 'MultipleFrameworkIds', 'message': '<fake message>'}
    ret = packagemanager._format_error_message(error_dict)
    assert '<fake message>' in ret
    assert "Manually shut them down using 'dcos service shutdown'" in ret


def test_format_error_message_json_schema_mismatch_unwanted():
    error_dict = {
        'type': 'JsonSchemaMismatch',
        'message': '<fake message>',
        'data': {
            'errors': [
                {'unwanted': ['x', 'y']},
            ],
        },
    }
    ret = packagemanager._format_error_message(error_dict)
    assert '<fake message>' in ret
    assert "Unexpected properties: ['x', 'y']" in ret


def test_format_error_message_marathon_bad_response():
    error_dict = {
        'type': 'MarathonBadResponse',
        'message': '<fake message>',
        'data': {
            'errors': [
                {'error': 'Something went wrong'},
            ],
        },
    }
    ret = packagemanager._format_error_message(error_dict)
    assert '<fake message>' in ret
    assert "Something went wrong" in ret


@mock.patch('dcos.http.post')
def test_install(post_fn):
    post_fn.side_effect = [
        make_response(200, {'Content-Type': describe_response_content_type}),
        make_response(200, {'Content-Type': install_response_content_type}),
    ]

    cosmos_url = 'http://127.0.0.1/cosmos'
    package_manager = packagemanager.PackageManager(cosmos_url)
    pkg = packagemanager.CosmosPackageVersion(
        name='pkg', package_version='0.0.1', url='http://url/to/package')
    package_manager.install_app(pkg=pkg, options=None, app_id=None)
    assert post_fn.mock_calls[0][1][0] == 'http://url/to/package/describe'
    post_fn.assert_called_with(
        mock.ANY,
        data=None,
        headers=mock.ANY,
        json={'packageName': 'pkg', 'packageVersion': '0.0.1'},
    )
