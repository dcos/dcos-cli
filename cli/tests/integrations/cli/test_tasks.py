import collections
import json

import dcos.util as util
from dcos.mesos import Task
from dcos.util import create_schema
from dcoscli.tasks.main import _task_table

import mock
import pytest
from common import (assert_command, exec_command, list_deployments,
                    watch_deployment)

SLEEP1 = 'tests/data/marathon/apps/sleep.json'
SLEEP2 = 'tests/data/marathon/apps/sleep2.json'


@pytest.fixture
def task():
    task = Task({
        "executor_id": "",
        "framework_id": "20150502-231327-16842879-5050-3889-0000",
        "id": "test-app.d44dd7f2-f9b7-11e4-bb43-56847afe9799",
        "labels": [],
        "name": "test-app",
        "resources": {
            "cpus": 0.1,
            "disk": 0,
            "mem": 16,
            "ports": "[31651-31651]"
        },
        "slave_id": "20150513-185808-177048842-5050-1220-S0",
        "state": "TASK_RUNNING",
        "statuses": [
            {
                "state": "TASK_RUNNING",
                "timestamp": 1431552866.52692
            }
        ]
    }, None)

    task.user = mock.Mock(return_value='root')
    return task


def test_help():
    stdout = b"""Get the status of mesos tasks

Usage:
    dcos tasks --info
    dcos tasks [--inactive --json <task>]

Options:
    -h, --help    Show this screen
    --info        Show a short description of this subcommand
    --json        Print json-formatted task data
    --inactive    Show inactive tasks as well
    --version     Show version

Positional Arguments:

    <task>        Only match tasks whose ID matches <task>.  <task> may be
                  a substring of the ID, or a unix glob pattern.
"""
    assert_command(['dcos', 'tasks', '--help'], stdout=stdout)


def test_info():
    stdout = b"Get the status of mesos tasks\n"
    assert_command(['dcos', 'tasks', '--info'], stdout=stdout)


def test_tasks(task):
    _install_sleep_task()

    # test `dcos tasks` output
    returncode, stdout, stderr = exec_command(['dcos', 'tasks', '--json'])

    assert returncode == 0
    assert stderr == b''

    tasks = json.loads(stdout.decode('utf-8'))
    assert isinstance(tasks, collections.Sequence)
    assert len(tasks) == 1

    schema = create_schema(task.dict())
    for task in tasks:
        assert not util.validate_json(task, schema)

    _uninstall_sleep()


def test_tasks_inactive():
    _install_sleep_task()
    _uninstall_sleep()
    _install_sleep_task()

    returncode, stdout, stderr = exec_command(
        ['dcos', 'tasks', '--inactive', '--json'])
    assert returncode == 0
    assert stderr == b''
    assert len(json.loads(stdout.decode('utf-8'))) > 1

    returncode, stdout, stderr = exec_command(
        ['dcos', 'tasks', '--json'])
    assert returncode == 0
    assert stderr == b''
    assert len(json.loads(stdout.decode('utf-8'))) == 1

    _uninstall_sleep()


def test_tasks_none():
    assert_command(['dcos', 'tasks', '--json'],
                   stdout=b'[]\n')


def test_filter(task):
    _install_sleep_task()
    _install_sleep_task(SLEEP2, 'test-app2')

    returncode, stdout, stderr = exec_command(
        ['dcos', 'tasks', 'test-app2', '--json'])

    assert returncode == 0
    assert stderr == b''
    assert len(json.loads(stdout.decode('utf-8'))) == 1

    _uninstall_sleep()
    _uninstall_sleep('test-app2')


# not an integration test
def test_task_table(task):
    table = _task_table([task])
    stdout = b"""\
   NAME    USER  STATE                        ID                      \n\
 test-app  root    R    test-app.d44dd7f2-f9b7-11e4-bb43-56847afe9799 """
    assert str(table).encode('utf-8') == stdout


def _install_sleep_task(app_path=SLEEP1, app_name='test-app'):
    # install helloworld app
    args = ['dcos', 'marathon', 'app', 'add', app_path]
    assert_command(args)
    _wait_for_deployment()


def _wait_for_deployment():
    deps = list_deployments()
    if deps:
        watch_deployment(deps[0]['id'], 60)


def _uninstall_helloworld(args=[]):
    assert_command(['dcos', 'package', 'uninstall', 'helloworld'] + args)


def _uninstall_sleep(app_id='test-app'):
    assert_command(['dcos', 'marathon', 'app', 'remove', app_id])
