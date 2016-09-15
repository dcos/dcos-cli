import contextlib
import json
import re

from dcos import util

import pytest

from ..common import file_bytes
from ..fixtures.marathon import (DOUBLE_POD_FILE_PATH, DOUBLE_POD_ID,
                                 GOOD_POD_FILE_PATH, GOOD_POD_ID,
                                 TRIPLE_POD_FILE_PATH, TRIPLE_POD_ID,
                                 UPDATED_GOOD_POD_FILE_PATH, pod_fixture)
from .common import assert_command, exec_command

_POD_BASE_CMD = ['dcos', 'marathon', 'pod']
_POD_ADD_CMD = _POD_BASE_CMD + ['add']
_POD_LIST_CMD = _POD_BASE_CMD + ['list']
_POD_REMOVE_CMD = _POD_BASE_CMD + ['remove']
_POD_SHOW_CMD = _POD_BASE_CMD + ['show']
_POD_UPDATE_CMD = _POD_BASE_CMD + ['update']


@pytest.mark.skip(reason="Pods support in Marathon not released yet")
def test_pod_add_from_file_then_remove():
    returncode, stdout, stderr = _pod_add_from_file(GOOD_POD_FILE_PATH)
    assert returncode == 0
    assert stdout == b''
    assert stderr == b''

    # Explicitly testing non-forced-removal; can't use the context manager
    _assert_pod_remove(GOOD_POD_ID, extra_args=[])


@pytest.mark.skip(reason="Pods support in Marathon not released yet")
def test_pod_add_from_stdin_then_force_remove():
    # Explicitly testing adding from stdin; can't use the context manager
    _assert_pod_add_from_stdin(GOOD_POD_FILE_PATH)
    _assert_pod_remove(GOOD_POD_ID, extra_args=['--force'])


@pytest.mark.skip(reason="Pods support in Marathon not released yet")
def test_pod_list():
    expected_json = pod_fixture()
    expected_table = file_bytes('tests/unit/data/pod.txt')

    with _pod(GOOD_POD_ID, GOOD_POD_FILE_PATH), \
            _pod(DOUBLE_POD_ID, DOUBLE_POD_FILE_PATH), \
            _pod(TRIPLE_POD_ID, TRIPLE_POD_FILE_PATH):

        _assert_pod_list_json(expected_json)
        _assert_pod_list_table(stdout=expected_table + b'\n')


@pytest.mark.skip(reason="Pods support in Marathon not released yet")
def test_pod_show():
    with _pod(GOOD_POD_ID, GOOD_POD_FILE_PATH):
        _assert_pod_show(GOOD_POD_ID)


@pytest.mark.skip(reason="Pods support in Marathon not released yet")
def test_pod_update_from_file():
    expected_show_stdout = file_bytes(UPDATED_GOOD_POD_FILE_PATH)

    with _pod(GOOD_POD_ID, GOOD_POD_FILE_PATH):
        _assert_pod_update_from_file(GOOD_POD_ID,
                                     UPDATED_GOOD_POD_FILE_PATH,
                                     extra_args=[])
        _assert_pod_show(GOOD_POD_ID, expected_show_stdout)


@pytest.mark.skip(reason="Pods support in Marathon not released yet")
def test_pod_update_from_stdin_force_true():
    expected_show_stdout = file_bytes(UPDATED_GOOD_POD_FILE_PATH)

    with _pod(GOOD_POD_ID, GOOD_POD_FILE_PATH):
        _assert_pod_update_from_stdin(GOOD_POD_ID,
                                      UPDATED_GOOD_POD_FILE_PATH,
                                      extra_args=['--force'])
        _assert_pod_show(GOOD_POD_ID, expected_show_stdout)


def _pod_add_from_file(file_path):
    cmd = _POD_ADD_CMD + [file_path]
    return exec_command(cmd)


def _assert_pod_add_from_stdin(file_path):
    cmd = _POD_ADD_CMD
    with open(file_path) as fd:
        assert_command(cmd, returncode=0, stdout=b'', stderr=b'', stdin=fd)


def _assert_pod_list_json(expected_json):
    cmd = _POD_LIST_CMD + ['--json']
    returncode, stdout, stderr = exec_command(cmd)
    assert returncode == 0
    assert stderr == b''

    # The below comparison assumes the expected JSON has a specific structure
    parsed_stdout = json.loads(stdout.decode('utf-8'))
    pods_by_id = {pod['id']: pod for pod in parsed_stdout}

    for expected_pod in expected_json:
        pod_id = expected_pod['id']
        actual_pod = pods_by_id.pop(pod_id)

        expected_containers = expected_pod['containers']
        actual_containers = actual_pod['containers']
        containers_by_name = {c['name']: c for c in actual_containers}

        for expected_container in expected_containers:
            container_name = expected_container['name']
            actual_container = containers_by_name.pop(container_name)

            for k, v in expected_container['resources'].items():
                assert actual_container['resources'][k] == v

        assert len(containers_by_name) == 0

    assert len(pods_by_id) == 0


def _assert_pod_list_table(stdout):
    assert_command(_POD_LIST_CMD, returncode=0, stdout=stdout, stderr=b'')


def _assert_pod_remove(pod_id, extra_args):
    cmd = _POD_REMOVE_CMD + [pod_id] + extra_args
    assert_command(cmd, returncode=0, stdout=b'', stderr=b'')


def _assert_pod_show(pod_id):
    cmd = _POD_SHOW_CMD + [pod_id]
    returncode, stdout, stderr = exec_command(cmd)

    assert returncode == 0
    assert stderr == b''

    pod_json = json.loads(stdout.decode('utf-8'))
    assert pod_json['id'] == util.normalize_marathon_id_path(pod_id)


def _assert_pod_update_from_file(pod_id, file_path, extra_args):
    cmd = _POD_UPDATE_CMD + [pod_id, file_path] + extra_args
    returncode, stdout, stderr = exec_command(cmd)

    assert returncode == 0
    assert re.fullmatch('Created deployment \S+\n', stdout.decode('utf-8'))
    assert stderr == b''


def _assert_pod_update_from_stdin(pod_id, file_path, extra_args):
    cmd = _POD_UPDATE_CMD + [pod_id, file_path] + extra_args
    with open(file_path) as fd:
        returncode, stdout, stderr = exec_command(cmd, stdin=fd)

    assert returncode == 0
    assert re.fullmatch('Created deployment \S+\n', stdout.decode('utf-8'))
    assert stderr == b''


@contextlib.contextmanager
def _pod(pod_id, file_path):
    returncode, stdout, stderr = _pod_add_from_file(file_path)
    pod_added = (returncode == 0)

    try:
        assert pod_added
        assert stdout == b''
        assert stderr == b''

        yield
    finally:
        if pod_added:
            _assert_pod_remove(pod_id, extra_args=['--force'])
