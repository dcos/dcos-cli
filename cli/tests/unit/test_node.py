import dcoscli.node.main as main
from dcos.errors import DCOSException

import mock
import pytest


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
        'DC/OS backend does not support snapshot capabilities in this version.'
        ' Must be DC/OS >= 1.8')


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
@mock.patch('dcoscli.node.main._do_snapshot_request')
def test_node_snapshot_create(mock_do_snapshot_request, mock_get, mock_cosmos):
    """
    Test _snapshot_create(), should not fail.
    """

    mock_cosmos().enabled.return_value = True
    m = mock.MagicMock()
    m.json.return_value = {
        'capabilities': [{'name': 'SUPPORT_CLUSTER_REPORT'}]
    }
    mock_get.return_value = m
    mock_do_snapshot_request.return_value = {
        'status': 'OK',
        'extra': {
            'snapshot_name': 'snapshot.zip'
        }
    }
    main._snapshot_create(['10.10.0.1'])
    mock_do_snapshot_request.assert_called_once_with(
        '/system/health/v1/report/snapshot/create',
        'POST',
        json={'nodes': ['10.10.0.1']})


@mock.patch('dcos.cosmospackage.Cosmos')
@mock.patch('dcos.http.get')
@mock.patch('dcoscli.node.main._do_snapshot_request')
def test_node_snapshot_delete(mock_do_snapshot_request, mock_get, mock_cosmos):
    """
    Test _snapshot_delete(), should not fail
    """

    mock_cosmos().enabled.return_value = True
    m = mock.MagicMock()
    m.json.return_value = {
        'capabilities': [{'name': 'SUPPORT_CLUSTER_REPORT'}]
    }
    mock_get.return_value = m
    mock_do_snapshot_request.return_value = {
        'status': 'OK'
    }
    main._snapshot_delete('snapshot.zip')
    mock_do_snapshot_request.assert_called_once_with(
        '/system/health/v1/report/snapshot/delete/snapshot.zip',
        'POST'
    )


@mock.patch('dcos.cosmospackage.Cosmos')
@mock.patch('dcos.http.get')
@mock.patch('dcoscli.node.main._do_snapshot_request')
def test_node_snapshot_list(mock_do_snapshot_request, mock_get, mock_cosmos):
    """
    Test _snapshot_manage(), should not fail
    """

    mock_cosmos().enabled.return_value = True
    m = mock.MagicMock()
    m.json.return_value = {
        'capabilities': [{'name': 'SUPPORT_CLUSTER_REPORT'}]
    }
    mock_get.return_value = m
    mock_do_snapshot_request.return_value = {
        '127.0.0.1': [
            {
                'file_name': 'snapshot.zip',
                'file_size': 123
            }
        ]
    }

    # _snapshot_manage(list_snapshots, status, cancel, json)
    main._snapshot_manage(True, False, False, False)
    mock_do_snapshot_request.assert_called_once_with(
        '/system/health/v1/report/snapshot/list/all',
        'GET'
    )


@mock.patch('dcos.cosmospackage.Cosmos')
@mock.patch('dcos.http.get')
@mock.patch('dcoscli.node.main._do_snapshot_request')
def test_node_snapshot_status(mock_do_snapshot_request, mock_get, mock_cosmos):
    """
    Test _snapshot_manage(), should not fail
    """

    mock_cosmos().enabled.return_value = True
    m = mock.MagicMock()
    m.json.return_value = {
        'capabilities': [{'name': 'SUPPORT_CLUSTER_REPORT'}]
    }
    mock_get.return_value = m
    mock_do_snapshot_request.return_value = {
        'host1': {
            'prop1': 'value1'
        }
    }

    # _snapshot_manage(list_snapshots, status, cancel, json)
    main._snapshot_manage(False, True, False, False)
    mock_do_snapshot_request.assert_called_once_with(
        '/system/health/v1/report/snapshot/status/all',
        'GET'
    )


@mock.patch('dcos.cosmospackage.Cosmos')
@mock.patch('dcos.http.get')
@mock.patch('dcoscli.node.main._do_snapshot_request')
def test_node_snapshot_cancel(mock_do_snapshot_request, mock_get, mock_cosmos):
    """
    Test _snapshot_manage(), should not fail
    """

    mock_cosmos().enabled.return_value = True
    m = mock.MagicMock()
    m.json.return_value = {
        'capabilities': [{'name': 'SUPPORT_CLUSTER_REPORT'}]
    }
    mock_get.return_value = m
    mock_do_snapshot_request.return_value = {
        'status': 'success'
    }

    # _snapshot_manage(list_snapshots, status, cancel, json)
    main._snapshot_manage(False, False, True, False)
    mock_do_snapshot_request.assert_called_once_with(
        '/system/health/v1/report/snapshot/cancel',
        'POST'
    )


@mock.patch('dcos.cosmospackage.Cosmos')
@mock.patch('dcoscli.node.main._do_request')
@mock.patch('dcoscli.node.main._get_snapshots_list')
def test_node_snapshot_download(mock_get_snapshot_list, mock_do_request,
                                mock_cosmos):
    mock_cosmos().enabled.return_value = True
    mock_get_snapshot_list.return_value = [('snap.zip', 123)]
    main._snapshot_download('snap.zip', None)
    mock_do_request.assert_called_with(
        '/system/health/v1/report/snapshot/serve/snap.zip', 'GET',
        stream=True)
