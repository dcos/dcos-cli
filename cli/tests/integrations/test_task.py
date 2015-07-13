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
from dcoscli.task.main import _mesos_files, main

from mock import MagicMock, patch

from ..fixtures.task import task_fixture
from .common import (app, assert_command, assert_lines, assert_mock,
                     exec_command, watch_all_deployments)

SLEEP1 = 'tests/data/marathon/apps/sleep.json'
SLEEP2 = 'tests/data/marathon/apps/sleep2.json'
FOLLOW = 'tests/data/file/follow.json'
TWO_TASKS = 'tests/data/file/two_tasks.json'
TWO_TASKS_FOLLOW = 'tests/data/file/two_tasks_follow.json'


def test_help():
    stdout = b"""Manage DCOS tasks

Usage:
    dcos task --info
    dcos task [--completed --json <task>]
    dcos task log [--completed --follow --lines=N] <task> [<file>]

Options:
    -h, --help    Show this screen
    --info        Show a short description of this subcommand
    --completed   Include completed tasks as well
    --follow      Output data as the file grows
    --json        Print json-formatted tasks
    --lines=N     Output the last N lines [default: 10]
    --version     Show version

Positional Arguments:

    <task>        Only match tasks whose ID matches <task>.  <task> may be
                  a substring of the ID, or a unix glob pattern.

    <file>        Output this file. [default: stdout]
"""
    assert_command(['dcos', 'task', '--help'], stdout=stdout)


def test_info():
    stdout = b"Manage DCOS tasks\n"
    assert_command(['dcos', 'task', '--info'], stdout=stdout)


def test_task():
    _install_sleep_task()

    # test `dcos task` output
    returncode, stdout, stderr = exec_command(['dcos', 'task', '--json'])

    assert returncode == 0
    assert stderr == b''

    tasks = json.loads(stdout.decode('utf-8'))
    assert isinstance(tasks, collections.Sequence)
    assert len(tasks) == 1

    schema = create_schema(task_fixture().dict())
    for task in tasks:
        assert not util.validate_json(task, schema)

    _uninstall_sleep()


def test_task_table():
    _install_sleep_task()
    assert_lines(['dcos', 'task'], 2)
    _uninstall_sleep()


def test_task_completed():
    _install_sleep_task()
    _uninstall_sleep()
    _install_sleep_task()

    returncode, stdout, stderr = exec_command(
        ['dcos', 'task', '--completed', '--json'])
    assert returncode == 0
    assert stderr == b''
    assert len(json.loads(stdout.decode('utf-8'))) > 1

    returncode, stdout, stderr = exec_command(
        ['dcos', 'task', '--json'])
    assert returncode == 0
    assert stderr == b''
    assert len(json.loads(stdout.decode('utf-8'))) == 1

    _uninstall_sleep()


def test_task_none():
    assert_command(['dcos', 'task', '--json'],
                   stdout=b'[]\n')


def test_filter():
    _install_sleep_task()
    _install_sleep_task(SLEEP2, 'test-app2')

    returncode, stdout, stderr = exec_command(
        ['dcos', 'task', 'test-app2', '--json'])

    assert returncode == 0
    assert stderr == b''
    assert len(json.loads(stdout.decode('utf-8'))) == 1

    _uninstall_sleep()
    _uninstall_sleep('test-app2')


def test_log_no_files():
    """ Tail stdout on nonexistant task """
    assert_command(['dcos', 'task', 'log', 'asdf'],
                   returncode=1,
                   stderr=b'No matching tasks. Exiting.\n')


def test_log_single_file():
    """ Tail a single file on a single task """
    with app(SLEEP1, 'test-app', True):
        returncode, stdout, stderr = exec_command(
            ['dcos', 'task', 'log', 'test-app'])

        assert returncode == 0
        assert stderr == b''
        assert len(stdout.decode('utf-8').split('\n')) == 5


def test_log_missing_file():
    """ Tail a single file on a single task """
    with app(SLEEP1, 'test-app', True):
        returncode, stdout, stderr = exec_command(
            ['dcos', 'task', 'log', 'test-app', 'asdf'])

        assert returncode == 1
        assert stdout == b''
        assert stderr == b'No files exist. Exiting.\n'


def test_log_lines():
    """ Test --lines """
    with app(SLEEP1, 'test-app', True):
        assert_lines(['dcos', 'task', 'log', 'test-app', '--lines=2'], 2)


def test_log_lines_invalid():
    """ Test invalid --lines value """
    assert_command(['dcos', 'task', 'log', 'test-app', '--lines=bogus'],
                   stdout=b'',
                   stderr=b'Error parsing string as int\n',
                   returncode=1)


def test_log_follow():
    """ Test --follow """
    with app(FOLLOW, 'follow', True):
        # verify output
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
    with app(TWO_TASKS, 'two-tasks', True):
        returncode, stdout, stderr = exec_command(
            ['dcos', 'task', 'log', 'two-tasks'])

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
    """ Test --completed """
    # create a completed task
    # ensure that tail lists nothing
    # ensure that tail --completed lists a completed task
    with app(SLEEP1, 'test-app', True):
        pass

    assert_command(['dcos', 'task', 'log', 'test-app'],
                   returncode=1,
                   stderr=b'No matching tasks. Exiting.\n',
                   stdout=b'')

    returncode, stdout, stderr = exec_command(
        ['dcos', 'task', 'log', '--completed', 'test-app'])
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
    with app(SLEEP1, 'test-app', True):
        client = mesos.DCOSClient()
        client.get_slave_state = _mock_exception()

        with patch('dcos.mesos.DCOSClient', return_value=client):
            args = ['task', 'log', 'test-app']
            stderr = (b"""Error accessing slave: exception\n"""
                      b"""No matching tasks. Exiting.\n""")
            assert_mock(main, args, returncode=1, stderr=stderr)


def test_log_file_unavailable():
    """ Test a file's read.json being unavailable """
    with app(SLEEP1, 'test-app', True):
        files = _mesos_files(False, "", "stdout")
        assert len(files) == 1
        files[0].read = _mock_exception('exception')

        with patch('dcoscli.task.main._mesos_files', return_value=files):
            args = ['task', 'log', 'test-app']
            stderr = b"No files exist. Exiting.\n"
            assert_mock(main, args, returncode=1, stderr=stderr)


def _mock_exception(contents='exception'):
    return MagicMock(side_effect=DCOSException(contents))


def _mark_non_blocking(file_):
    fcntl.fcntl(file_.fileno(), fcntl.F_SETFL, os.O_NONBLOCK)


def _install_sleep_task(app_path=SLEEP1, app_name='test-app'):
    # install helloworld app
    args = ['dcos', 'marathon', 'app', 'add', app_path]
    assert_command(args)
    watch_all_deployments()


def _uninstall_helloworld(args=[]):
    assert_command(['dcos', 'package', 'uninstall', 'helloworld'] + args)


def _uninstall_sleep(app_id='test-app'):
    assert_command(['dcos', 'marathon', 'app', 'remove', app_id])
