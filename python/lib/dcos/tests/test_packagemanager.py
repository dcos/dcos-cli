import mock
import pytest
import requests

from dcos import packagemanager


def describe_response_headers(pkg_mgr):
    content_type = pkg_mgr.cosmos._get_accept('package.describe', 'v3')
    return {'Content-Type': content_type}


def install_response_headers(pkg_mgr):
    content_type = pkg_mgr.cosmos._get_accept('package.install', 'v2')
    return {'Content-Type': content_type}


def mock_response(status_code, headers, body=None):
    res = mock.create_autospec(requests.Response)
    res.status_code = status_code
    res.headers = headers
    if body is not None:
        res.body = body
    return res


@pytest.fixture
def pkg_mgr():
    return packagemanager.PackageManager('http://testserver/cosmos')


@pytest.fixture
def fake_pkg(pkg_mgr):
    with mock.patch('dcos.http.post') as post_fn:
        post_fn.return_value = mock_response(
            200, describe_response_headers(pkg_mgr),
        )
        yield pkg_mgr.get_package_version('fake_pkg', '0.0.1')


def test_format_error_message_ambiguous_app_id():
    error_dict = {'type': 'AmbiguousAppId', 'message': '<fake message>'}
    ret = packagemanager._format_error_message(error_dict)
    assert '<fake message>' in ret
    assert 'the ID of the app to uninstall' in ret


def test_format_error_message_multiple_framework_ids():
    error_dict = {'type': 'MultipleFrameworkIds', 'message': '<fake message>'}
    ret = packagemanager._format_error_message(error_dict)
    assert '<fake message>' in ret
    assert "Manually shut them down using 'dcos service shutdown'" in ret


def test_format_error_message_json_schema_mismatch():
    error_dict = {
        'type': 'JsonSchemaMismatch',
        'message': '<fake message>',
        'data': {
            'errors': [
                {'unwanted': ['x', 'y']},
                {'found': 128, 'minimum': 256,
                 'instance': {'pointer': 'service.mem'}},
                {'expected': ['yes', 'no']},
            ],
        },
    }
    ret = packagemanager._format_error_message(error_dict)
    assert '<fake message>' in ret
    assert 'Found: 128' in ret
    assert 'minimum: 256' in ret
    assert 'Path: service.mem' in ret
    assert 'Expected: yes,no' in ret
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
def test_install(post_fn, pkg_mgr, fake_pkg):
    post_fn.return_value = mock_response(
        200, install_response_headers(pkg_mgr),
    )
    pkg_mgr.install_app(fake_pkg, options=None)
    post_fn.assert_called_with(
        'http://testserver/package/install',
        data=None,
        headers=pkg_mgr.cosmos._get_header('package/install', 'v2'),
        json={'packageName': fake_pkg.name(),
              'packageVersion': fake_pkg.version()},
    )
