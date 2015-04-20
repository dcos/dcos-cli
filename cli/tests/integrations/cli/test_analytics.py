
import json
import os

import dcoscli
import rollbar
from dcos.api import config, constants
from dcoscli.constants import ROLLBAR_SERVER_POST_KEY
from dcoscli.main import main

from mock import Mock, patch


def test_no_exc():
    '''Tests that a command which does not raise an exception does not
    report an exception.

    '''

    args = ['dcos']
    exit_code = _mock_analytics_run(args)

    assert rollbar.report_message.call_count == 0
    assert exit_code == 0


def test_exc():
    '''Tests that a command which does raise an exception does report an
    exception.

    '''

    args = ['dcos']
    exit_code = _mock_analytics_run_exc(args)

    props = _analytics_properties(args, exit_code=1)
    rollbar.report_message.assert_called_with('Traceback', 'error',
                                              extra_data=props)
    assert exit_code == 1


def test_config_reporting_false():
    '''Test that "core.reporting = false" blocks exception reporting.'''

    args = ['dcos']
    exit_code = _mock_analytics_run_exc(args, False)

    assert rollbar.report_message.call_count == 0
    assert exit_code == 1


def test_production_setting_true():
    '''Test that env var DCOS_PRODUCTION=true sends exceptions to
    the 'prod' environment.

    '''

    args = ['dcos']
    with patch.dict(os.environ, {'DCOS_PRODUCTION': 'true'}):
        _mock_analytics_run(args)
        rollbar.init.assert_called_with(ROLLBAR_SERVER_POST_KEY, 'prod')


def test_production_setting_false():
    '''Test that env var DCOS_PRODUCTION=false sends exceptions to
    the 'dev' environment.

    '''

    args = ['dcos']
    with patch.dict(os.environ, {'DCOS_PRODUCTION': 'false'}):
        _mock_analytics_run(args)
        rollbar.init.assert_called_with(ROLLBAR_SERVER_POST_KEY, 'dev')


def _config_path_reporting():
    return os.path.join('tests', 'data', 'analytics', 'dcos_reporting.toml')


def _config_path_no_reporting():
    return os.path.join('tests', 'data', 'analytics', 'dcos_no_reporting.toml')


def _env_reporting():
    return {constants.DCOS_CONFIG_ENV: _config_path_reporting()}


def _env_no_reporting():
    return {constants.DCOS_CONFIG_ENV: _config_path_no_reporting()}


def _mock_analytics_run_exc(args, reporting=True):
    dcoscli.main._wait_and_capture = Mock(return_value=(1, 'Traceback'))
    return _mock_analytics_run(args, reporting)


def _mock_analytics_run(args, reporting=True):
    env = _env_reporting() if reporting else _env_no_reporting()

    with patch('sys.argv', args), patch.dict(os.environ, env):
        rollbar.init = Mock()
        rollbar.report_message = Mock()
        return main()


def _analytics_properties(sysargs, **kwargs):
    conf = config.load_from_path(_config_path_reporting())
    defaults = {'cmd': ' '.join(sysargs),
                'exit_code': 0,
                'dcoscli.version': dcoscli.version,
                'config': json.dumps(list(conf.property_items()))}
    defaults.update(kwargs)
    return defaults
