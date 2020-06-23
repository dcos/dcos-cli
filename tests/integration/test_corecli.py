import os

import pytest

from .common import exec_cmd, default_cluster  # noqa: F401


@pytest.mark.parametrize("cmd", [['dcos', 'package', 'install', 'dcos-core-cli'],
                                 ['dcos', 'package', 'install', 'dcos-core-cli', '--cli'],
                                 ['dcos', 'package', 'install', 'dcos-core-cli', '--yes'],
                                 ['dcos', '-vv', 'package', 'install', 'dcos-core-cli']])
def test_update_core(cmd, default_cluster):
    code, out, _ = exec_cmd(cmd)
    assert code == 0
    assert out == ''


@pytest.mark.skipif(
    os.environ.get('DCOS_TEST_DEFAULT_CLUSTER_VARIANT') == 'open',
    reason="This test needs the Bootstrap Registry, only available on DC/OS EE."
)
def test_update_core_with_bootstrap_registry(default_cluster):
    code, _, _ = exec_cmd(['dcos', 'package', 'repo', 'remove', 'Universe'])
    assert code == 0

    try:
        code, out, _ = exec_cmd(['dcos', 'package', 'install', 'dcos-core-cli'])
        assert code == 0
        assert out == ''
    finally:
        code, _, _ = exec_cmd(['dcos', 'package', 'repo', 'add', '--index=0',
                               'Universe', 'https://universe.mesosphere.com/repo'])
        assert code == 0
