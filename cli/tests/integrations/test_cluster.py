import json
import os
import subprocess
from distutils.dir_util import copy_tree

import pytest

from dcos import cluster
from dcoscli.test.common import (assert_command, dcos_tempdir, exec_command,
                                 skip_if_env_missing)
from dcoscli.test.constants import (DCOS_TEST_URL_ENV)


@pytest.fixture
def dcos_dir_tmp_copy():
    with dcos_tempdir(True) as tempdir:
        yield tempdir


@pytest.fixture
def dcos_dir_tmp():
    with dcos_tempdir() as tempdir:
        yield tempdir


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
    keys = ["attached", "cluster_id", "name", "status", "url", "version"]
    assert sorted(info.keys()) == keys
    assert info.get('version') != cluster.VERSION_UNKNOWN


def test_remove_all(dcos_dir_tmp_copy):
    # confirm 1
    assert _num_of_clusters() == 1

    # integration tests assume 1 cluster setup.  updating to 2.
    for root, dirs, _ in os.walk(os.path.join(dcos_dir_tmp_copy, "clusters")):
        if len(dirs) > 0:
            test_cluster = os.path.join(root, dirs[0])
            break

    # hacky way to create another cluster
    test_cluster_2 = os.path.join(
        os.path.dirname(test_cluster),
        "a8b53513-63d4-4068-8b08-fde4fe1f1a83")

    copy_tree(test_cluster, test_cluster_2)

    # confirm 2
    assert _num_of_clusters() == 2

    # actual test
    returncode, stdout, stderr = exec_command(
        ['dcos', 'cluster', 'remove', "--all"])
    assert returncode == 0
    assert stderr == b''
    assert stdout == b''

    assert _num_of_clusters() == 0


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

    skip_if_env_missing([DCOS_TEST_URL_ENV])

    returncode, stdout, stderr = exec_command(
        ['dcos',
         'cluster',
         'setup',
         os.environ.get(DCOS_TEST_URL_ENV)],
        timeout=30,
        stdin=subprocess.DEVNULL)

    assert returncode == 1
    assert b"'' is not a valid response" in stdout
    assert b"Couldn't get confirmation for the fingerprint." in stderr


def test_setup_unreachable_url():
    """
    Run "dcos cluster setup" with an invalid URL.
    This makes sure we don't print unexpected errors or hang for too long.
    """

    returncode, stdout, stderr = exec_command(
        ['dcos',
         'cluster',
         'setup',
         'https://will.never.exist.hopefully.BOFGY7tfb7doftd'],
        timeout=10)

    assert returncode == 1
    msg = (b"Error downloading CA certificate from cluster."
           b" Please check the provided DC/OS URL.\n")
    assert msg == stderr


def test_link_self(dcos_dir_tmp_copy):
    skip_if_env_missing([DCOS_TEST_URL_ENV])

    returncode, stdout, stderr = exec_command(
        ['dcos',
         'cluster',
         'link',
         '--provider=dcos-users',
         os.environ.get(DCOS_TEST_URL_ENV)])

    assert returncode != 0
    assert stdout == b''
    assert stderr == b"Cannot link a cluster to itself.\n"


def test_link_invalid_cluster(dcos_dir_tmp_copy):
    name = 'https://will.never.exist.hopefully.BOFGY7tfb7doftd'
    ret, _, err = exec_command(['dcos', 'cluster', 'link', name])
    assert ret != 0
    assert err.decode('utf-8').startswith(
            "Unable to retrieve IP for '{}':".format(name))


def test_unlink_invalid_cluster(dcos_dir_tmp_copy):
    name = 'not-me'
    ret, _, err = exec_command(['dcos', 'cluster', 'unlink', name])
    assert ret != 0
    assert err.decode('utf-8') == "Unknown cluster link {}.\n".format(name)


def _num_of_clusters():
    _, stdout, _ = exec_command(
        ['dcos', 'cluster', 'list', '--json'])
    cluster_list = json.loads(stdout.decode('utf-8'))
    return len(cluster_list)
