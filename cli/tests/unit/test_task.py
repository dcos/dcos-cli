import pytest
from mock import MagicMock, patch

from dcos import mesos
from dcos.errors import DCOSException
from dcoscli.log import is_success, log_files
from dcoscli.metrics import EmptyMetricsException
from dcoscli.task.main import _dcos_log, _dcos_log_v2, _metrics, main

from .common import assert_mock


# metrics_messages is a minimal fixture for mocking non-empty API responses
metrics_message = {
    'datapoints': [
        {
            'name': 'statsd_tester.time.uptime',
            'value': 1234,
        }
    ]
}


@patch('dcos.config.get_config')
def test_log_master_unavailable(config_mock):
    config_mock.return_value = {'core.dcos_url': 'foo'}

    """ Test master's state.json being unavailable """
    client = mesos.DCOSClient()
    client.get_master_state = _mock_exception()

    with patch('dcos.mesos.DCOSClient', return_value=client):
        args = ['task', 'log', '_']
        assert_mock(main, args, returncode=1, stderr=(b"exception\n"))


def test_log_no_tasks():
    """ Test slave's state.json being unavailable """
    with patch('dcos.mesos.DCOSClient.get_master_state', return_value={}), \
            patch('dcos.mesos.Master.tasks', return_value={}):

        stderr = b"""No matching tasks. Exiting.\n"""
        args = ['task', 'log', 'test-app-1']
        assert_mock(main, args, returncode=1, stderr=stderr)


def test_task_exact_match():
    """Test a task gets returned if it is an exact match, even if
    it is a substring of another task.
    """
    with patch('dcos.mesos.Master.slaves',
               return_value=[{"id": "foo"}, {"id": "foobar"}]):
        master = mesos.Master(None)
        assert master.slave("foo") == {"id": "foo"}


def test_log_file_unavailable():
    """ Test a file's read.json being unavailable """
    files = [mesos.MesosFile('bogus')]
    files[0].read = _mock_exception('exception')

    with pytest.raises(DCOSException) as e:
        log_files(files, True, 10)

    msg = "No files exist. Exiting."
    assert e.exconly().split(':', 1)[1].strip() == msg


def _mock_exception(contents='exception'):
    return MagicMock(side_effect=DCOSException(contents))


@patch('dcoscli.log.follow_logs')
@patch('dcos.config.get_config_val')
def test_dcos_log_v2(mocked_get_config_val, mocked_follow_logs):
    mocked_get_config_val.return_value = 'http://127.0.0.1'

    task = {'id': 'test-task'}

    _dcos_log_v2(True, [task], 10, 'stdout')
    mocked_follow_logs.assert_called_with(
        'http://127.0.0.1/system/v1/logs/v2/task/test-task/file/stdout?'
        'cursor=END&skip=-10')


@patch('dcos.http.get')
@patch('dcos.config.get_config_val')
def test_dcos_log(mocked_get_config_val, mocked_http_get):
    mocked_get_config_val.return_value = 'http://127.0.0.1'

    m = MagicMock()
    m.status_code = 200
    mocked_http_get.return_value = m

    executor_info = {
        'tasks': [
            {
                'container': 'container1',
                'state': 'TASK_RUNNING',
                'statuses': [
                    {
                        'state': 'TASK_RUNNING',
                        'container_status': {
                            'container_id': {
                                'value': 'child-123',
                                'parent': {
                                    'value': 'parent-456'
                                }
                            }
                        }
                    }
                ],
                'slave_id': 'slave-123',
                'framework_id': 'framework-123',
                'id': 'id-123'
            }
        ]
    }

    task = MagicMock
    task.executor = lambda: executor_info
    _dcos_log(False, [task], 10, 'stdout', False)
    mocked_http_get.assert_called_with(
        'http://127.0.0.1/system/v1/agent/slave-123/logs/v1/range/framework/'
        'framework-123/executor/id-123/container/parent-456.child-123'
        '?skip_prev=10&filter=STREAM:STDOUT',
        headers={'Accept': 'text/plain'},
        is_success=is_success)


@patch('dcoscli.log.follow_logs')
@patch('dcos.http.get')
@patch('dcos.config.get_config_val')
def test_dcos_log_stream(mocked_get_config_val, mocked_http_get,
                         mocked_follow_logs):
    mocked_get_config_val.return_value = 'http://127.0.0.1'

    m = MagicMock()
    m.status_code = 200
    mocked_http_get.return_value = m

    executor_info = {
        'tasks': [
            {
                'container': 'container1',
                'state': 'TASK_RUNNING',
                'statuses': [
                    {
                        'state': 'TASK_RUNNING',
                        'container_status': {
                            'container_id': {
                                'value': 'child-123',
                            }
                        }
                    }
                ],
                'slave_id': 'slave-123',
                'framework_id': 'framework-123',
                'id': 'id-123'
            }
        ]
    }

    task = MagicMock
    task.executor = lambda: executor_info
    _dcos_log(True, [task], 10, 'stderr', False)
    mocked_follow_logs.assert_called_with(
        'http://127.0.0.1/system/v1/agent/slave-123/logs/v1/'
        'stream/framework/framework-123/executor/id-123/container/'
        'child-123?skip_prev=10&filter=STREAM:STDERR')


@patch('dcos.http.get')
@patch('dcos.mesos.get_master')
@patch('dcos.config.get_config_val')
def test_dcos_task_metrics_agent_details(mocked_get_config_val,
                                         mocked_get_master,
                                         mocked_http_get):
    mocked_get_config_val.return_value = 'http://127.0.0.1'

    mock_http_response = MagicMock()
    mock_http_response.status_code = 200
    mock_http_response.json = lambda: metrics_message
    mocked_http_get.return_value = mock_http_response

    mock_master = MagicMock()
    mock_master.task = lambda _: {'slave_id': 'slave_id'}
    mock_master.get_container_id = lambda _: {
        'parent': {},
        'value': 'container_id'
    }
    mocked_get_master.return_value = mock_master

    _metrics(True, 'task_id', False)

    # Metrics should query both endpoints
    mocked_http_get.assert_any_call('http://127.0.0.1/system/v1/agent/'
                                    'slave_id/metrics/v0/containers/'
                                    'container_id/app')
    mocked_http_get.assert_any_call('http://127.0.0.1/system/v1/agent/'
                                    'slave_id/metrics/v0/containers/'
                                    'container_id')


@patch('dcos.http.get')
@patch('dcos.mesos.get_master')
@patch('dcos.config.get_config_val')
def test_dcos_task_metrics_agent_missing_container(
    mocked_get_config_val, mocked_get_master, mocked_http_get
):
    mocked_get_config_val.return_value = 'http://127.0.0.1'

    mock_container_response = MagicMock()
    mock_container_response.status_code = 204
    mock_app_response = MagicMock()
    mock_app_response.status_code = 200
    mock_app_response.json = lambda: metrics_message

    mocked_http_get.side_effect = [mock_container_response, mock_app_response]

    mock_master = MagicMock()
    mock_master.task = lambda _: {'slave_id': 'slave_id'}
    mock_master.get_container_id = lambda _: {
        'parent': {},
        'value': 'container_id'
    }
    mocked_get_master.return_value = mock_master

    _metrics(True, 'task_id', False)


@patch('dcos.http.get')
@patch('dcos.mesos.get_master')
@patch('dcos.config.get_config_val')
def test_dcos_task_metrics_agent_missing_app(
    mocked_get_config_val, mocked_get_master, mocked_http_get
):
    mocked_get_config_val.return_value = 'http://127.0.0.1'

    mock_container_response = MagicMock()
    mock_container_response.status_code = 200
    mock_container_response.json = lambda: metrics_message
    mock_app_response = MagicMock()
    mock_app_response.status_code = 204
    mocked_http_get.side_effect = [mock_container_response, mock_app_response]

    mock_master = MagicMock()
    mock_master.task = lambda _: {'slave_id': 'slave_id'}
    mock_master.get_container_id = lambda _: {
        'parent': {},
        'value': 'container_id'
    }
    mocked_get_master.return_value = mock_master

    _metrics(True, 'task_id', False)


@patch('dcos.http.get')
@patch('dcos.mesos.get_master')
@patch('dcos.config.get_config_val')
def test_dcos_task_metrics_agent_missing_both(
    mocked_get_config_val, mocked_get_master, mocked_http_get
):
    mocked_get_config_val.return_value = 'http://127.0.0.1'

    mock_response = MagicMock()
    mock_response.status_code = 204
    mocked_http_get.return_value = mock_response

    mock_master = MagicMock()
    mock_master.task = lambda _: {'slave_id': 'slave_id'}
    mock_master.get_container_id = lambda _: {
        'parent': {},
        'value': 'container_id'
    }
    mocked_get_master.return_value = mock_master

    with pytest.raises(EmptyMetricsException):
        _metrics(True, 'task_id', False)


@patch('dcos.http.get')
@patch('dcos.mesos.get_master')
@patch('dcos.config.get_config_val')
def test_dcos_task_metrics_agent_missing_slave(mocked_get_config_val,
                                               mocked_get_master,
                                               mocked_http_get):
    mocked_get_config_val.return_value = 'http://127.0.0.1'

    mock_http_response = MagicMock()
    mock_http_response.status_code = 200
    mocked_http_get.return_value = mock_http_response

    mock_master = MagicMock()
    mock_master.task = lambda _: {}
    mocked_get_master.return_value = mock_master

    # Should a task not have a slave ID, expect an error
    with pytest.raises(DCOSException):
        _metrics(True, 'task_id', False)


def test_task_fault_domain():
    fd = {
        'domain': {
            'fault_domain': {
                'region': {
                    'name': 'us-east-1'
                },
                'zone': {
                    'name': 'us-east-1a'
                }
            }
        }
    }

    state = {'prop1': 'value1'}
    state.update(fd)
    slave = mesos.Slave(state, None, None)
    assert slave.fault_domain() == fd

    slave = mesos.Slave({}, None, None)
    assert not slave.fault_domain()


@patch('dcos.http.get')
def test_dcos_log_v2_500(mocked_http_get):
    mock_http_response = MagicMock()
    mock_http_response.status_code = 500
    mock_http_response.text = "foo bar error"
    mocked_http_get.return_value = mock_http_response

    task = {'id': 'test-task'}
    with pytest.raises(DCOSException) as excinfo:
        _dcos_log_v2(False, [task], 10, 'stdout')
    assert 'foo bar error' in str(excinfo.value)
