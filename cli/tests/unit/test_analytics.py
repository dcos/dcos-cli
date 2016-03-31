import os
from functools import wraps

import dcoscli.analytics
import rollbar
from dcos import constants, http
from dcoscli.constants import SEGMENT_URL
from dcoscli.main import main
from dcoscli.subcommand import SubcommandMain

from mock import patch

from .common import mock_called_some_args

ANON_ID = 0
USER_ID = 'test@mail.com'


def _mock(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        with patch('rollbar.init'), \
                patch('rollbar.report_message'), \
                patch('dcos.http.post'), \
                patch('dcos.http.get'), \
                patch('dcoscli.analytics.session_id'):

            dcoscli.analytics.session_id = ANON_ID
            fn()

    return wrapper


@_mock
def test_config_set():
    argv = ['set', 'core.email', 'test@mail.com']

    config_thread = SubcommandMain("config", argv)
    exitcode, err = config_thread.run_and_capture()
    assert exitcode == 0
    assert err is None

    # segment.io
    assert mock_called_some_args(http.post,
                                 '{}/identify'.format(SEGMENT_URL),
                                 json={'userId': 'test@mail.com'},
                                 timeout=(1, 1))


@_mock
def test_cluster_id_not_sent_on_config_call():
    """Tests that cluster_id is not sent to segment.io on call to config
    subcommand
    """

    args = ['dcos', 'config', 'show']

    with patch('sys.argv', args), \
            patch('dcos.mesos.DCOSClient.metadata') as get_cluster_id:
        assert main() == 0

        assert get_cluster_id.call_count == 0


@_mock
def test_no_exc():
    '''Tests that a command which does not raise an exception does not
    report an exception.

    '''

    args = ['dcos']
    env = _env_reporting()
    version = 'release'

    with patch('sys.argv', args), \
            patch.dict(os.environ, env), \
            patch('dcoscli.version', version):
        assert main() == 0

        assert rollbar.report_message.call_count == 0


@_mock
def test_exc():
    '''Tests that a command which does raise an exception does report an
    exception.

    '''

    args = ['dcos']
    env = _env_reporting()
    version = 'release'
    with patch('sys.argv', args), \
            patch('dcoscli.version', version), \
            patch.dict(os.environ, env), \
            patch('dcoscli.subcommand.SubcommandMain.run_and_capture',
                  return_value=(1, "Traceback")), \
            patch('dcoscli.analytics._segment_track') as track:

        assert main() == 1
        assert track.call_count == 2
        assert rollbar.report_message.call_count == 1


def _env_reporting():
    path = os.path.join('tests', 'data', 'analytics', 'dcos_reporting.toml')
    return {constants.DCOS_CONFIG_ENV: path}


@_mock
def test_config_reporting_false():
    '''Test that "core.reporting = false" blocks exception reporting.'''

    args = ['dcos']
    env = _env_no_reporting()
    version = 'release'

    with patch('sys.argv', args), \
            patch('dcoscli.version', version), \
            patch.dict(os.environ, env), \
            patch('dcoscli.subcommand.SubcommandMain.run_and_capture',
                  return_value=(1, "Traceback")), \
            patch('dcoscli.analytics._segment_track') as track:

        assert main() == 1
        assert track.call_count == 0


def _env_no_reporting():
    path = os.path.join('tests', 'data', 'analytics', 'dcos_no_reporting.toml')
    return {constants.DCOS_CONFIG_ENV: path}
