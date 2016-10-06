import contextlib
import json
import os
import re
import time

import pytest

from .common import (assert_command, exec_command, file_json_ast,
                     watch_all_deployments)
from ..fixtures.marathon import (DOUBLE_POD_FILE_PATH, DOUBLE_POD_ID,
                                 GOOD_POD_FILE_PATH, GOOD_POD_ID,
                                 pod_list_fixture, TRIPLE_POD_FILE_PATH,
                                 TRIPLE_POD_ID, UPDATED_GOOD_POD_FILE_PATH)

_PODS_ENABLED = 'DCOS_PODS_ENABLED' in os.environ

_POD_BASE_CMD = ['dcos', 'marathon', 'pod']
_POD_ADD_CMD = _POD_BASE_CMD + ['add']
_POD_LIST_CMD = _POD_BASE_CMD + ['list']
_POD_REMOVE_CMD = _POD_BASE_CMD + ['remove']
_POD_SHOW_CMD = _POD_BASE_CMD + ['show']
_POD_UPDATE_CMD = _POD_BASE_CMD + ['update']


@pytest.mark.skipif(not _PODS_ENABLED, reason="Requires pods")
def test_pod_add_from_file_then_remove():
    returncode, stdout, stderr = _pod_add_from_file(GOOD_POD_FILE_PATH)
    assert returncode == 0
    assert stdout == b''
    assert stderr == b''

    watch_all_deployments()

    # Explicitly testing non-forced-removal; can't use the context manager
    _assert_pod_remove(GOOD_POD_ID, extra_args=[])


@pytest.mark.skipif(not _PODS_ENABLED, reason="Requires pods")
def test_pod_add_from_stdin_then_force_remove():
    # Explicitly testing adding from stdin; can't use the context manager
    _assert_pod_add_from_stdin(GOOD_POD_FILE_PATH)
    _assert_pod_remove(GOOD_POD_ID, extra_args=['--force'])


@pytest.mark.skipif(not _PODS_ENABLED, reason="Requires pods")
def test_pod_list():
    expected_json = pod_list_fixture()

    with _pod(GOOD_POD_ID, GOOD_POD_FILE_PATH), \
            _pod(DOUBLE_POD_ID, DOUBLE_POD_FILE_PATH), \
            _pod(TRIPLE_POD_ID, TRIPLE_POD_FILE_PATH):

        _assert_pod_list_json(expected_json)
        _assert_pod_list_table()


@pytest.mark.skipif(not _PODS_ENABLED, reason="Requires pods")
def test_pod_show():
    expected_json = file_json_ast(GOOD_POD_FILE_PATH)

    with _pod(GOOD_POD_ID, GOOD_POD_FILE_PATH):
        _assert_pod_show(GOOD_POD_ID, expected_json)


def test_pod_update_does_not_support_properties():
    cmd = _POD_UPDATE_CMD + ['any-pod', 'foo=bar']
    returncode, stdout, stderr = exec_command(cmd)

    assert returncode == 1
    assert stdout.startswith(b'Command not recognized\n')
    assert stderr == b''


@pytest.mark.skipif(not _PODS_ENABLED, reason="Requires pods")
def test_pod_update_from_stdin():
    _assert_pod_update_from_stdin(extra_args=[])


@pytest.mark.skipif(not _PODS_ENABLED, reason="Requires pods")
def test_pod_update_from_stdin_force():
    _assert_pod_update_from_stdin(extra_args=['--force'])


def _pod_add_from_file(file_path):
    cmd = _POD_ADD_CMD + [file_path]
    return exec_command(cmd)


def _assert_pod_add_from_stdin(file_path):
    cmd = _POD_ADD_CMD
    with open(file_path) as fd:
        assert_command(cmd, returncode=0, stdout=b'', stderr=b'', stdin=fd)

    watch_all_deployments()


def _assert_pod_list_json(expected_json):
    cmd = _POD_LIST_CMD + ['--json']
    returncode, stdout, stderr = exec_command(cmd)
    assert returncode == 0
    assert stderr == b''

    actual_json = json.loads(stdout.decode('utf-8'))
    _assert_pod_list_json_subset(expected_json, actual_json)


def _assert_pod_list_json_subset(expected_json, actual_json):
    actual_pods_by_id = {pod['id']: pod for pod in actual_json}

    for expected_pod in expected_json:
        pod_id = expected_pod['id']
        actual_pod = actual_pods_by_id[pod_id]
        _assert_pod_json(expected_pod['spec'], actual_pod['spec'])

    assert len(actual_json) == len(expected_json)


def _assert_pod_json(expected_pod, actual_pod):
    """Checks that the "actual" pod JSON matches the "expected" pod JSON.

    The comparison only looks at specific fields that are present in the
    test data used by this module.

    :param expected_pod: contains the baseline values for the comparison
    :type expected_pod: {}
    :param actual_pod: has its fields checked against the expected fields
    :type actual_pod: {}
    :rtype: None
    """

    expected_containers = expected_pod['containers']
    actual_containers = actual_pod['containers']
    actual_containers_by_name = {c['name']: c for c in actual_containers}

    for expected_container in expected_containers:
        container_name = expected_container['name']
        actual_container = actual_containers_by_name[container_name]

        for k, v in expected_container['resources'].items():
            assert actual_container['resources'][k] == v

    assert len(actual_containers) == len(expected_containers)


def _assert_pod_list_table():
    _wait_for_instances({'/double-pod': 2, '/good-pod': 3, '/winston': 1})
    returncode, stdout, stderr = exec_command(_POD_LIST_CMD)

    assert returncode == 0
    assert stderr == b''

    stdout_lines = stdout.decode('utf-8').split('\n')

    pattern = r'ID\+TASKS +INSTANCES +VERSION +STATUS +STATUS SINCE *'
    assert re.fullmatch(pattern, stdout_lines[0])

    assert stdout_lines[1].startswith('/double-pod')
    assert stdout_lines[2].startswith(' |-thing-1')
    assert stdout_lines[3].startswith(' |-thing-2')
    assert stdout_lines[4].startswith('/good-pod')
    assert stdout_lines[5].startswith(' |-good-container')
    assert stdout_lines[6].startswith('/winston')
    assert stdout_lines[7].startswith(' |-the-cat')
    assert stdout_lines[8].startswith(' |-thing-1')
    assert stdout_lines[9].startswith(' |-thing-2')

    assert stdout_lines[10] == ''
    assert len(stdout_lines) == 11


def _assert_pod_remove(pod_id, extra_args):
    cmd = _POD_REMOVE_CMD + [pod_id] + extra_args
    assert_command(cmd, returncode=0, stdout=b'', stderr=b'')

    watch_all_deployments()


def _assert_pod_show(pod_id, expected_json):
    cmd = _POD_SHOW_CMD + [pod_id]
    returncode, stdout, stderr = exec_command(cmd)

    assert returncode == 0
    assert stderr == b''

    pod_json = json.loads(stdout.decode('utf-8'))
    _assert_pod_json(expected_json, pod_json)


def _assert_pod_update_from_stdin(extra_args):
    expected_json = file_json_ast(UPDATED_GOOD_POD_FILE_PATH)

    with _pod(GOOD_POD_ID, GOOD_POD_FILE_PATH):
        cmd = _POD_UPDATE_CMD + [GOOD_POD_ID] + extra_args
        with open(UPDATED_GOOD_POD_FILE_PATH) as fd:
            returncode, stdout, stderr = exec_command(cmd, stdin=fd)

        assert returncode == 0
        assert re.fullmatch('Created deployment \S+\n', stdout.decode('utf-8'))
        assert stderr == b''

        watch_all_deployments()
        _assert_pod_show(GOOD_POD_ID, expected_json)


@contextlib.contextmanager
def _pod(pod_id, file_path):
    returncode, stdout, stderr = _pod_add_from_file(file_path)
    pod_added = (returncode == 0)

    try:
        assert pod_added
        assert stdout == b''
        assert stderr == b''

        watch_all_deployments()
        yield
    finally:
        if pod_added:
            _assert_pod_remove(pod_id, extra_args=['--force'])


def _wait_for_instances(expected_instances, max_attempts=10):
    """Polls the `pod list` command until the instance counts are as expected.

    :param expected_instances: a mapping from pod ID to instance count
    :type expected_instances: {}
    :param max_attempts: give up and fail the test after this many attempts
    :type max_attempts: int
    :rtype: None
    """

    for attempt in range(max_attempts):
        returncode, stdout, stderr = exec_command(_POD_LIST_CMD + ['--json'])

        assert returncode == 0
        assert stderr == b''

        status_json = json.loads(stdout.decode('utf-8'))
        actual_instances = {pod['id']: len(pod.get('instances', []))
                            for pod in status_json}

        if actual_instances == expected_instances:
            return
        time.sleep(1)
    else:
        assert False, "Timed out waiting for expected instance counts"
