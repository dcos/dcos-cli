import contextlib
import json
import re

from .common import (file_bytes, file_json, exec_command)

FILE_PATH_BASE = 'tests/data/marathon/pods/'

GOOD_POD_ID = 'good-pod'
GOOD_POD_FILE_PATH = FILE_PATH_BASE + 'good.json'
UPDATED_GOOD_POD_FILE_PATH = FILE_PATH_BASE + 'updated_good.json'

DOUBLE_POD_ID = 'double-pod'
DOUBLE_POD_FILE_PATH = FILE_PATH_BASE + 'double.json'

TRIPLE_POD_ID = 'winston'
TRIPLE_POD_FILE_PATH = FILE_PATH_BASE + 'doubleplusgood.json'


def test_pod_add_from_file_then_remove():
    exit_status = _pod_add_from_file(GOOD_POD_FILE_PATH)
    assert exit_status == 0

    exit_status = _pod_remove(GOOD_POD_ID, force=False)
    assert exit_status == 0


def test_pod_add_from_stdin_then_force_remove():
    exit_status = _pod_add_from_stdin(GOOD_POD_FILE_PATH)
    assert exit_status == 0

    exit_status = _pod_remove(GOOD_POD_ID, force=True)
    assert exit_status == 0


def test_pod_list_json():
    with _pod(GOOD_POD_ID, GOOD_POD_FILE_PATH):
        with _pod(DOUBLE_POD_ID, DOUBLE_POD_FILE_PATH):
            with _pod(TRIPLE_POD_ID, TRIPLE_POD_FILE_PATH):
                exit_status, stdout = _pod_list(json=True)
                assert exit_status == 0

                parsed_stdout = json.loads(stdout.decode('utf-8'))
                parsed_good = file_json(GOOD_POD_FILE_PATH)
                parsed_double = file_json(DOUBLE_POD_FILE_PATH)
                parsed_triple = file_json(TRIPLE_POD_FILE_PATH)
                expected_stdout = [parsed_good, parsed_double, parsed_triple]

                _assert_same_elements(parsed_stdout, expected_stdout)


def test_pod_list_table():
    # Add several pods, verify that the table view is correct
    pass


def test_pod_show():
    with _pod(GOOD_POD_ID, GOOD_POD_FILE_PATH):
        exit_status, stdout = _pod_show(GOOD_POD_ID)
        assert exit_status == 0

        good_pod_json = file_bytes(GOOD_POD_FILE_PATH)
        assert stdout == good_pod_json


def test_pod_update_from_file():
    with _pod(GOOD_POD_ID, GOOD_POD_FILE_PATH):
        exit_status, stdout = _pod_update_from_file(GOOD_POD_ID,
                                                    UPDATED_GOOD_POD_FILE_PATH,
                                                    force=False)
        assert exit_status == 0
        assert re.fullmatch('Created deployment \S+\n', stdout.decode('utf-8'))

        exit_status, stdout = _pod_show(GOOD_POD_ID)
        assert exit_status == 0

        updated_good_pod_json = file_bytes(UPDATED_GOOD_POD_FILE_PATH)
        assert stdout == updated_good_pod_json


def test_pod_update_from_stdin_force_true():
    with _pod(GOOD_POD_ID, GOOD_POD_FILE_PATH):
        exit_status, stdout = \
            _pod_update_from_stdin(GOOD_POD_ID,
                                   UPDATED_GOOD_POD_FILE_PATH,
                                   force=True)
        assert exit_status == 0
        assert re.fullmatch('Created deployment \S+\n', stdout.decode('utf-8'))

        exit_status, stdout = _pod_show(GOOD_POD_ID)
        assert exit_status == 0

        updated_good_pod_json = file_bytes(UPDATED_GOOD_POD_FILE_PATH)
        assert stdout == updated_good_pod_json


_POD_BASE_CMD = ['dcos', 'marathon', 'pod']
_POD_ADD_CMD = _POD_BASE_CMD + ['add']
_POD_LIST_CMD = _POD_BASE_CMD + ['list']
_POD_REMOVE_CMD = _POD_BASE_CMD + ['remove']
_POD_SHOW_CMD = _POD_BASE_CMD + ['show']
_POD_UPDATE_CMD = _POD_BASE_CMD + ['update']


def _pod_add_from_file(file_path):
    cmd = _POD_ADD_CMD + [file_path]
    exit_status, stdout, stderr = exec_command(cmd)
    return exit_status


def _pod_add_from_stdin(file_path):
    cmd = _POD_ADD_CMD
    exit_status, stdout, stderr = _exec_command_with_stdin(cmd, file_path)
    return exit_status


def _pod_list(json):
    cmd = _POD_LIST_CMD + (['--json'] if json else [])
    exit_status, stdout, stderr = exec_command(cmd)
    return exit_status, stdout


def _pod_remove(pod_id, force):
    cmd = _POD_REMOVE_CMD + _force_args(force) + [pod_id]
    exit_status, stdout, stderr = exec_command(cmd)
    return exit_status


def _pod_show(pod_id):
    cmd = _POD_SHOW_CMD + [pod_id]
    exit_status, stdout, stderr = exec_command(cmd)
    return exit_status, stdout


def _pod_update_from_file(pod_id, file_path, force):
    cmd = _POD_UPDATE_CMD + _force_args(force) + [pod_id, file_path]
    exit_status, stdout, stderr = exec_command(cmd)
    return exit_status, stdout


def _pod_update_from_stdin(pod_id, file_path, force):
    cmd = _POD_UPDATE_CMD + _force_args(force) + [pod_id, file_path]
    exit_status, stdout, stderr = _exec_command_with_stdin(cmd, file_path)
    return exit_status, stdout


def _force_args(force):
    return ['--force'] if force else []


def _exec_command_with_stdin(cmd, file_path):
    with open(file_path) as fd:
        return exec_command(cmd, stdin=fd)


# TODO cruhland: Replace when PR #743 is merged
def _assert_same_elements(list1, list2):
    for element in list1:
        list2.remove(element)
    assert not list2


@contextlib.contextmanager
def _pod(pod_id, file_path):
    exit_status = _pod_add_from_file(file_path)
    pod_added = (exit_status == 0)

    try:
        assert pod_added
        yield
    finally:
        if pod_added:
            exit_status = _pod_remove(pod_id, force=True)
            assert exit_status == 0
