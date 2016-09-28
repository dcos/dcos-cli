import pytest
from mock import MagicMock, patch

from dcos import mesos
from dcos.errors import DCOSException
from dcoscli.log import log_files
from dcoscli.task.main import main

from .common import assert_mock


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
