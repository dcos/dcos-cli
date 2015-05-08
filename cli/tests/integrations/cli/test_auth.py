import os
import webbrowser

from dcos import auth, constants, util
from dcoscli.main import main

import pytest
from mock import Mock, patch


@pytest.skip('Test TC')
def test_no_browser_auth():
    webbrowser.get = Mock(side_effect=webbrowser.Error())
    with patch('webbrowser.open') as op:
        _mock_dcos_run([util.which('dcos')], False)
        assert op.call_count == 0


@pytest.skip('Test TC')
def test_when_authenticated():
    with patch('dcos.auth.force_auth'):

        _mock_dcos_run([util.which('dcos')], True)
        assert auth.force_auth.call_count == 0


@pytest.skip('Test TC')
def test_anonymous_login():
    with patch('six.moves.input',
               return_value=''), patch('uuid.uuid1',
                                       return_value='anonymous@email'):

        assert _mock_dcos_run([util.which('dcos'),
                               'help'], False) == 0
        assert _mock_dcos_run([util.which('dcos'), 'config',
                               'show', 'core.email'], False) == 0
        assert _mock_dcos_run([util.which('dcos'), 'config',
                               'unset', 'core.email'], False) == 0


def _mock_dcos_run(args, authenticated=True):
    env = _config_with_credentials() if authenticated else \
        _config_without_credentials()
    with patch('sys.argv', args), patch.dict(os.environ, env):
        return main()


def _config_with_credentials():
    return {constants.DCOS_CONFIG_ENV: os.path.join(
        'tests', 'data', 'auth', 'dcos_with_credentials.toml')}


def _config_without_credentials():
    return {constants.DCOS_CONFIG_ENV: os.path.join(
        'tests', 'data', 'auth', 'dcos_without_credentials.toml')}
