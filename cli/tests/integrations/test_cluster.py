import json
import subprocess

from .helpers.common import assert_command, exec_command


def test_info():
    stdout = b'Manage your DC/OS clusters\n'
    assert_command(['dcos', 'cluster', '--info'],
                   stdout=stdout)


def test_version():
    stdout = b'dcos-cluster version SNAPSHOT\n'
    assert_command(['dcos', 'cluster', '--version'],
                   stdout=stdout)


def test_list():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'cluster', 'list', '--json'])
    assert returncode == 0
    assert stderr == b''
    cluster_list = json.loads(stdout.decode('utf-8'))
    assert len(cluster_list) == 1
    info = cluster_list[0]
    assert info.get("attached")
    keys = ["attached", "cluster_id", "name", "url", "version"]
    assert sorted(info.keys()) == keys


def test_rename():
    _, stdout, _ = exec_command(
        ['dcos', 'cluster', 'list', '--json'])
    info = json.loads(stdout.decode('utf-8'))[0]
    name = info.get("name")

    new_name = "test"
    assert_command(['dcos', 'cluster', 'rename', name, new_name])

    returncode, stdout, stderr = exec_command(
        ['dcos', 'cluster', 'list', '--json'])
    assert json.loads(stdout.decode('utf-8'))[0].get("name") == new_name

    # rename back to original name
    assert_command(['dcos', 'cluster', 'rename', new_name, name])


def test_setup_noninteractive():
    """
    Run "dcos cluster setup" command as non-interactive with a 30 sec timeout.
    This makes sure the process doesn't prompt for input forever (DCOS-15590).
    """

    try:
        returncode, stdout, _ = exec_command(
            ['dcos',
             'cluster',
             'setup',
             'https://dcos.snakeoil.mesosphere.com'],
            timeout=30,
            stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        assert False, 'timed out waiting for process to exit'

    assert returncode == 1
    assert b"'' is not a valid response" in stdout
