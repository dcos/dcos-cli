import json
import os
import sys

from concurrent import futures

import pytest

from .common import exec_cmd, default_cluster  # noqa: F401


@pytest.mark.skipif(os.environ.get('DCOS_TEST_CORECLI') is None, reason="no core CLI bundle")
def test_extract_core(default_cluster):
    code, out, err = exec_cmd(['dcos', 'plugin', 'remove', 'dcos-core-cli'])
    assert code == 0
    assert out == ''
    assert err == ''

    cmd = ['dcos', 'package', 'describe', 'dcos-core-cli']

    code, out, err = exec_cmd(cmd)
    assert code == 0
    assert err.startswith("Extracting \"dcos-core-cli\"...\n")

    pkgInfo = json.loads(out)
    assert pkgInfo['package']['name'] == 'dcos-core-cli'

    code, out, err = exec_cmd(cmd)
    assert code == 0
    assert err == ""

    pkgInfo = json.loads(out)
    assert pkgInfo['package']['name'] == 'dcos-core-cli'


@pytest.mark.skipif(os.environ.get('DCOS_TEST_CORECLI') is None, reason="no core CLI bundle")
@pytest.mark.skipif(sys.platform == 'win32',
                    reason='Not yet concurrent-safe on Windows (DCOS_OSS-4843)')
def test_extract_core_concurrently(default_cluster):
    code, out, err = exec_cmd(['dcos', 'plugin', 'remove', 'dcos-core-cli'])
    assert code == 0
    assert out == ''
    assert err == ''

    with futures.ThreadPoolExecutor() as pool:
        cmds = [pool.submit(exec_cmd, ['dcos', 'node', 'list']) for _ in range(50)]

        completed, _ = futures.wait(cmds, timeout=60)
        assert len(completed) == 50

        for cmd in completed:
            code, out, err = cmd.result()
            assert code == 0, out + err


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
