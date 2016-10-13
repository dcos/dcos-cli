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
                                 GOOD_POD_STATUS_FILE_PATH,
                                 POD_KILL_FILE_PATH, POD_KILL_ID,
                                 pod_list_fixture, TRIPLE_POD_FILE_PATH,
                                 TRIPLE_POD_ID, UNGOOD_POD_FILE_PATH,
                                 UPDATED_GOOD_POD_FILE_PATH)

_PODS_ENABLED = 'DCOS_PODS_ENABLED' in os.environ

_POD_BASE_CMD = ['dcos', 'marathon', 'pod']
_POD_ADD_CMD = _POD_BASE_CMD + ['add']
_POD_KILL_CMD = _POD_BASE_CMD + ['kill']
_POD_LIST_CMD = _POD_BASE_CMD + ['list']
_POD_REMOVE_CMD = _POD_BASE_CMD + ['remove']
_POD_SHOW_CMD = _POD_BASE_CMD + ['show']
_POD_UPDATE_CMD = _POD_BASE_CMD + ['update']


@pytest.mark.skipif(not _PODS_ENABLED, reason="Requires pods")
def test_pod_add_from_file_then_remove():
    returncode, stdout, stderr = _pod_add_from_file(GOOD_POD_FILE_PATH)
    assert returncode == 0
    assert re.fullmatch('Created deployment \S+\n', stdout.decode('utf-8'))
    assert stderr == b''

    watch_all_deployments()

    # Explicitly testing non-forced-removal; can't use the context manager
    _assert_pod_remove(GOOD_POD_ID, extra_args=[])
    watch_all_deployments()


@pytest.mark.skipif(not _PODS_ENABLED, reason="Requires pods")
def test_pod_add_from_stdin_then_force_remove():
    # Explicitly testing adding from stdin; can't use the context manager
    _assert_pod_add_from_stdin(GOOD_POD_FILE_PATH)
    _assert_pod_remove(GOOD_POD_ID, extra_args=['--force'])
    watch_all_deployments()


@pytest.mark.skipif(not _PODS_ENABLED, reason="Requires pods")
def test_pod_list():
    expected_json = pod_list_fixture()

    with _pods({GOOD_POD_ID: GOOD_POD_FILE_PATH,
                DOUBLE_POD_ID: DOUBLE_POD_FILE_PATH,
                TRIPLE_POD_ID: TRIPLE_POD_FILE_PATH}):

        _assert_pod_list_json(expected_json)
        _assert_pod_list_table()


@pytest.mark.skipif(not _PODS_ENABLED, reason="Requires pods")
def test_pod_show():
    expected_json = file_json_ast(GOOD_POD_STATUS_FILE_PATH)

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
    with _pod(GOOD_POD_ID, GOOD_POD_FILE_PATH):
        # The deployment will never complete
        _assert_pod_update_from_stdin(
            extra_args=[],
            pod_json_file_path=UNGOOD_POD_FILE_PATH)

        # Override above failed deployment
        _assert_pod_update_from_stdin(
            extra_args=['--force'],
            pod_json_file_path=UPDATED_GOOD_POD_FILE_PATH)

        watch_all_deployments()


@pytest.mark.skipif(not _PODS_ENABLED, reason="Requires pods")
def test_pod_kill():
    with _pod(POD_KILL_ID, POD_KILL_FILE_PATH):
        kill_1, keep, kill_2 = _get_pod_instance_ids(POD_KILL_ID, 3)

        remove_args = [POD_KILL_ID, kill_1, kill_2]
        assert_command(_POD_KILL_CMD + remove_args)

        new_instance_ids = _get_pod_instance_ids(POD_KILL_ID, 3)
        assert keep in new_instance_ids
        assert kill_1 not in new_instance_ids
        assert kill_2 not in new_instance_ids
        # Marathon spins up new instances to replace the killed ones
        assert len(new_instance_ids) == 3


def _pod_add_from_file(file_path):
    cmd = _POD_ADD_CMD + [file_path]
    return exec_command(cmd)


def _assert_pod_add_from_stdin(file_path):
    cmd = _POD_ADD_CMD
    with open(file_path) as fd:
        returncode, stdout, stderr = exec_command(cmd, stdin=fd)

    assert returncode == 0
    assert re.fullmatch('Created deployment \S+\n', stdout.decode('utf-8'))
    assert stderr == b''

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
        _assert_pod_spec_json(expected_pod['spec'], actual_pod['spec'])

    assert len(actual_json) == len(expected_json)


def _assert_pod_status_json(expected_pod_status, actual_pod_status):
    """Checks that the "actual" pod status JSON matched the "expected" JSON.

    The comparison only looks at specific fields that are present in the
    test data used by this module.

    :param expected_pod_status: contains the baseline values for the comparison
    :type expected_pod_status: {}
    :param actual_pod_status: has its fields checked against expected's fields
    :type actual_pod_status: {}
    :rtype: None
    """

    assert actual_pod_status['id'] == expected_pod_status['id']
    assert actual_pod_status['status'] == expected_pod_status['status']
    assert len(actual_pod_status['instances']) == \
        len(expected_pod_status['instances'])

    _assert_pod_spec_json(expected_pod_status['spec'],
                          actual_pod_status['spec'])

    expected_instance = expected_pod_status['instances'][0]
    expected_container_statuses = {container['name']: container['status']
                                   for container
                                   in expected_instance['containers']}

    for actual_instance in actual_pod_status['instances']:
        assert actual_instance['status'] == expected_instance['status']

        actual_container_statuses = {container['name']: container['status']
                                     for container
                                     in actual_instance['containers']}

        assert actual_container_statuses == expected_container_statuses


def _assert_pod_spec_json(expected_pod_spec, actual_pod_spec):
    """Checks that the "actual" pod spec JSON matches the "expected" JSON.

    The comparison only looks at specific fields that are present in the
    test data used by this module.

    :param expected_pod_spec: contains the baseline values for the comparison
    :type expected_pod_spec: {}
    :param actual_pod_spec: has its fields checked against the expected fields
    :type actual_pod_spec: {}
    :rtype: None
    """

    expected_containers = expected_pod_spec['containers']
    actual_containers = actual_pod_spec['containers']
    actual_containers_by_name = {c['name']: c for c in actual_containers}

    for expected_container in expected_containers:
        container_name = expected_container['name']
        actual_container = actual_containers_by_name[container_name]

        for k, v in expected_container['resources'].items():
            assert actual_container['resources'][k] == v

    assert len(actual_containers) == len(expected_containers)


def _assert_pod_list_table():
    _wait_for_instances({'/double-pod': 2, '/good-pod': 1, '/winston': 1})
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


def _assert_pod_show(pod_id, expected_json):
    cmd = _POD_SHOW_CMD + [pod_id]
    returncode, stdout, stderr = exec_command(cmd)

    assert returncode == 0
    assert stderr == b''

    pod_status_json = json.loads(stdout.decode('utf-8'))
    _assert_pod_status_json(expected_json, pod_status_json)


def _assert_pod_update_from_stdin(extra_args, pod_json_file_path):
    cmd = _POD_UPDATE_CMD + [GOOD_POD_ID] + extra_args
    with open(pod_json_file_path) as fd:
        returncode, stdout, stderr = exec_command(cmd, stdin=fd)

    assert returncode == 0
    assert re.fullmatch('Created deployment \S+\n', stdout.decode('utf-8'))
    assert stderr == b''


@contextlib.contextmanager
def _pod(pod_id, file_path):
    with _pods({pod_id: file_path}):
        yield


@contextlib.contextmanager
def _pods(ids_and_paths):
    ids_and_results = {}
    for pod_id, file_path in ids_and_paths.items():
        ids_and_results[pod_id] = _pod_add_from_file(file_path)

    try:
        for pod_id, (returncode, stdout, stderr) in ids_and_results.items():
            assert returncode == 0
            assert re.fullmatch('Created deployment \S+\n',
                                stdout.decode('utf-8'))
            assert stderr == b''

        watch_all_deployments()
        yield
    finally:
        for pod_id, results in ids_and_results.items():
            returncode, _, _ = results
            if returncode == 0:
                _assert_pod_remove(pod_id, extra_args=['--force'])
        watch_all_deployments()


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


def _get_pod_instance_ids(pod_id, target_instance_count):
    """Waits for the given pod to reach a target instance count, then returns
    the IDs of all instances.

    :param pod_id: the pod to retrieve the instance IDs from
    :type pod_id: str
    :param target_instance_count: waits until the number of instances reaches
                                  this number
    :type target_instance_count: int
    :returns: a tuple of the pod's instance IDs
    :rtype: tuple(str)
    """

    _wait_for_instances({'/{}'.format(pod_id): target_instance_count})

    show_cmd = _POD_SHOW_CMD + [pod_id]
    returncode, stdout, stderr = exec_command(show_cmd)

    assert returncode == 0
    assert stderr == b''

    pod_status_json = json.loads(stdout.decode('utf-8'))
    instances_json = pod_status_json['instances']
    return tuple(instance['id'] for instance in instances_json)
