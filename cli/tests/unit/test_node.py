import mock
import pytest

import dcoscli.node.main as main
from dcos.errors import DCOSException


@mock.patch('dcos.cosmospackage.Cosmos')
def test_check_version_fail(mock_cosmos):
    """
    Test _check_3dt_version(), should throw DCOSException exception.
    """

    mock_cosmos().enabled.return_value = True
    mock_cosmos().has_capability.return_value = False

    with pytest.raises(DCOSException) as excinfo:
        main._check_3dt_version()
    assert str(excinfo.value) == (
        'DC/OS backend does not support diagnostics capabilities in this '
        'version. Must be DC/OS >= 1.8')


@mock.patch('dcos.cosmospackage.Cosmos')
@mock.patch('dcos.http.get')
def test_check_version_success(mock_get, mock_cosmos):
    """
    Test _check_3dt_version(), should not fail.
    """

    mock_cosmos().enabled.return_value = True
    m = mock.MagicMock()
    m.json.return_value = {
        'capabilities': [{'name': 'SUPPORT_CLUSTER_REPORT'}]
    }
    mock_get.return_value = m
    main._check_3dt_version()


@mock.patch('dcos.cosmospackage.Cosmos')
@mock.patch('dcos.http.get')
@mock.patch('dcoscli.node.main._do_diagnostics_request')
def test_node_diagnostics_create(mock_do_diagnostics_request, mock_get,
                                 mock_cosmos):
    """
    Test _bundle_create(), should not fail.
    """

    mock_cosmos().enabled.return_value = True
    m = mock.MagicMock()
    m.json.return_value = {
        'capabilities': [{'name': 'SUPPORT_CLUSTER_REPORT'}]
    }
    mock_get.return_value = m
    mock_do_diagnostics_request.return_value = {
        'status': 'OK',
        'extra': {
            'bundle_name': 'bundle.zip'
        }
    }
    main._bundle_create(['10.10.0.1'])
    mock_do_diagnostics_request.assert_called_once_with(
        '/system/health/v1/report/diagnostics/create',
        'POST',
        json={'nodes': ['10.10.0.1']})


@mock.patch('dcos.cosmospackage.Cosmos')
@mock.patch('dcos.http.get')
@mock.patch('dcoscli.node.main._do_diagnostics_request')
def test_node_diagnostics_delete(mock_do_diagnostics_request, mock_get,
                                 mock_cosmos):
    """
    Test _bundle_delete(), should not fail
    """

    mock_cosmos().enabled.return_value = True
    m = mock.MagicMock()
    m.json.return_value = {
        'capabilities': [{'name': 'SUPPORT_CLUSTER_REPORT'}]
    }
    mock_get.return_value = m
    mock_do_diagnostics_request.return_value = {
        'status': 'OK'
    }
    main._bundle_delete('bundle.zip')
    mock_do_diagnostics_request.assert_called_once_with(
        '/system/health/v1/report/diagnostics/delete/bundle.zip',
        'POST'
    )


@mock.patch('dcos.cosmospackage.Cosmos')
@mock.patch('dcos.http.get')
@mock.patch('dcoscli.node.main._do_diagnostics_request')
def test_node_diagnostics_list(mock_do_diagnostics_request, mock_get,
                               mock_cosmos):
    """
    Test _bundle_manage(), should not fail
    """

    mock_cosmos().enabled.return_value = True
    m = mock.MagicMock()
    m.json.return_value = {
        'capabilities': [{'name': 'SUPPORT_CLUSTER_REPORT'}]
    }
    mock_get.return_value = m
    mock_do_diagnostics_request.return_value = {
        '127.0.0.1': [
            {
                'file_name': 'bundle.zip',
                'file_size': 123
            }
        ]
    }

    # _bundle_manage(list_bundles, status, cancel, json)
    main._bundle_manage(True, False, False, False)
    mock_do_diagnostics_request.assert_called_once_with(
        '/system/health/v1/report/diagnostics/list/all',
        'GET'
    )


@mock.patch('dcos.cosmospackage.Cosmos')
@mock.patch('dcos.http.get')
@mock.patch('dcoscli.node.main._do_diagnostics_request')
def test_node_diagnostics_status(mock_do_diagnostics_request, mock_get,
                                 mock_cosmos):
    """
    Test _bundle_manage(), should not fail
    """

    mock_cosmos().enabled.return_value = True
    m = mock.MagicMock()
    m.json.return_value = {
        'capabilities': [{'name': 'SUPPORT_CLUSTER_REPORT'}]
    }
    mock_get.return_value = m
    mock_do_diagnostics_request.return_value = {
        'host1': {
            'prop1': 'value1'
        }
    }

    # _bundle_manage(list_bundles, status, cancel, json)
    main._bundle_manage(False, True, False, False)
    mock_do_diagnostics_request.assert_called_once_with(
        '/system/health/v1/report/diagnostics/status/all',
        'GET'
    )


@mock.patch('dcos.cosmospackage.Cosmos')
@mock.patch('dcos.http.get')
@mock.patch('dcoscli.node.main._do_diagnostics_request')
def test_node_diagnostics_cancel(mock_do_diagnostics_request, mock_get,
                                 mock_cosmos):
    """
    Test _bundle_manage(), should not fail
    """

    mock_cosmos().enabled.return_value = True
    m = mock.MagicMock()
    m.json.return_value = {
        'capabilities': [{'name': 'SUPPORT_CLUSTER_REPORT'}]
    }
    mock_get.return_value = m
    mock_do_diagnostics_request.return_value = {
        'status': 'success'
    }

    # _bundle_manage(list_bundles, status, cancel, json)
    main._bundle_manage(False, False, True, False)
    mock_do_diagnostics_request.assert_called_once_with(
        '/system/health/v1/report/diagnostics/cancel',
        'POST'
    )


@mock.patch('dcos.cosmospackage.Cosmos')
@mock.patch('dcoscli.node.main._do_request')
@mock.patch('dcoscli.node.main._get_bundle_list')
def test_node_diagnostics_download(mock_get_diagnostics_list, mock_do_request,
                                   mock_cosmos):
    mock_cosmos().enabled.return_value = True
    mock_get_diagnostics_list.return_value = [('bundle.zip', 123)]
    main._bundle_download('bundle.zip', None)
    mock_do_request.assert_called_with(
        '/system/health/v1/report/diagnostics/serve/bundle.zip', 'GET',
        stream=True)
