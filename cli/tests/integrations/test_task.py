import collections
import json

import dcos.util as util
from dcos.util import create_schema

from ..fixtures.task import task_fixture
from .common import (assert_command, assert_lines, exec_command,
                     watch_all_deployments)

SLEEP1 = 'tests/data/marathon/apps/sleep.json'
SLEEP2 = 'tests/data/marathon/apps/sleep2.json'


def test_help():
    stdout = b"""Get the status of DCOS tasks

Usage:
    dcos task --info
    dcos task [--completed --json <task>]

Options:
    -h, --help    Show this screen
    --info        Show a short description of this subcommand
    --json        Print json-formatted tasks
    --completed   Show completed tasks as well
    --version     Show version

Positional Arguments:

    <task>        Only match tasks whose ID matches <task>.  <task> may be
                  a substring of the ID, or a unix glob pattern.
"""
    assert_command(['dcos', 'task', '--help'], stdout=stdout)


def test_info():
    stdout = b"Get the status of DCOS tasks\n"
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


def _install_sleep_task(app_path=SLEEP1, app_name='test-app'):
    # install helloworld app
    args = ['dcos', 'marathon', 'app', 'add', app_path]
    assert_command(args)
    watch_all_deployments()


def _uninstall_helloworld(args=[]):
    assert_command(['dcos', 'package', 'uninstall', 'helloworld'] + args)


def _uninstall_sleep(app_id='test-app'):
    assert_command(['dcos', 'marathon', 'app', 'remove', app_id])
