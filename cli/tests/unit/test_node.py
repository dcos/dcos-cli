import mock
import pytest

import dcoscli.node.main as main
from dcos.errors import DCOSException


@mock.patch('dcos.packagemanager.PackageManager')
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


@mock.patch('dcos.packagemanager.PackageManager')
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


@mock.patch('dcos.packagemanager.PackageManager')
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


@mock.patch('dcos.packagemanager.PackageManager')
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


@mock.patch('dcos.packagemanager.PackageManager')
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


@mock.patch('dcos.packagemanager.PackageManager')
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


@mock.patch('dcos.packagemanager.PackageManager')
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


@mock.patch('dcos.packagemanager.PackageManager')
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


@mock.patch('dcos.config.get_config_val')
@mock.patch('dcos.http.get')
@mock.patch('dcoscli.log.dcos_log_enabled')
def test_dcos_log_leader_mesos(mocked_dcos_log_enabked, mocked_http_get,
                               mocked_get_config_val):
    mocked_dcos_log_enabked.return_value = True

    m = mock.MagicMock()
    m.status_code = 200
    mocked_http_get.return_value = m

    mocked_get_config_val.return_value = 'http://127.0.0.1'

    main._dcos_log(False, 10, True, '', None, [])
    mocked_http_get.assert_called_with(
        'http://127.0.0.1/system/v1/leader/mesos/logs/v1/range/?skip_prev=10',
        headers={'Accept': 'text/plain'})


@mock.patch('dcos.config.get_config_val')
@mock.patch('dcos.http.get')
@mock.patch('dcoscli.log.dcos_log_enabled')
def test_dcos_log_leader_marathon(mocked_dcos_log_enabked, mocked_http_get,
                                  mocked_get_config_val):
    mocked_dcos_log_enabked.return_value = True

    m = mock.MagicMock()
    m.status_code = 200
    mocked_http_get.return_value = m

    mocked_get_config_val.return_value = 'http://127.0.0.1'

    main._dcos_log(False, 10, True, '', 'dcos-marathon', [])
    mocked_http_get.assert_called_with(
        'http://127.0.0.1/system/v1/leader/marathon/logs/v1/range/'
        '?skip_prev=10&filter=_SYSTEMD_UNIT:dcos-marathon.service',
        headers={'Accept': 'text/plain'})


@mock.patch('dcoscli.log.follow_logs')
@mock.patch('dcos.config.get_config_val')
@mock.patch('dcos.http.get')
@mock.patch('dcoscli.log.dcos_log_enabled')
def test_dcos_log_stream(mocked_dcos_log_enabked, mocked_http_get,
                         mocked_get_config_val, mocked_follow_logs):
    mocked_dcos_log_enabked.return_value = True

    m = mock.MagicMock()
    m.status_code = 200
    mocked_http_get.return_value = m

    mocked_get_config_val.return_value = 'http://127.0.0.1'

    main._dcos_log(True, 20, False, 'mesos-id', None, [])
    mocked_follow_logs.assert_called_with(
        'http://127.0.0.1/system/v1/agent/mesos-id/logs'
        '/v1/stream/?skip_prev=20')


@mock.patch('dcoscli.log.follow_logs')
@mock.patch('dcos.config.get_config_val')
@mock.patch('dcos.http.get')
@mock.patch('dcoscli.log.dcos_log_enabled')
def test_dcos_log_filters(mocked_dcos_log_enabked, mocked_http_get,
                          mocked_get_config_val, mocked_follow_logs):
    mocked_dcos_log_enabked.return_value = True

    m = mock.MagicMock()
    m.status_code = 200
    mocked_http_get.return_value = m

    mocked_get_config_val.return_value = 'http://127.0.0.1'

    main._dcos_log(True, 20, False, 'mesos-id', 'dcos-mesos-master',
                   ['key1:value1', 'key2:value2'])

    mocked_follow_logs.assert_called_with(
        'http://127.0.0.1/system/v1/agent/mesos-id/logs/v1/stream/'
        '?skip_prev=20&filter=key1:value1&filter=key2:value2&'
        'filter=_SYSTEMD_UNIT:dcos-mesos-master.service')


@mock.patch('dcos.config.get_config_val')
@mock.patch('dcoscli.node.main._get_slave_ip')
@mock.patch('dcos.http.get')
def test_list_components(mocked_get, mocked_get_slave_ip,
                         mocked_get_config_val):
    m = mock.MagicMock()
    m.json.return_value = {
        'units': [
            {
                'id': 'dcos-component.service',
            }
        ]
    }
    mocked_get.return_value = m
    mocked_get_slave_ip.return_value = '127.0.0.1'
    mocked_get_config_val.return_value = 'http://10.10.10.10'
    main._list_components(None, 'slave-id', False)
    mocked_get.assert_called_with(
        'http://10.10.10.10/system/health/v1/nodes/127.0.0.1/units')


@mock.patch('dcos.config.get_config_val')
@mock.patch('dcos.mesos.MesosDNSClient')
@mock.patch('dcos.http.get')
def test_list_components_leader(mocked_get, mocked_dns,
                                mocked_get_config_val):
    m = mock.MagicMock()
    m.json.return_value = {
        'units': [
            {
                'id': 'dcos-component.service',
            }
        ]
    }
    mocked_dns().hosts.return_value = [{'ip': '10.10.0.1'}]
    mocked_get_config_val.return_value = 'http://10.10.10.10'

    mocked_get.return_value = m
    main._list_components(True, False, False)
    mocked_get.assert_called_with(
        'http://10.10.10.10/system/health/v1/nodes/10.10.0.1/units')
