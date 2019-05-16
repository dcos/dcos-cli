from .common import exec_cmd, default_cluster  # noqa: F401


def test_update_core(default_cluster):
    cmds = [
        ['dcos', 'package', 'install', 'dcos-core-cli'],
        ['dcos', 'package', 'install', 'dcos-core-cli', '--cli'],
        ['dcos', 'package', 'install', 'dcos-core-cli', '--yes'],
        ['dcos', '-vv', 'package', 'install', 'dcos-core-cli'],
    ]

    for cmd in cmds:
        code, out, _ = exec_cmd(cmd)
        assert code == 0
        assert out == ''
