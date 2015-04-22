import os
from functools import wraps

import dcoscli.analytics
import requests
import rollbar
from dcos.api import constants, util
from dcoscli.analytics import _base_properties
from dcoscli.constants import (ROLLBAR_SERVER_POST_KEY,
                               SEGMENT_IO_CLI_ERROR_EVENT,
                               SEGMENT_IO_CLI_EVENT, SEGMENT_IO_WRITE_KEY_DEV,
                               SEGMENT_IO_WRITE_KEY_PROD, SEGMENT_URL)
from dcoscli.main import main

from mock import patch

ANON_ID = 0


def _mock(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        with patch('rollbar.init'), \
                patch('rollbar.report_message'), \
                patch('requests.post'), \
                patch('dcoscli.analytics.session_id'):

            dcoscli.analytics.session_id = ANON_ID
            fn()

    return wrapper


@_mock
def test_no_exc():
    '''Tests that a command which does not raise an exception does not
    report an exception.

    '''

    # args
    args = [util.which('dcos')]
    env = _env_reporting()

    with patch('sys.argv', args), patch.dict(os.environ, env):
        assert main() == 0

        # segment.io
        args, kwargs = requests.post.call_args
        assert args == (SEGMENT_URL,)

        props = _base_properties()
        assert kwargs['json'] == {'anonymousId': ANON_ID,
                                  'event': SEGMENT_IO_CLI_EVENT,
                                  'properties': props}
        assert kwargs['timeout'] == 3

        # rollbar
        assert rollbar.report_message.call_count == 0


@_mock
def test_exc():
    '''Tests that a command which does raise an exception does report an
    exception.

    '''

    # args
    args = [util.which('dcos')]
    env = _env_reporting()

    with patch('sys.argv', args), \
            patch.dict(os.environ, env), \
            patch('dcoscli.analytics._wait_and_capture',
                  return_value=(1, 'Traceback')):
        assert main() == 1

        # segment.io
        _, kwargs = requests.post.call_args_list[1]

        props = _base_properties()
        props['err'] = 'Traceback'
        props['exit_code'] = 1
        assert kwargs['json'] == {'anonymousId': ANON_ID,
                                  'event': SEGMENT_IO_CLI_ERROR_EVENT,
                                  'properties': props}

        props = _base_properties()
        props['exit_code'] = 1
        rollbar.report_message.assert_called_with('Traceback', 'error',
                                                  extra_data=props)


@_mock
def test_config_reporting_false():
    '''Test that "core.reporting = false" blocks exception reporting.'''

    args = [util.which('dcos')]
    env = _env_no_reporting()

    with patch('sys.argv', args), \
            patch.dict(os.environ, env), \
            patch('dcoscli.analytics._wait_and_capture',
                  return_value=(1, 'Traceback')):

        assert main() == 1

        assert rollbar.report_message.call_count == 0
        assert requests.post.call_count == 0


@_mock
def test_production_setting_true():
    '''Test that env var DCOS_PRODUCTION as empty string sends exceptions
    to the 'prod' environment.

    '''

    args = [util.which('dcos')]
    env = _env_reporting()
    env['DCOS_PRODUCTION'] = ''

    with patch('sys.argv', args), patch.dict(os.environ, env):
        assert main() == 0

        _, kwargs = requests.post.call_args_list[0]
        assert kwargs['auth'].username == SEGMENT_IO_WRITE_KEY_PROD

        rollbar.init.assert_called_with(ROLLBAR_SERVER_POST_KEY, 'prod')


@_mock
def test_production_setting_false():
    '''Test that env var DCOS_PRODUCTION=false sends exceptions to
    the 'dev' environment.

    '''

    args = [util.which('dcos')]
    env = _env_reporting()
    env['DCOS_PRODUCTION'] = 'false'

    with patch('sys.argv', args), patch.dict(os.environ, env):
        assert main() == 0

        _, kwargs = requests.post.call_args_list[0]
        assert kwargs['auth'].username == SEGMENT_IO_WRITE_KEY_DEV

        rollbar.init.assert_called_with(ROLLBAR_SERVER_POST_KEY, 'dev')


def _env_reporting():
    path = os.path.join('tests', 'data', 'analytics', 'dcos_reporting.toml')
    return {constants.DCOS_CONFIG_ENV: path}


def _env_no_reporting():
    path = os.path.join('tests', 'data', 'analytics', 'dcos_no_reporting.toml')
    return {constants.DCOS_CONFIG_ENV: path}
