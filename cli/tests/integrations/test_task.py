import collections
import fcntl
import json
import os
import re
import subprocess
import time

import dcos.util as util
from dcos import mesos
from dcos.errors import DCOSException
from dcos.util import create_schema
from dcoscli.task.main import main

from mock import MagicMock, patch

from ..fixtures.task import task_fixture
from .common import (add_app, app, assert_command, assert_lines, assert_mock,
                     exec_command, remove_app, watch_all_deployments)

SLEEP_COMPLETED = 'tests/data/marathon/apps/sleep-completed.json'
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
    with app(SLEEP_COMPLETED, 'test-app-completed', True):
        pass

    for app_ in INIT_APPS:
        add_app(app_[0], True)


def teardown_module():
    for app_ in INIT_APPS:
        remove_app(app_[1])


def test_help():
    stdout = b"""Manage DCOS tasks

Usage:
    dcos task --info
    dcos task [--completed --json <task>]
    dcos task log [--completed --follow --lines=N] <task> [<file>]
    dcos task ls [--long] <task> [<path>]

Options:
    -h, --help    Show this screen
    --info        Show a short description of this subcommand
    --completed   Include completed tasks as well
    --follow      Print data as the file grows
    --json        Print json-formatted tasks
    --lines=N     Print the last N lines [default: 10]
    --long        Use a long listing format
    --version     Show version

Positional Arguments:
    <file>        Print this file. [default: stdout]
    <path>        List this directory. [default: '.']
    <task>        Only match tasks whose ID matches <task>.  <task> may be
                  a substring of the ID, or a unix glob pattern.
"""
    assert_command(['dcos', 'task', '--help'], stdout=stdout)


def test_info():
    stdout = b"Manage DCOS tasks\n"
    assert_command(['dcos', 'task', '--info'], stdout=stdout)


def test_task():
    # test `dcos task` output
    returncode, stdout, stderr = exec_command(['dcos', 'task', '--json'])

    assert returncode == 0
    assert stderr == b''

    tasks = json.loads(stdout.decode('utf-8'))
    assert isinstance(tasks, collections.Sequence)
    assert len(tasks) == NUM_TASKS

    schema = create_schema(task_fixture().dict())
    for task in tasks:
        assert not util.validate_json(task, schema)


def test_task_table():
    assert_lines(['dcos', 'task'], NUM_TASKS+1)


def test_task_completed():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'task', '--completed', '--json'])
    assert returncode == 0
    assert stderr == b''
    assert len(json.loads(stdout.decode('utf-8'))) > NUM_TASKS

    returncode, stdout, stderr = exec_command(
        ['dcos', 'task', '--json'])
    assert returncode == 0
    assert stderr == b''
    assert len(json.loads(stdout.decode('utf-8'))) == NUM_TASKS


def test_task_none():
    assert_command(['dcos', 'task', 'bogus', '--json'],
                   stdout=b'[]\n')


def test_filter():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'task', 'test-app2', '--json'])

    assert returncode == 0
    assert stderr == b''
    assert len(json.loads(stdout.decode('utf-8'))) == 1


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
    assert len(stdout.decode('utf-8').split('\n')) == 5


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


def test_log_follow():
    """ Test --follow """
    # verify output
    with app(FOLLOW, 'follow', True):
        proc = subprocess.Popen(['dcos', 'task', 'log', 'follow', '--follow'],
                                stdout=subprocess.PIPE)

        # mark stdout as non-blocking, so we can read all available data
        # before EOF
        _mark_non_blocking(proc.stdout)

        # wait for data to be output
        time.sleep(1)

        # assert lines before and after sleep
        assert len(proc.stdout.read().decode('utf-8').split('\n')) == 5
        time.sleep(8)
        assert len(proc.stdout.read().decode('utf-8').split('\n')) == 2

        proc.kill()


def test_log_two_tasks():
    """ Test tailing a single file on two separate tasks """
    returncode, stdout, stderr = exec_command(
        ['dcos', 'task', 'log', 'test-app'])

    assert returncode == 0
    assert stderr == b''

    lines = stdout.decode('utf-8').split('\n')
    assert len(lines) == 11
    assert re.match('===>.*<===', lines[0])
    assert re.match('===>.*<===', lines[5])


def test_log_two_tasks_follow():
    """ Test tailing a single file on two separate tasks with --follow """
    with app(TWO_TASKS_FOLLOW, 'two-tasks-follow', True):
        proc = subprocess.Popen(
            ['dcos', 'task', 'log', 'two-tasks-follow', '--follow'],
            stdout=subprocess.PIPE)

        # mark stdout as non-blocking, so we can read all available data
        # before EOF
        _mark_non_blocking(proc.stdout)

        # wait for data to be output
        time.sleep(1)

        # get output before and after the task's sleep
        first_lines = proc.stdout.read().decode('utf-8').split('\n')
        time.sleep(8)
        second_lines = proc.stdout.read().decode('utf-8').split('\n')

        # assert both tasks have printed the expected amount of output
        assert len(first_lines) >= 11
        # assert there is some difference after sleeping
        assert len(second_lines) > 0

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
    assert len(stdout.decode('utf-8').split('\n')) > 4


def test_log_master_unavailable():
    """ Test master's state.json being unavailable """
    client = mesos.DCOSClient()
    client.get_master_state = _mock_exception()

    with patch('dcos.mesos.DCOSClient', return_value=client):
        args = ['task', 'log', '_']
        assert_mock(main, args, returncode=1, stderr=(b"exception\n"))


def test_log_slave_unavailable():
    """ Test slave's state.json being unavailable """
    client = mesos.DCOSClient()
    client.get_slave_state = _mock_exception()

    with patch('dcos.mesos.DCOSClient', return_value=client):
        args = ['task', 'log', 'test-app1']
        stderr = (b"""Error accessing slave: exception\n"""
                  b"""No matching tasks. Exiting.\n""")
        assert_mock(main, args, returncode=1, stderr=stderr)


def test_log_file_unavailable():
    """ Test a file's read.json being unavailable """
    files = [mesos.MesosFile('bogus')]
    files[0].read = _mock_exception('exception')

    with patch('dcoscli.task.main._mesos_files', return_value=files):
        args = ['task', 'log', 'test-app1']
        stderr = b"No files exist. Exiting.\n"
        assert_mock(main, args, returncode=1, stderr=stderr)


def test_ls():
    assert_command(['dcos', 'task', 'ls', 'test-app1'],
                   stdout=b'stderr  stdout\n')


def test_ls_multiple_tasks():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'task', 'ls', 'test-app'])

    assert returncode == 1
    assert stdout == b''
    assert stderr.startswith(b'There are multiple tasks with ID matching '
                             b'[test-app]. Please choose one:\n\t')


def test_ls_long():
    assert_lines(['dcos', 'task', 'ls', '--long', 'test-app1'], 2)


def test_ls_path():
    assert_command(['dcos', 'task', 'ls', 'ls-app', 'test'],
                   stdout=b'test1  test2\n')


def test_ls_bad_path():
    assert_command(
        ['dcos', 'task', 'ls', 'test-app1', 'bogus'],
        stderr=b'Cannot access [bogus]: No such file or directory\n',
        returncode=1)


def _mock_exception(contents='exception'):
    return MagicMock(side_effect=DCOSException(contents))


def _mark_non_blocking(file_):
    fcntl.fcntl(file_.fileno(), fcntl.F_SETFL, os.O_NONBLOCK)


def _install_sleep_task(app_path=SLEEP1, app_name='test-app'):
    args = ['dcos', 'marathon', 'app', 'add', app_path]
    assert_command(args)
    watch_all_deployments()


def _uninstall_helloworld(args=[]):
    assert_command(['dcos', 'package', 'uninstall', 'helloworld'] + args)


def _uninstall_sleep(app_id='test-app'):
    assert_command(['dcos', 'marathon', 'app', 'remove', app_id])
