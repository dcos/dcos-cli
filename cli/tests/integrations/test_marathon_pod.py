import contextlib
import json
import os
import re

from ..common import assert_same_elements
from .common import assert_command, exec_command, file_bytes, file_json

FILE_PATH_BASE = 'tests/data/marathon/pods'

GOOD_POD_ID = 'good-pod'
GOOD_POD_FILE_PATH = os.path.join(FILE_PATH_BASE, 'good.json')
UPDATED_GOOD_POD_FILE_PATH = os.path.join(FILE_PATH_BASE, 'updated_good.json')

DOUBLE_POD_ID = 'double-pod'
DOUBLE_POD_FILE_PATH = os.path.join(FILE_PATH_BASE, 'double.json')

TRIPLE_POD_ID = 'winston'
TRIPLE_POD_FILE_PATH = os.path.join(FILE_PATH_BASE, 'doubleplusgood.json')


def test_pod_add_from_file_then_remove():
    returncode, stdout, stderr = _pod_add_from_file(GOOD_POD_FILE_PATH)
    assert returncode == 0
    assert stdout == b''
    assert stderr == b''

    # Explicitly testing non-forced-removal; can't use the context manager
    _assert_pod_remove(GOOD_POD_ID, extra_args=[])


def test_pod_add_from_stdin_then_force_remove():
    # Explicitly testing adding from stdin; can't use the context manager
    _assert_pod_add_from_stdin(GOOD_POD_FILE_PATH)
    _assert_pod_remove(GOOD_POD_ID, extra_args=['--force'])


def test_pod_list():
    paths = [GOOD_POD_FILE_PATH, DOUBLE_POD_FILE_PATH, TRIPLE_POD_FILE_PATH]
    expected_json = [file_json(path) for path in paths]
    expected_table = file_bytes('tests/unit/data/pod.txt')

    with _pod(GOOD_POD_ID, GOOD_POD_FILE_PATH), \
            _pod(DOUBLE_POD_ID, DOUBLE_POD_FILE_PATH), \
            _pod(TRIPLE_POD_ID, TRIPLE_POD_FILE_PATH):

        _assert_pod_list_json(expected_json)
        _assert_pod_list_table(stdout=expected_table)


def test_pod_show():
    expected_stdout = file_bytes(GOOD_POD_FILE_PATH)

    with _pod(GOOD_POD_ID, GOOD_POD_FILE_PATH):
        _assert_pod_show(GOOD_POD_ID, expected_stdout)


def test_pod_update_from_file():
    expected_show_stdout = file_bytes(UPDATED_GOOD_POD_FILE_PATH)

    with _pod(GOOD_POD_ID, GOOD_POD_FILE_PATH):
        _assert_pod_update_from_file(GOOD_POD_ID,
                                     UPDATED_GOOD_POD_FILE_PATH,
                                     extra_args=[])
        _assert_pod_show(GOOD_POD_ID, expected_show_stdout)


def test_pod_update_from_stdin_force_true():
    expected_show_stdout = file_bytes(UPDATED_GOOD_POD_FILE_PATH)

    with _pod(GOOD_POD_ID, GOOD_POD_FILE_PATH):
        _assert_pod_update_from_stdin(GOOD_POD_ID,
                                      UPDATED_GOOD_POD_FILE_PATH,
                                      extra_args=['--force'])
        _assert_pod_show(GOOD_POD_ID, expected_show_stdout)


_POD_BASE_CMD = ['dcos', 'marathon', 'pod']
_POD_ADD_CMD = _POD_BASE_CMD + ['add']
_POD_LIST_CMD = _POD_BASE_CMD + ['list']
_POD_REMOVE_CMD = _POD_BASE_CMD + ['remove']
_POD_SHOW_CMD = _POD_BASE_CMD + ['show']
_POD_UPDATE_CMD = _POD_BASE_CMD + ['update']


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
    assert stderr

    parsed_stdout = json.loads(stdout.decode('utf-8'))
    assert_same_elements(parsed_stdout, expected_json)


def _assert_pod_list_table(stdout):
    assert_command(_POD_LIST_CMD, returncode=0, stdout=stdout, stderr=b'')


def _assert_pod_remove(pod_id, extra_args):
    cmd = _POD_REMOVE_CMD + [pod_id] + extra_args
    assert_command(cmd, returncode=0, stdout=b'', stderr=b'')


def _assert_pod_show(pod_id, stdout):
    cmd = _POD_SHOW_CMD + [pod_id]
    assert_command(cmd, returncode=0, stdout=stdout, stderr=b'')


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
