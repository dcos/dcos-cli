import contextlib
import json
import re

import pytest

from ..common import file_bytes
from ..fixtures.marathon import (DOUBLE_POD_FILE_PATH, DOUBLE_POD_ID,
                                 GOOD_POD_FILE_PATH, GOOD_POD_ID,
                                 TRIPLE_POD_FILE_PATH, TRIPLE_POD_ID,
                                 UPDATED_GOOD_POD_FILE_PATH, pod_fixture)
from .common import (assert_command, exec_command, file_json_ast,
                     watch_all_deployments)

_POD_BASE_CMD = ['dcos', 'marathon', 'pod']
_POD_ADD_CMD = _POD_BASE_CMD + ['add']
_POD_LIST_CMD = _POD_BASE_CMD + ['list']
_POD_REMOVE_CMD = _POD_BASE_CMD + ['remove']
_POD_SHOW_CMD = _POD_BASE_CMD + ['show']
_POD_UPDATE_CMD = _POD_BASE_CMD + ['update']


def test_pod_add_from_file_then_remove():
    returncode, stdout, stderr = _pod_add_from_file(GOOD_POD_FILE_PATH)
    assert returncode == 0
    assert stdout == b''
    assert stderr == b''

    watch_all_deployments()

    # Explicitly testing non-forced-removal; can't use the context manager
    _assert_pod_remove(GOOD_POD_ID, extra_args=[])


def test_pod_add_from_stdin_then_force_remove():
    # Explicitly testing adding from stdin; can't use the context manager
    _assert_pod_add_from_stdin(GOOD_POD_FILE_PATH)
    _assert_pod_remove(GOOD_POD_ID, extra_args=['--force'])


def test_pod_list():
    expected_json = pod_fixture()
    expected_table = file_bytes('tests/unit/data/pod.txt')

    with _pod(GOOD_POD_ID, GOOD_POD_FILE_PATH), \
            _pod(DOUBLE_POD_ID, DOUBLE_POD_FILE_PATH), \
            _pod(TRIPLE_POD_ID, TRIPLE_POD_FILE_PATH):

        _assert_pod_list_json(expected_json)
        _assert_pod_list_table(stdout=expected_table + b'\n')


def test_pod_show():
    expected_json = file_json_ast(GOOD_POD_FILE_PATH)

    with _pod(GOOD_POD_ID, GOOD_POD_FILE_PATH):
        _assert_pod_show(GOOD_POD_ID, expected_json)


def test_pod_update_from_properties():
    expected_json = file_json_ast(UPDATED_GOOD_POD_FILE_PATH)
    containers_json_str = json.dumps(expected_json['containers'])
    networks_json_str = json.dumps(expected_json['networks'])
    properties = ['id=/{}'.format(GOOD_POD_ID),
                  'containers={}'.format(containers_json_str),
                  'networks={}'.format(networks_json_str)]

    with _pod(GOOD_POD_ID, GOOD_POD_FILE_PATH):
        _assert_pod_update_from_properties(GOOD_POD_ID,
                                           properties,
                                           extra_args=[])
        _assert_pod_show(GOOD_POD_ID, expected_json)


def test_pod_update_from_stdin_force_true():
    expected_json = file_json_ast(UPDATED_GOOD_POD_FILE_PATH)

    with _pod(GOOD_POD_ID, GOOD_POD_FILE_PATH):
        _assert_pod_update_from_stdin(GOOD_POD_ID,
                                      UPDATED_GOOD_POD_FILE_PATH,
                                      extra_args=['--force'])
        _assert_pod_show(GOOD_POD_ID, expected_json)


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
        _assert_pod_json(expected_pod, actual_pod)

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


def _assert_pod_list_table(stdout):
    assert_command(_POD_LIST_CMD, returncode=0, stdout=stdout, stderr=b'')


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


def _assert_pod_update_from_properties(pod_id, properties, extra_args):
    cmd = _POD_UPDATE_CMD + [pod_id] + properties + extra_args
    returncode, stdout, stderr = exec_command(cmd)

    assert returncode == 0
    assert re.fullmatch('Created deployment \S+\n', stdout.decode('utf-8'))
    assert stderr == b''

    watch_all_deployments()


def _assert_pod_update_from_stdin(pod_id, file_path, extra_args):
    cmd = _POD_UPDATE_CMD + [pod_id] + extra_args
    with open(file_path) as fd:
        returncode, stdout, stderr = exec_command(cmd, stdin=fd)

    assert returncode == 0
    assert re.fullmatch('Created deployment \S+\n', stdout.decode('utf-8'))
    assert stderr == b''

    watch_all_deployments()


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
