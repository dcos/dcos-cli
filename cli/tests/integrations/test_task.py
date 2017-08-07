import collections
import json
import os
import re
import subprocess
import sys
import time

import pytest

import dcos.util as util
from dcos.util import create_schema

from .helpers.common import (assert_command, assert_lines,
                             assert_lines_range, exec_command)
from .helpers.marathon import (add_app, app, pod, remove_app,
                               watch_all_deployments)
from ..fixtures.task import task_fixture

SLEEP_COMPLETED = 'tests/data/marathon/apps/sleep-completed.json'
SLEEP_COMPLETED1 = 'tests/data/marathon/apps/sleep-completed1.json'
SLEEP1 = 'tests/data/marathon/apps/sleep1.json'
SLEEP2 = 'tests/data/marathon/apps/sleep2.json'
FOLLOW = 'tests/data/file/follow.json'
TWO_TASKS = 'tests/data/file/two_tasks.json'
TWO_TASKS_FOLLOW = 'tests/data/file/two_tasks_follow.json'
LS = 'tests/data/tasks/ls-app.json'

INIT_APPS = ((LS, 'ls-app'),
             (SLEEP1, 'test-app1'),
             (SLEEP2, 'test-app2'))
NUM_TASKS = len(INIT_APPS)


def setup_module():
    # create a completed task
    with app(SLEEP_COMPLETED, 'test-app-completed'):
        pass

    for app_ in INIT_APPS:
        add_app(app_[0])


def teardown_module():
    for app_ in INIT_APPS:
        remove_app(app_[1])


def test_help():
    with open('dcoscli/data/help/task.txt') as content:
        assert_command(['dcos', 'task', '--help'],
                       stdout=content.read().encode('utf-8'))


def test_info():
    stdout = b"Manage DC/OS tasks\n"
    assert_command(['dcos', 'task', '--info'], stdout=stdout)


def test_task():
    # test `dcos task` output
    returncode, stdout, stderr = exec_command(['dcos', 'task', '--json'])

    assert returncode == 0
    assert stderr == b''

    tasks = json.loads(stdout.decode('utf-8'))
    assert isinstance(tasks, collections.Sequence)
    assert len(tasks) == NUM_TASKS

    schema = create_schema(task_fixture().dict(), True)
    schema['required'].remove('labels')

    for task in tasks:
        assert not util.validate_json(task, schema)


def test_task_table():
    assert_lines(['dcos', 'task'], NUM_TASKS + 1)


def test_task_completed():
    assert_lines(
        ['dcos', 'task', '--completed', '--json', 'test-app-completed*'],
        1,
        greater_than=True)


def test_task_all():
    assert_lines(
        ['dcos', 'task', '--json', '*-app*'],
        NUM_TASKS,
        greater_than=True)


def test_task_none():
    assert_command(['dcos', 'task', 'bogus', '--json'],
                   stdout=b'[]\n')


def test_filter():
    assert_lines(['dcos', 'task', 'test-app2', '--json'], 1, greater_than=True)


def test_log_no_files():
    """ Tail stdout on nonexistant task """
    assert_command(['dcos', 'task', 'log', 'bogus'],
                   returncode=1,
                   stderr=b'No matching tasks. Exiting.\n')


def test_log_single_file():
    """ Tail a single file on a single task """
    returncode, stdout, stderr = exec_command(
        ['dcos', 'task', 'log', 'test-app1'])

    assert returncode == 0
    assert stderr == b''
    assert len(stdout.decode('utf-8').split('\n')) > 0


def test_log_pod_task():
    good_pod_file = 'tests/data/marathon/pods/good.json'
    with pod(good_pod_file, 'good-pod'):
        returncode, stdout, stderr = exec_command(
            ['dcos', 'task', 'log', 'good-container', 'stderr'])

        # pod task log are not executor logs, so normal executor stderr
        # logs shouldn't be seen and this pod shouldn't have any logging
        # to stderr
        assert returncode == 0
        assert 'No logs for this task' in str(stderr)
        assert stdout == b'\n'


def test_log_missing_file():
    """ Tail a single file on a single task """
    returncode, stdout, stderr = exec_command(
        ['dcos', 'task', 'log', 'test-app', 'bogus'])

    assert returncode == 1
    assert stdout == b''
    assert stderr == b'No files exist. Exiting.\n'


def test_log_lines():
    """ Test --lines """
    assert_lines(['dcos', 'task', 'log', 'test-app1', '--lines=2'], 2)


def test_log_lines_invalid():
    """ Test invalid --lines value """
    assert_command(['dcos', 'task', 'log', 'test-app1', '--lines=bogus'],
                   stdout=b'',
                   stderr=b'Error parsing string as int\n',
                   returncode=1)


@pytest.mark.skipif(sys.platform == 'win32',
                    reason="Using Windows unsupported import (fcntl)")
def test_log_follow():
    """ Test --follow """
    # verify output
    with app(FOLLOW, 'follow'):
        proc = subprocess.Popen(['dcos', 'task', 'log', 'follow', '--follow'],
                                stdout=subprocess.PIPE)

        # mark stdout as non-blocking, so we can read all available data
        # before EOF
        _mark_non_blocking(proc.stdout)

        time.sleep(10)
        assert len(_read_lines(proc.stdout)) >= 1

        proc.kill()


def test_log_two_tasks():
    """ Test tailing a single file on two separate tasks """
    returncode, stdout, stderr = exec_command(
        ['dcos', 'task', 'log', 'test-app'])

    assert returncode == 0
    assert stderr == b''

    lines = stdout.decode('utf-8').split('\n')
    assert len(lines) == 7
    assert len(
        [line for line in lines if line.startswith('===> task:test-app')]
    ) == 2


@pytest.mark.skipif(sys.platform == 'win32',
                    reason='Using Windows unsupported import (fcntl)')
def test_log_two_tasks_follow():
    """ Test tailing a single file on two separate tasks with --follow """
    with app(TWO_TASKS_FOLLOW, 'two-tasks-follow'):
        proc = subprocess.Popen(
            ['dcos', 'task', 'log', 'two-tasks-follow', '--follow'],
            stdout=subprocess.PIPE)

        # mark stdout as non-blocking, so we can read all available data
        # before EOF
        _mark_non_blocking(proc.stdout)

        time.sleep(5)
        first_lines = _read_lines(proc.stdout)
        time.sleep(3)
        second_lines = _read_lines(proc.stdout)

        assert len(first_lines) >= 1
        # assert there are more lines after sleeping
        assert len(second_lines) >= 1

        proc.kill()


def test_log_completed():
    """ Test `dcos task log --completed` """
    # create a completed task
    # ensure that tail lists nothing
    # ensure that tail --completed lists a completed task
    returncode, stdout, stderr = exec_command(
        ['dcos', 'task', 'log', 'test-app-completed'])

    assert returncode == 1
    assert stdout == b''
    assert stderr.startswith(b'No running tasks match ID [test-app-completed]')

    returncode, stdout, stderr = exec_command(
        ['dcos', 'task', 'log', '--completed', 'test-app-completed'])
    assert returncode == 0
    assert stderr == b''
    assert len(stdout.decode('utf-8').split('\n')) >= 3

    returncode, stdout, stderr = exec_command(
        ['dcos', 'task', 'log', '--all', 'test-app-completed'])
    assert returncode == 0
    assert stderr == b''
    assert len(stdout.decode('utf-8').split('\n')) >= 3


def test_ls_no_params():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'task', 'ls'])

    assert returncode == 0
    assert stderr == b''

    ls_line = '\.ssl.*stderr.*stdout.*'
    lines = stdout.decode('utf-8').split('\n')
    assert len(lines) == 7
    assert re.match('===>.*<===', lines[0])
    assert re.match(ls_line, lines[1])
    assert re.match('===>.*<===', lines[2])
    assert re.match(ls_line, lines[3])
    assert re.match('===>.*<===', lines[4])
    assert re.match(ls_line, lines[5])


def test_ls():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'task', 'ls', 'test-app1'])

    assert returncode == 0
    assert stderr == b''

    ls_line = '\.ssl.*stderr.*stdout.*'
    lines = stdout.decode('utf-8').split('\n')
    assert len(lines) == 2
    assert re.match(ls_line, lines[0])


def test_ls_multiple_tasks():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'task', 'ls', 'test-app'])

    assert returncode == 0
    assert stderr == b''

    ls_line = '\.ssl.*stderr.*stdout.*'
    lines = stdout.decode('utf-8').split('\n')
    assert len(lines) == 5
    assert re.match('===>.*<===', lines[0])
    assert re.match(ls_line, lines[1])
    assert re.match('===>.*<===', lines[2])
    assert re.match(ls_line, lines[3])


def test_ls_long():
    assert_lines_range(['dcos', 'task', 'ls', '--long', 'test-app1'], 5, 7)


def test_ls_path():
    assert_command(['dcos', 'task', 'ls', 'ls-app', 'test'],
                   stdout=b'test1  test2\n')


def test_ls_bad_path():
    assert_command(
        ['dcos', 'task', 'ls', 'test-app1', 'bogus'],
        stderr=b'Cannot access [bogus]: No such file or directory\n',
        returncode=1)


def test_ls_completed():
    with app(SLEEP_COMPLETED1, 'test-app-completed1'):
        task_id_completed = _get_task_id('test-app-completed1')

    returncode, stdout, stderr = exec_command(
        ['dcos', 'task', 'ls', task_id_completed])

    assert returncode == 1
    assert stdout == b''

    err = b'Cannot find a task with ID containing "test-app-completed1'
    assert stderr.startswith(err)

    returncode, stdout, stderr = exec_command(
        ['dcos', 'task', 'ls', '--completed', task_id_completed])

    assert returncode == 0
    assert stderr == b''

    ls_line = '\.ssl.*stderr.*stdout.*'
    lines = stdout.decode('utf-8').split('\n')
    assert len(lines) == 2
    assert re.match(ls_line, lines[0])


def test_exec_non_interactive():
    with open('tests/data/tasks/lorem-ipsum.txt') as text:
        content = text.read()

    task_id = _get_task_id('test-app1')

    with open('tests/data/tasks/lorem-ipsum.txt') as text:
        assert_command(
            ['dcos', 'task', 'exec', task_id, 'printf', content],
            stdout=bytes(content, 'UTF-8'))


def test_exec_interactive():
    with open('tests/data/tasks/lorem-ipsum.txt') as text:
        content = bytes(text.read(), 'UTF-8')

    task_id = _get_task_id('test-app1')

    with open('tests/data/tasks/lorem-ipsum.txt') as text:
        assert_command(
            ['dcos', 'task', 'exec', '--interactive', task_id, 'cat'],
            stdout=content, stdin=text)


def _mark_non_blocking(file_):
    import fcntl
    fcntl.fcntl(file_.fileno(), fcntl.F_SETFL, os.O_NONBLOCK)


def _install_sleep_task(app_path=SLEEP1, app_name='test-app'):
    args = ['dcos', 'marathon', 'app', 'add', app_path]
    assert_command(args)
    watch_all_deployments()


def _uninstall_helloworld(args=[]):
    assert_command(['dcos', 'package', 'uninstall', 'helloworld',
                    '--yes'] + args)


def _uninstall_sleep(app_id='test-app'):
    assert_command(['dcos', 'marathon', 'app', 'remove', app_id])


def _get_task_id(app_id):
    returncode, stdout, stderr = exec_command(
        ['dcos', 'task', '--json', app_id])
    assert returncode == 0
    tasks = json.loads(stdout.decode('utf-8'))
    assert len(tasks) == 1
    task_id = tasks[0]['id']
    return task_id


def _read_lines(raw_io):
    """Polls calls to `read()` on the given byte stream until some bytes are
    returned, or the maximum number of attempts is reached.

    :param raw_io: the byte stream to read from
    :type raw_io: io.RawIOBase
    :returns: the bytes read, decoded as UTF-8 and split into a list of lines
    :rtype: [str]
    """

    for _ in range(30):
        bytes_read = raw_io.read()
        if bytes_read is not None:
            break
        time.sleep(1)
    else:
        assert False, 'timed out trying to read bytes'

    return bytes_read.decode('utf-8').split('\n')
