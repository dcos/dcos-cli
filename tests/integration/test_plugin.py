import json
import os
import shutil
import sys

from concurrent import futures

import pytest

from .common import setup_cluster, exec_cmd, default_cluster  # noqa: F401


def test_plugin_list(default_cluster):
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
    assert 'backup' in dcos_enterprise_cli[1:]
    assert 'license' in dcos_enterprise_cli[1:]
    assert 'security' in dcos_enterprise_cli[1:]
    assert len(dcos_enterprise_cli[1:]) == 3


def test_plugin_install_invalid_test(default_cluster):
    filename = os.path.splitext(os.path.basename(__file__))[0]
    code, out, err = exec_cmd(['dcos', 'plugin', 'add', __file__])
    assert code == 1
    assert err == 'Error: {} has no commands\n'.format(filename)
    assert out == ''


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


@pytest.mark.skipif(sys.platform == 'win32',
                    reason='Not yet concurrent-safe on Windows (DCOS_OSS-4843)')
def test_plugin_concurrent_invocation(default_cluster):
    _install_test_plugin()

    with futures.ThreadPoolExecutor() as pool:
        cmds = [pool.submit(exec_cmd, ['dcos', 'test', 'arg']) for _ in range(50)]

        completed, _ = futures.wait(cmds, timeout=30)
        assert len(completed) == 50

        for cmd in completed:
            code, out, err = cmd.result()
            assert code == 0, out + err


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


def test_plugin_exit_code(default_cluster):
    _install_test_plugin()

    code, _, _ = exec_cmd(['dcos', 'test', 'exit', '43'])
    assert code == 43


def test_plugin_remove(default_cluster):
    _install_test_plugin()

    code, out, err = exec_cmd(['dcos', 'plugin', 'remove', 'dcos-test'])
    assert code == 0
    assert out == ''
    assert err == ''


def test_plugin_help(default_cluster):
    _install_test_plugin()

    code, out, err = exec_cmd(['dcos', 'help', 'test'])
    assert code == 0
    assert err == ''
    assert out == 'Help usage for dcos-test\n'


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
