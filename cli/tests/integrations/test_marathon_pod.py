import json
import re
import time

import pytest

from .helpers.common import assert_command, exec_command
from .helpers.marathon import (add_pod, pod, pod_spec_json, pods, remove_pod,
                               watch_all_deployments)
from ..fixtures.marathon import (DOUBLE_POD_FILE_PATH, DOUBLE_POD_ID,
                                 GOOD_POD_FILE_PATH, GOOD_POD_ID,
                                 POD_KILL_FILE_PATH, POD_KILL_ID,
                                 pod_list_fixture, TRIPLE_POD_FILE_PATH,
                                 TRIPLE_POD_ID, UNGOOD_POD_FILE_PATH,
                                 UPDATED_GOOD_POD_FILE_PATH)

_POD_BASE_CMD = ['dcos', 'marathon', 'pod']
_POD_ADD_CMD = _POD_BASE_CMD + ['add']
_POD_KILL_CMD = _POD_BASE_CMD + ['kill']
_POD_LIST_CMD = _POD_BASE_CMD + ['list']
_POD_REMOVE_CMD = _POD_BASE_CMD + ['remove']
_POD_SHOW_CMD = _POD_BASE_CMD + ['show']
_POD_UPDATE_CMD = _POD_BASE_CMD + ['update']


def test_pod_add_from_file():
    add_pod(GOOD_POD_FILE_PATH)
    remove_pod(GOOD_POD_ID, force=False)
    watch_all_deployments()


def test_pod_list():
    expected_json = pod_list_fixture()

    with pods({GOOD_POD_FILE_PATH: GOOD_POD_ID,
               DOUBLE_POD_FILE_PATH: DOUBLE_POD_ID,
               TRIPLE_POD_FILE_PATH: TRIPLE_POD_ID}):

        _assert_pod_list_json(expected_json)
        _assert_pod_list_table()


def test_pod_update_does_not_support_properties():
    cmd = _POD_UPDATE_CMD + ['any-pod', 'foo=bar']
    returncode, stdout, stderr = exec_command(cmd)

    assert returncode == 1
    assert stdout.startswith(b'Invalid subcommand usage\n')
    assert stderr == b''


def test_pod_update_from_stdin():
    with pod(GOOD_POD_FILE_PATH, GOOD_POD_ID):
        # The deployment will never complete
        _assert_pod_update_from_stdin(
            extra_args=[],
            pod_json_file_path=UNGOOD_POD_FILE_PATH)

        # Override above failed deployment
        _assert_pod_update_from_stdin(
            extra_args=['--force'],
            pod_json_file_path=UPDATED_GOOD_POD_FILE_PATH)

        watch_all_deployments()


@pytest.mark.skipif(
    True, reason='https://mesosphere.atlassian.net/browse/DCOS-13368')
def test_pod_kill():
    with pod(POD_KILL_FILE_PATH, POD_KILL_ID):
        kill_1, keep, kill_2 = _get_pod_instance_ids(POD_KILL_ID, 3)

        remove_args = [POD_KILL_ID, kill_1, kill_2]
        assert_command(_POD_KILL_CMD + remove_args)

        new_instance_ids = _get_pod_instance_ids(POD_KILL_ID, 3)
        assert keep in new_instance_ids
        assert kill_1 not in new_instance_ids
        assert kill_2 not in new_instance_ids
        # Marathon spins up new instances to replace the killed ones
        assert len(new_instance_ids) == 3


def _pod_add_from_stdin(file_path):
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
        pod_spec_json(expected_pod['spec'], actual_pod['spec'])

    assert len(actual_json) == len(expected_json)


def _assert_pod_list_table():
    _wait_for_instances({'/double-pod': 2, '/good-pod': 1, '/winston': 1})
    returncode, stdout, stderr = exec_command(_POD_LIST_CMD)

    assert returncode == 0
    assert stderr == b''

    stdout_lines = stdout.decode('utf-8').split('\n')

    pattern = r'ID\+TASKS +INSTANCES +VERSION +STATUS +STATUS SINCE +WAITING *'
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


def _assert_pod_update_from_stdin(extra_args, pod_json_file_path):
    cmd = _POD_UPDATE_CMD + [GOOD_POD_ID] + extra_args
    with open(pod_json_file_path) as fd:
        returncode, stdout, stderr = exec_command(cmd, stdin=fd)

    assert returncode == 0
    assert re.fullmatch('Created deployment \S+\n', stdout.decode('utf-8'))
    assert stderr == b''


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
        actual_instances = {pod_obj['id']: len(pod_obj.get('instances', []))
                            for pod_obj in status_json}

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
