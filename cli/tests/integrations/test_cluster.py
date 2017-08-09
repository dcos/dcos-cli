import json
import os
import pytest
import dcos
import subprocess

from .helpers.common import assert_command, exec_command
from distutils.dir_util import copy_tree, remove_tree


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


@pytest.fixture
def cluster_backup():
    dcos_dir = os.environ.get('DCOS_DIR')
    if dcos_dir is None:
        dcos_dir = dcos.config.get_config_dir_path()
    assert dcos_dir is not None
    cluster_dir = os.path.join(dcos_dir, 'clusters')
    back_dir = os.path.join(dcos_dir, 'backup')
    copy_tree(cluster_dir, back_dir)

    yield cluster_dir
    # return to order
    remove_tree(cluster_dir)
    copy_tree(back_dir, cluster_dir)
    remove_tree(back_dir)


def test_remove_all(cluster_backup):
    cluster_dir = cluster_backup

    # confirm 1
    assert num_of_clusters() == 1


    # integration tests assume 1 cluster setup.  updating to 2.
    for root, dirs, files in os.walk(cluster_dir):
        if len(dirs) > 0:
            test_cluster = os.path.join(root, dirs[0])
            break
    # hacky way to create another cluster
    test_cluster2 = "{}2".format(test_cluster)
    copy_tree(test_cluster, test_cluster2)

    # confirm 2
    assert num_of_clusters() == 2

    # actual test
    returncode, stdout, stderr = exec_command(
        ['dcos', 'cluster', 'remove', "--all"])
    assert returncode == 0
    assert stderr == b''
    assert stdout == b''

    assert num_of_clusters() == 0


def num_of_clusters():
    _, stdout, _ = exec_command(
        ['dcos', 'cluster', 'list', '--json'])
    cluster_list = json.loads(stdout.decode('utf-8'))
    return len(cluster_list)


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
