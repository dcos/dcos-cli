import contextlib
import re

from .common import exec_command

GOOD_POD_ID = 'good-pod'
GOOD_POD_FILE_PATH = 'tests/data/marathon/pods/good.json'
UPDATED_GOOD_POD_FILE_PATH = 'tests/data/marathon/pods/updated_good.json'


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


def test_pod_list():
    # Add several pods, verify that they appear in the list
    pass


def test_pod_list_table():
    # Add several pods, verify that the table view is correct
    pass


def test_pod_show():
    with _pod(GOOD_POD_ID, GOOD_POD_FILE_PATH, add_fn=_pod_add_from_file):
        exit_status, stdout = _pod_show(GOOD_POD_ID)
        assert exit_status == 0

        good_pod_json = _read_file(GOOD_POD_FILE_PATH)
        assert stdout == good_pod_json


def test_pod_update_from_file():
    with _pod(GOOD_POD_ID, GOOD_POD_FILE_PATH, add_fn=_pod_add_from_file):
        exit_status, stdout = _pod_update_from_file(GOOD_POD_ID,
                                                    UPDATED_GOOD_POD_FILE_PATH,
                                                    force=False)
        assert exit_status == 0
        assert re.fullmatch('Created deployment \S+\n', stdout.decode('utf-8'))

        exit_status, stdout = _pod_show(GOOD_POD_ID)
        assert exit_status == 0

        updated_good_pod_json = _read_file(UPDATED_GOOD_POD_FILE_PATH)
        assert stdout == updated_good_pod_json


def test_pod_update_from_stdin_force_true():
    with _pod(GOOD_POD_ID, GOOD_POD_FILE_PATH, add_fn=_pod_add_from_stdin):
        exit_status, stdout = _pod_update_from_file(GOOD_POD_ID,
                                                    UPDATED_GOOD_POD_FILE_PATH,
                                                    force=True)
        assert exit_status == 0
        assert re.fullmatch('Created deployment \S+\n', stdout.decode('utf-8'))

        exit_status, stdout = _pod_show(GOOD_POD_ID)
        assert exit_status == 0

        updated_good_pod_json = _read_file(UPDATED_GOOD_POD_FILE_PATH)
        assert stdout == updated_good_pod_json


_POD_BASE_CMD = ['dcos', 'marathon', 'pod']
_POD_ADD_CMD = _POD_BASE_CMD + ['add']
_POD_REMOVE_CMD = _POD_BASE_CMD + ['remove']
_POD_SHOW_CMD = _POD_BASE_CMD + ['show']
_POD_UPDATE_CMD = _POD_BASE_CMD + ['update']


def _pod_add_from_file(file_path):
    cmd = _POD_ADD_CMD + [file_path]
    exit_status, stdout, stderr = exec_command(cmd)
    return exit_status


def _pod_add_from_stdin(file_path):
    cmd = _POD_ADD_CMD
    with open(file_path) as fd:
        exit_status, stdout, stderr = exec_command(cmd, stdin=fd)
    return exit_status


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


def _read_file(file_path):
    with open(file_path) as fd:
        return fd.read()


def _force_args(force):
    return ['--force'] if force else []


@contextlib.contextmanager
def _pod(pod_id, file_path, add_fn):
    exit_status = add_fn(file_path)
    pod_added = (exit_status == 0)

    try:
        assert pod_added
        yield
    finally:
        if pod_added:
            exit_status = _pod_remove(pod_id, force=True)
            assert exit_status == 0
