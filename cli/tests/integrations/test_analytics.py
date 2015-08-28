import os
from functools import wraps

import dcoscli.analytics
import rollbar
from dcos import constants, http, util
from dcoscli.analytics import _base_properties
from dcoscli.config.main import main as config_main
from dcoscli.constants import (SEGMENT_IO_CLI_ERROR_EVENT,
                               SEGMENT_IO_CLI_EVENT, SEGMENT_URL)
from dcoscli.main import main

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
                patch('dcoscli.analytics.session_id'):

            dcoscli.analytics.session_id = ANON_ID
            fn()

    return wrapper


@_mock
def test_config_set():
    '''Tests that a `dcos config set core.email <email>` makes a
    segment.io identify call'''

    args = [util.which('dcos'), 'config', 'set', 'core.email', 'test@mail.com']
    env = _env_reporting()

    with patch('sys.argv', args), patch.dict(os.environ, env):
        assert config_main() == 0

        # segment.io
        assert mock_called_some_args(http.post,
                                     '{}/identify'.format(SEGMENT_URL),
                                     json={'userId': 'test@mail.com'},
                                     timeout=(1, 1))


@_mock
def test_no_exc():
    '''Tests that a command which does not raise an exception does not
    report an exception.

    '''

    args = [util.which('dcos')]
    env = _env_reporting()
    version = 'release'

    with patch('sys.argv', args), \
            patch.dict(os.environ, env), \
            patch('dcoscli.version', version):
        assert main() == 0

        # segment.io
        data = {'userId': USER_ID,
                'event': SEGMENT_IO_CLI_EVENT,
                'properties': _base_properties()}
        assert mock_called_some_args(http.post,
                                     '{}/track'.format(SEGMENT_URL),
                                     json=data,
                                     timeout=(1, 1))

        # rollbar
        assert rollbar.report_message.call_count == 0


@_mock
def test_exc():
    '''Tests that a command which does raise an exception does report an
    exception.

    '''

    args = [util.which('dcos')]
    env = _env_reporting()
    version = 'release'
    with patch('sys.argv', args), \
            patch('dcoscli.version', version), \
            patch.dict(os.environ, env), \
            patch('dcoscli.analytics.wait_and_capture',
                  return_value=(1, 'Traceback')):
        assert main() == 1

        # segment.io
        props = _base_properties()
        props['err'] = 'Traceback'
        props['exit_code'] = 1
        data = {'userId': USER_ID,
                'event': SEGMENT_IO_CLI_ERROR_EVENT,
                'properties': props}

        assert mock_called_some_args(http.post,
                                     '{}/track'.format(SEGMENT_URL),
                                     json=data,
                                     timeout=(1, 1))

        # rollbar
        props = _base_properties()
        props['exit_code'] = 1
        props['stderr'] = 'Traceback'
        rollbar.report_message.assert_called_with('Traceback', 'error',
                                                  extra_data=props)


@_mock
def test_config_reporting_false():
    '''Test that "core.reporting = false" blocks exception reporting.'''

    args = [util.which('dcos')]
    env = _env_no_reporting()
    version = 'release'

    with patch('sys.argv', args), \
            patch('dcoscli.version', version), \
            patch.dict(os.environ, env), \
            patch('dcoscli.analytics.wait_and_capture',
                  return_value=(1, 'Traceback')):

        assert main() == 1

        assert rollbar.report_message.call_count == 0
        assert http.post.call_count == 0


def _env_reporting():
    path = os.path.join('tests', 'data', 'analytics', 'dcos_reporting.toml')
    return {constants.DCOS_CONFIG_ENV: path}


def _env_no_reporting():
    path = os.path.join('tests', 'data', 'analytics', 'dcos_no_reporting.toml')
    return {constants.DCOS_CONFIG_ENV: path}
