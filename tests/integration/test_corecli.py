import json
import os

from .common import exec_cmd, default_cluster, default_cluster_with_plugins  # noqa: F401

import pytest


@pytest.mark.skipif(os.environ.get('DCOS_TEST_CORECLI') is None, reason="no core CLI bundle")
def test_extract_core(default_cluster):
    cmd = ['dcos', 'package', 'describe', 'dcos-core-cli']

    code, out, err = exec_cmd(cmd)
    assert code == 0
    assert err == "Extracting \"dcos-core-cli\"...\n"

    pkgInfo = json.loads(out)
    assert pkgInfo['package']['name'] == 'dcos-core-cli'

    code, out, err = exec_cmd(cmd)
    assert code == 0
    assert err == ""

    pkgInfo = json.loads(out)
    assert pkgInfo['package']['name'] == 'dcos-core-cli'



def test_update_core(default_cluster_with_plugins):
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
