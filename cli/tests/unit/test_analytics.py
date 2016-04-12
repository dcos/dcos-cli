import json
import os
from functools import wraps

import dcoscli.analytics
import rollbar
from dcos import constants
from dcoscli.main import main

from mock import patch


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
def test_cluster_id_not_sent_on_config_call():
    """Tests that cluster_id is not sent to segment.io on call to config
    subcommand
    """

    args = ['dcos', 'config', 'show']

    with patch('sys.argv', args), \
            patch('dcos.mesos.DCOSClient.metadata') as get_cluster_id:
        assert main() == 0

        assert get_cluster_id.call_count == 0


def test_dont_send_acs_token():
    """Tests that we donn't send acs token"""

    args = ['dcos', 'help']
    env = _env_reporting()
    version = 'release'

    with patch('sys.argv', args), \
            patch.dict(os.environ, env), \
            patch('dcoscli.version', version):
        to_send = dcoscli.analytics._base_properties()
        config_to_send = json.loads(to_send.get("config"))
        assert "core.dcos_acs_token" not in config_to_send


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


def test_command_always_returns_str():
    """Test that _command() returns str even if not subcommand specified"""
    args = ['dcos']
    with patch('sys.argv', args):
        assert dcoscli.analytics._command() == ""
