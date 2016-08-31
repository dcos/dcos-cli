from .common import exec_command

GOOD_POD_ID = 'good-pod'
GOOD_POD_FILE_PATH = 'tests/data/marathon/pods/good.json'


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
    exit_status = _pod_add_from_file(GOOD_POD_FILE_PATH)
    assert exit_status == 0

    exit_status, stdout = _pod_show(GOOD_POD_ID)
    assert exit_status == 0

    good_pod_json = _read_file(GOOD_POD_FILE_PATH)
    assert stdout == good_pod_json


def test_pod_update_from_file():
    # Add pod, verify that it can be updated
    pass


def test_pod_update_from_file_force_true():
    # Add pod, verify that it can be --force updated
    pass


def test_pod_update_from_stdin():
    # Add pod, verify that it can be updated from spec on stdin
    pass

_POD_BASE_CMD = ['dcos', 'marathon', 'pod']
_POD_ADD_CMD = _POD_BASE_CMD + ['add']
_POD_REMOVE_CMD = _POD_BASE_CMD + ['remove']
_POD_SHOW_CMD = _POD_BASE_CMD + ['show']


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
    force_arg = ['--force'] if force else []
    cmd = _POD_REMOVE_CMD + force_arg + [pod_id]
    exit_status, stdout, stderr = exec_command(cmd)
    return exit_status


def _pod_show(pod_id):
    cmd = _POD_SHOW_CMD + [pod_id]
    exit_status, stdout, stderr = exec_command(cmd)
    return exit_status, stdout


def _read_file(file_path):
    with open(file_path) as fd:
        return fd.read()
