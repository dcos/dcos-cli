from .common import exec_cmd, default_cluster  # noqa: F401


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
    assert dcos_enterprise_cli[1:] == ['backup', 'license', 'security']
