import json
import os
import shutil
import sys

from .common import setup_cluster, exec_cmd, default_cluster, default_cluster_with_plugins  # noqa: F401


def test_plugin_list(default_cluster_with_plugins):
    code, out, err = exec_cmd(['dcos', 'plugin', 'list'])
    assert code == 0
    assert err == ''

    lines = out.splitlines()
    assert len(lines) == 3

    # heading
    assert lines[0].split() == ['NAME', 'COMMANDS']

    dcos_core_cli = lines[1].split()
    assert dcos_core_cli[0] == 'dcos-core-cli'
    assert dcos_core_cli[1:] == ['job', 'marathon', 'node', 'package', 'service', 'task']

    dcos_enterprise_cli = lines[2].split()
    assert dcos_enterprise_cli[0] == 'dcos-enterprise-cli'
    assert dcos_enterprise_cli[1:] == ['backup', 'license', 'security']


def test_plugin_invocation(default_cluster):
    _install_test_plugin()

    args = ['dcos', 'test', 'arg1', 'arg2']
    code, out, err = exec_cmd(args)
    assert code == 0
    out = json.loads(out)

    assert out['args'][1:] == args[1:]

    executable_path = out['env'].get('DCOS_CLI_EXECUTABLE_PATH')
    if sys.platform == 'win32':
        # On Windows, "shutil.which" normalizes the path so the drive letter is not present.
        # This removes it from the value returned by the test plugin too.
        (_, executable_path) = os.path.splitdrive(executable_path)
        expected_executable_path = shutil.which("dcos.exe")
    else:
        expected_executable_path = shutil.which("dcos")
    assert executable_path == expected_executable_path

    assert out['env'].get('DCOS_URL') == default_cluster['dcos_url']
    assert out['env'].get('DCOS_ACS_TOKEN') == default_cluster['acs_token']


def test_plugin_invocation_tls():
    with setup_cluster(scheme='https'):
        _install_test_plugin()

        code, out, _ = exec_cmd(['dcos', 'config', 'show', 'core.ssl_verify'])
        assert code == 0
        ca_path = out.rstrip()

        code, out, err = exec_cmd(['dcos', 'test'])
        assert code == 0
        out = json.loads(out)

        assert out['env'].get('DCOS_TLS_INSECURE') is None
        assert out['env'].get('DCOS_TLS_CA_PATH') == ca_path

        code, _, _ = exec_cmd(['dcos', 'config', 'set', 'core.ssl_verify', 'False'])
        assert code == 0

        code, out, err = exec_cmd(['dcos', 'test'])
        assert code == 0
        out = json.loads(out)

        assert out['env'].get('DCOS_TLS_INSECURE') == '1'
        assert out['env'].get('DCOS_TLS_CA_PATH') is None

    with setup_cluster(scheme='http'):
        _install_test_plugin()

        code, out, err = exec_cmd(['dcos', 'test'])
        assert code == 0
        out = json.loads(out)

        assert out['env'].get('DCOS_TLS_INSECURE') == '1'
        assert out['env'].get('DCOS_TLS_CA_PATH') is None


def test_plugin_verbosity(default_cluster):
    _install_test_plugin()

    fixtures = [
        {
            'cmd': ['dcos', 'test'],
            'DCOS_VERBOSITY': None,
            'DCOS_LOG_LEVEL': None,
        },
        {
            'cmd': ['dcos', '-v', 'test'],
            'DCOS_VERBOSITY': '1',
            'DCOS_LOG_LEVEL': 'info',
        },
        {
            'cmd': ['dcos', '-vv', 'test'],
            'DCOS_VERBOSITY': '2',
            'DCOS_LOG_LEVEL': 'debug',
        },
        {
            'cmd': ['dcos', '--log-level=debug', 'test'],
            'DCOS_VERBOSITY': '2',
            'DCOS_LOG_LEVEL': 'debug',
        },
        {
            'cmd': ['dcos', '--debug', 'test'],
            'DCOS_VERBOSITY': '2',
            'DCOS_LOG_LEVEL': 'debug',
        },
    ]

    for fixture in fixtures:
        code, out, _ = exec_cmd(fixture['cmd'])
        assert code == 0
        assert code == 0
        out = json.loads(out)

        assert out['args'][1:] == ['test']
        assert out['env'].get('DCOS_VERBOSITY') == fixture['DCOS_VERBOSITY']
        assert out['env'].get('DCOS_LOG_LEVEL') == fixture['DCOS_LOG_LEVEL']


def _install_test_plugin():
    code, out, err = exec_cmd(['dcos', 'plugin', 'add', _test_plugin_path()])
    assert code == 0
    assert err == ''
    assert out == ''


def _test_plugin_path():
    file = 'dcos-test.exe' if sys.platform == 'win32' else 'dcos-test'
    return os.path.join(_plugin_dir('dcos-test'), sys.platform, file)


def _plugin_dir(name):
    return os.path.join(os.path.dirname(__file__), 'fixtures', 'plugins', name)
