import contextlib
import json
import os
import re
import sys
import threading

import pytest
from six.moves.BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

from dcos import constants

from .common import (app, assert_command, assert_lines,
                     exec_command, list_deployments, popen_tty,
                     show_app, update_config, watch_all_deployments,
                     watch_deployment)

_ZERO_INSTANCE_APP_ID = 'zero-instance-app'
_ZERO_INSTANCE_APP_INSTANCES = 100


def test_help():
    with open('tests/data/help/marathon.txt') as content:
        assert_command(['dcos', 'marathon', '--help'],
                       stdout=content.read().encode('utf-8'))


def test_version():
    assert_command(['dcos', 'marathon', '--version'],
                   stdout=b'dcos-marathon version SNAPSHOT\n')


def test_info():
    assert_command(['dcos', 'marathon', '--info'],
                   stdout=b'Deploy and manage applications to DC/OS\n')


def test_about():
    returncode, stdout, stderr = exec_command(['dcos', 'marathon', 'about'])

    assert returncode == 0
    assert stderr == b''

    result = json.loads(stdout.decode('utf-8'))
    assert result['name'] == "marathon"


@pytest.fixture
def env():
    r = os.environ.copy()
    r.update({
        constants.PATH_ENV: os.environ[constants.PATH_ENV],
        constants.DCOS_CONFIG_ENV: os.path.join("tests", "data", "dcos.toml"),
    })

    return r


def test_missing_config(env):
    with update_config("core.dcos_url", None, env):
        assert_command(
            ['dcos', 'marathon', 'app', 'list'],
            returncode=1,
            stderr=(b'Missing required config parameter: "core.dcos_url".  '
                    b'Please run `dcos config set core.dcos_url <value>`.\n'),
            env=env)


def test_empty_list():
    _list_apps()


def test_add_app():
    with _zero_instance_app():
        _list_apps('zero-instance-app')


def test_add_app_through_http():
    with _zero_instance_app_through_http():
        _list_apps('zero-instance-app')


def test_add_app_bad_resource():
    stderr = (b'Can\'t read from resource: bad_resource.\n'
              b'Please check that it exists.\n')
    assert_command(['dcos', 'marathon', 'app', 'add', 'bad_resource'],
                   returncode=1,
                   stderr=stderr)


def test_add_app_with_filename():
    with _zero_instance_app():
        _list_apps('zero-instance-app')


def test_remove_app():
    with _zero_instance_app():
        pass
    _list_apps()


def test_add_bad_json_app():
    with open('tests/data/marathon/apps/bad.json') as fd:
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'app', 'add'],
            stdin=fd)

        assert returncode == 1
        assert stdout == b''
        assert stderr.decode('utf-8').startswith('Error loading JSON: ')


def test_add_existing_app():
    with _zero_instance_app():
        app_path = 'tests/data/marathon/apps/zero_instance_sleep_v2.json'
        with open(app_path) as fd:
            stderr = b"Application '/zero-instance-app' already exists\n"
            assert_command(['dcos', 'marathon', 'app', 'add'],
                           returncode=1,
                           stderr=stderr,
                           stdin=fd)


def test_show_app():
    with _zero_instance_app():
        show_app('zero-instance-app')


def test_show_absolute_app_version():
    with _zero_instance_app():
        _update_app(
            'zero-instance-app',
            'tests/data/marathon/apps/update_zero_instance_sleep.json')

        result = show_app('zero-instance-app')
        show_app('zero-instance-app', result['version'])


def test_show_relative_app_version():
    with _zero_instance_app():
        _update_app(
            'zero-instance-app',
            'tests/data/marathon/apps/update_zero_instance_sleep.json')
        show_app('zero-instance-app', "-1")


def test_show_missing_relative_app_version():
    app_id = _ZERO_INSTANCE_APP_ID

    with _zero_instance_app():
        _update_app(
            app_id,
            'tests/data/marathon/apps/update_zero_instance_sleep.json')

        # Marathon persists app versions indefinitely by ID, so pick a large
        # index here in case the history is long
        cmd = ['dcos', 'marathon', 'app', 'show', '--app-version=-200', app_id]
        returncode, stdout, stderr = exec_command(cmd)

        assert returncode == 1
        assert stdout == b''

        pattern = ("Application 'zero-instance-app' only has [1-9][0-9]* "
                   "version\\(s\\)\\.\n")
        assert re.fullmatch(pattern, stderr.decode('utf-8'), flags=re.DOTALL)


def test_show_missing_absolute_app_version():
    with _zero_instance_app():
        _update_app(
            'zero-instance-app',
            'tests/data/marathon/apps/update_zero_instance_sleep.json')

        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'app', 'show',
             '--app-version=2000-02-11T20:39:32.972Z', 'zero-instance-app'])

        assert returncode == 1
        assert stdout == b''
        assert stderr.decode('utf-8').startswith(
            "Error: App '/zero-instance-app' does not exist")


def test_show_bad_app_version():
    with _zero_instance_app():
        _update_app(
            'zero-instance-app',
            'tests/data/marathon/apps/update_zero_instance_sleep.json')

        stderr = (b'Error: Invalid format: "20:39:32.972Z" is malformed at '
                  b'":39:32.972Z"\n')
        assert_command(
            ['dcos', 'marathon', 'app', 'show', '--app-version=20:39:32.972Z',
             'zero-instance-app'],
            returncode=1,
            stderr=stderr)


def test_show_bad_relative_app_version():
    with _zero_instance_app():
        _update_app(
            'zero-instance-app',
            'tests/data/marathon/apps/update_zero_instance_sleep.json')

        assert_command(
            ['dcos', 'marathon', 'app', 'show',
             '--app-version=2', 'zero-instance-app'],
            returncode=1,
            stderr=b"Relative versions must be negative: 2\n")


def test_start_missing_app():
    assert_command(
        ['dcos', 'marathon', 'app', 'start', 'missing-id'],
        returncode=1,
        stderr=b"Error: App '/missing-id' does not exist\n")


def test_start_app():
    with _zero_instance_app():
        _start_app('zero-instance-app')


def test_start_already_started_app():
    with _zero_instance_app():
        _start_app('zero-instance-app')

        stdout = (b"Application 'zero-instance-app' already "
                  b"started: 1 instances.\n")
        assert_command(
            ['dcos', 'marathon', 'app', 'start', 'zero-instance-app'],
            returncode=1,
            stdout=stdout)


def test_stop_missing_app():
    assert_command(['dcos', 'marathon', 'app', 'stop', 'missing-id'],
                   returncode=1,
                   stderr=b"Error: App '/missing-id' does not exist\n")


def test_stop_app():
    with _zero_instance_app():
        _start_app('zero-instance-app', 3)
        watch_all_deployments()

        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'app', 'stop', 'zero-instance-app'])

        assert returncode == 0
        assert stdout.decode().startswith('Created deployment ')
        assert stderr == b''


def test_stop_already_stopped_app():
    with _zero_instance_app():
        stdout = (b"Application 'zero-instance-app' already "
                  b"stopped: 0 instances.\n")
        assert_command(
            ['dcos', 'marathon', 'app', 'stop', 'zero-instance-app'],
            returncode=1,
            stdout=stdout)


def test_update_missing_app():
    assert_command(['dcos', 'marathon', 'app', 'update', 'missing-id'],
                   stderr=b"Error: App '/missing-id' does not exist\n",
                   returncode=1)


def test_update_bad_type():
    with _zero_instance_app():
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'app', 'update',
             'zero-instance-app', 'cpus="a string"'])

        stderr_end = b"""{
  "details": [
    {
      "errors": [
        "error.expected.jsnumber"
      ],
      "path": "/cpus"
    }
  ],
  "message": "Invalid JSON"
}
"""
        assert returncode == 1
        assert stderr_end in stderr
        assert stdout == b''


def test_update_invalid_request():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'app', 'update', '{', 'instances'])
    assert returncode == 1
    assert stdout == b''
    stderr = stderr.decode()
    # TODO (tamar): this becomes 'Error: App '/{' does not exist\n"'
    # in Marathon 0.11.0
    assert stderr.startswith('Error on request')
    assert stderr.endswith('HTTP 400: Bad Request\n')


def test_app_add_invalid_request():
    path = os.path.join(
        'tests', 'data', 'marathon', 'apps', 'app_add_400.json')

    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'app', 'add', path])

    assert returncode == 1
    assert stdout == b''
    assert re.match(b"Error on request \[POST .*\]: HTTP 400: Bad Request:",
                    stderr)

    stderr_end = b"""{
  "details": [
    {
      "errors": [
        "host is not a valid network type"
      ],
      "path": "/container/docker/network"
    }
  ],
  "message": "Invalid JSON"
}
"""
    assert stderr.endswith(stderr_end)


def test_update_app():
    with _zero_instance_app():
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'app', 'update', 'zero-instance-app',
             'cpus=1', 'mem=20', "cmd='sleep 100'"])

        assert returncode == 0
        assert stdout.decode().startswith('Created deployment ')
        assert stderr == b''


def test_update_app_from_stdin():
    with _zero_instance_app():
        _update_app(
            'zero-instance-app',
            'tests/data/marathon/apps/update_zero_instance_sleep.json')


def test_restarting_stopped_app():
    with _zero_instance_app():
        stdout = (b"Unable to perform rolling restart of application '"
                  b"/zero-instance-app' because it has no running tasks\n")
        assert_command(
            ['dcos', 'marathon', 'app', 'restart', 'zero-instance-app'],
            returncode=1,
            stdout=stdout)


def test_restarting_missing_app():
    assert_command(['dcos', 'marathon', 'app', 'restart', 'missing-id'],
                   returncode=1,
                   stderr=b"Error: App '/missing-id' does not exist\n")


def test_restarting_app():
    with _zero_instance_app():
        _start_app('zero-instance-app', 3)
        watch_all_deployments()
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'app', 'restart', 'zero-instance-app'])

        assert returncode == 0
        assert stdout.decode().startswith('Created deployment ')
        assert stderr == b''


def test_killing_app():
    with _zero_instance_app():
        _start_app('zero-instance-app', 3)
        watch_all_deployments()
        task_set_1 = set([task['id']
                          for task in _list_tasks(3, 'zero-instance-app')])
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'app', 'kill', 'zero-instance-app'])
        assert returncode == 0
        assert stdout.decode().startswith('Killed tasks: ')
        assert stderr == b''
        watch_all_deployments()
        task_set_2 = set([task['id']
                          for task in _list_tasks(app_id='zero-instance-app')])
        assert len(task_set_1.intersection(task_set_2)) == 0


def test_killing_scaling_app():
    with _zero_instance_app():
        _start_app('zero-instance-app', 3)
        watch_all_deployments()
        _list_tasks(3)
        command = ['dcos', 'marathon', 'app', 'kill', '--scale',
                   'zero-instance-app']
        returncode, stdout, stderr = exec_command(command)
        assert returncode == 0
        assert stdout.decode().startswith('Started deployment: ')
        assert stdout.decode().find('version') > -1
        assert stdout.decode().find('deploymentId') > -1
        assert stderr == b''
        watch_all_deployments()
        _list_tasks(0)


def test_killing_with_host_app():
    with _zero_instance_app():
        _start_app('zero-instance-app', 3)
        watch_all_deployments()
        existing_tasks = _list_tasks(3, 'zero-instance-app')
        task_hosts = set([task['host'] for task in existing_tasks])
        if len(task_hosts) <= 1:
            pytest.skip('test needs 2 or more agents to succeed, '
                        'only {} agents available'.format(len(task_hosts)))
        assert len(task_hosts) > 1
        kill_host = list(task_hosts)[0]
        expected_to_be_killed = set([task['id']
                                     for task in existing_tasks
                                     if task['host'] == kill_host])
        not_to_be_killed = set([task['id']
                                for task in existing_tasks
                                if task['host'] != kill_host])
        assert len(not_to_be_killed) > 0
        assert len(expected_to_be_killed) > 0
        command = ['dcos', 'marathon', 'app', 'kill', '--host', kill_host,
                   'zero-instance-app']
        returncode, stdout, stderr = exec_command(command)
        assert stdout.decode().startswith('Killed tasks: ')
        assert stderr == b''
        new_tasks = set([task['id'] for task in _list_tasks()])
        assert not_to_be_killed.intersection(new_tasks) == not_to_be_killed
        assert len(expected_to_be_killed.intersection(new_tasks)) == 0


@pytest.mark.skipif(
    True, reason='https://github.com/mesosphere/marathon/issues/3251')
def test_kill_stopped_app():
    with _zero_instance_app():
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'app', 'kill', 'zero-instance-app'])
        assert returncode == 1
        assert stdout.decode().startswith('Killed tasks: []')


def test_kill_missing_app():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'app', 'kill', 'app'])
    assert returncode == 1
    assert stdout.decode() == ''
    stderr_expected = "Error: App '/app' does not exist"
    assert stderr.decode().strip() == stderr_expected


def test_list_version_missing_app():
    assert_command(
        ['dcos', 'marathon', 'app', 'version', 'list', 'missing-id'],
        returncode=1,
        stderr=b"Error: App '/missing-id' does not exist\n")


def test_list_version_negative_max_count():
    assert_command(['dcos', 'marathon', 'app', 'version', 'list',
                    'missing-id', '--max-count=-1'],
                   returncode=1,
                   stderr=b'Maximum count must be a positive number: -1\n')


def test_list_version_app():
    app_id = _ZERO_INSTANCE_APP_ID

    with _zero_instance_app():
        _list_versions(app_id, 1)

        _update_app(
            app_id,
            'tests/data/marathon/apps/update_zero_instance_sleep.json')
        _list_versions(app_id, 2)


def test_list_version_max_count():
    app_id = _ZERO_INSTANCE_APP_ID

    with _zero_instance_app():
        _update_app(
            app_id,
            'tests/data/marathon/apps/update_zero_instance_sleep.json')

        _list_versions(app_id, 1, 1)
        _list_versions(app_id, 2, 2)
        _list_versions(app_id, 2, 3)


def test_list_empty_deployment():
    list_deployments(0)


def test_list_deployment():
    with _zero_instance_app():
        _start_app('zero-instance-app', _ZERO_INSTANCE_APP_INSTANCES)
        list_deployments(1)


def test_list_deployment_table():
    """Simple sanity check for listing deployments with a table output.
    The more specific testing is done in unit tests.

    """

    with _zero_instance_app():
        _start_app('zero-instance-app', _ZERO_INSTANCE_APP_INSTANCES)
        assert_lines(['dcos', 'marathon', 'deployment', 'list'], 2)


def test_list_deployment_missing_app():
    with _zero_instance_app():
        _start_app('zero-instance-app')
        list_deployments(0, 'missing-id')


def test_list_deployment_app():
    with _zero_instance_app():
        _start_app('zero-instance-app', _ZERO_INSTANCE_APP_INSTANCES)
        list_deployments(1, 'zero-instance-app')


def test_rollback_missing_deployment():
    assert_command(
        ['dcos', 'marathon', 'deployment', 'rollback', 'missing-deployment'],
        returncode=1,
        stderr=b'Error: DeploymentPlan missing-deployment does not exist\n')


def test_rollback_deployment():
    with _zero_instance_app():
        _start_app('zero-instance-app', _ZERO_INSTANCE_APP_INSTANCES)
        result = list_deployments(1, 'zero-instance-app')

        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'deployment', 'rollback', result[0]['id']])

        result = json.loads(stdout.decode('utf-8'))

        assert returncode == 0
        assert 'deploymentId' in result
        assert 'version' in result
        assert stderr == b''

        watch_all_deployments()
        list_deployments(0)


def test_stop_deployment():
    with _zero_instance_app():
        _start_app('zero-instance-app', _ZERO_INSTANCE_APP_INSTANCES)
        result = list_deployments(1, 'zero-instance-app')

        assert_command(
            ['dcos', 'marathon', 'deployment', 'stop', result[0]['id']])

        list_deployments(0)


def test_watching_missing_deployment():
    watch_deployment('missing-deployment', 1)


def test_watching_deployment():
    with _zero_instance_app():
        _start_app('zero-instance-app', _ZERO_INSTANCE_APP_INSTANCES)
        result = list_deployments(1, 'zero-instance-app')
        watch_deployment(result[0]['id'], 60)
        assert_command(
            ['dcos', 'marathon', 'deployment', 'stop', result[0]['id']])
        list_deployments(0, 'zero-instance-app')


def test_list_empty_task():
    _list_tasks(0)


def test_list_empty_task_not_running_app():
    with _zero_instance_app():
        _list_tasks(0)


def test_list_tasks():
    with _zero_instance_app():
        _start_app('zero-instance-app', 3)
        watch_all_deployments()
        _list_tasks(3)


def test_list_tasks_table():
    with _zero_instance_app():
        _start_app('zero-instance-app', 3)
        watch_all_deployments()
        assert_lines(['dcos', 'marathon', 'task', 'list'], 4)


def test_list_app_tasks():
    with _zero_instance_app():
        _start_app('zero-instance-app', 3)
        watch_all_deployments()
        _list_tasks(3, 'zero-instance-app')


def test_list_missing_app_tasks():
    with _zero_instance_app():
        _start_app('zero-instance-app', 3)
        watch_all_deployments()
        _list_tasks(0, 'missing-id')


def test_show_missing_task():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'task', 'show', 'missing-id'])

    stderr = stderr.decode('utf-8')

    assert returncode == 1
    assert stdout == b''
    assert stderr.startswith("Task '")
    assert stderr.endswith("' does not exist\n")


def test_show_task():
    with _zero_instance_app():
        _start_app('zero-instance-app', 3)
        watch_all_deployments()
        result = _list_tasks(3, 'zero-instance-app')

        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'task', 'show', result[0]['id']])

        result = json.loads(stdout.decode('utf-8'))

        assert returncode == 0
        assert result['appId'] == '/zero-instance-app'
        assert stderr == b''


def test_stop_task():
    with _zero_instance_app():
        _start_app('zero-instance-app', 1)
        watch_all_deployments()
        task_list = _list_tasks(1, 'zero-instance-app')
        task_id = task_list[0]['id']

        _stop_task(task_id)


@pytest.mark.skip(reason="https://mesosphere.atlassian.net/browse/DCOS-10325")
def test_stop_task_wipe():
    with _zero_instance_app():
        _start_app('zero-instance-app', 1)
        watch_all_deployments()
        task_list = _list_tasks(1, 'zero-instance-app')
        task_id = task_list[0]['id']

        _stop_task(task_id, '--wipe')


def test_stop_unknown_task():
    with _zero_instance_app():
        _start_app('zero-instance-app')
        watch_all_deployments()
        task_id = 'unknown-task-id'

        _stop_task(task_id, expect_success=False)


def test_stop_unknown_task_wipe():
    with _zero_instance_app():
        _start_app('zero-instance-app')
        watch_all_deployments()
        task_id = 'unknown-task-id'

        _stop_task(task_id, '--wipe', expect_success=False)


def test_bad_configuration(env):
    with update_config('marathon.url', 'http://localhost:88888', env):
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'about'], env=env)

        assert returncode == 1
        assert stdout == b''
        assert stderr.startswith(
            b"URL [http://localhost:88888/v2/info] is unreachable")


def test_app_locked_error():
    with app('tests/data/marathon/apps/sleep_many_instances.json',
             '/sleep-many-instances',
             wait=False):
        stderr = b'Changes blocked: deployment already in progress for app.\n'
        assert_command(
            ['dcos', 'marathon', 'app', 'stop', 'sleep-many-instances'],
            returncode=1,
            stderr=stderr)


@pytest.mark.skipif(sys.platform == 'win32',
                    reason="No pseudo terminal on windows")
def test_app_add_no_tty():
    proc, master = popen_tty('dcos marathon app add')

    stdout, stderr = proc.communicate()
    os.close(master)

    print(stdout)
    print(stderr)

    assert proc.wait() == 1
    assert stdout == b''
    assert stderr == (b"We currently don't support reading from the TTY. "
                      b"Please specify an application JSON.\n"
                      b"E.g.: dcos marathon app add < app_resource.json\n")


def _list_apps(app_id=None):
    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'app', 'list', '--json'])

    result = json.loads(stdout.decode('utf-8'))

    if app_id is None:
        assert len(result) == 0
    else:
        assert len(result) == 1
        assert result[0]['id'] == '/' + app_id

    assert returncode == 0
    assert stderr == b''

    return result


def _start_app(app_id, instances=None):
    cmd = ['dcos', 'marathon', 'app', 'start', app_id]
    if instances is not None:
        cmd.append(str(instances))

    returncode, stdout, stderr = exec_command(cmd)

    assert returncode == 0
    assert stdout.decode().startswith('Created deployment ')
    assert stderr == b''


def _update_app(app_id, file_path):
    with open(file_path) as fd:
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'app', 'update', app_id],
            stdin=fd)

        assert returncode == 0
        assert stdout.decode().startswith('Created deployment ')
        assert stderr == b''


def _list_versions(app_id, expected_min_count, max_count=None):
    cmd = ['dcos', 'marathon', 'app', 'version', 'list', app_id]
    if max_count is not None:
        cmd.append('--max-count={}'.format(max_count))

    returncode, stdout, stderr = exec_command(cmd)

    result = json.loads(stdout.decode('utf-8'))

    assert returncode == 0
    assert isinstance(result, list)
    assert stderr == b''

    # Marathon persists app versions indefinitely by ID, so there may be extras
    assert len(result) >= expected_min_count

    if max_count is not None:
        assert len(result) <= max_count


def _list_tasks(expected_count=None, app_id=None):
    cmd = ['dcos', 'marathon', 'task', 'list', '--json']
    if app_id is not None:
        cmd.append(app_id)

    returncode, stdout, stderr = exec_command(cmd)

    result = json.loads(stdout.decode('utf-8'))

    assert returncode == 0
    if expected_count:
        assert len(result) == expected_count
    assert stderr == b''

    return result


def _stop_task(task_id, wipe=None, expect_success=True):
    cmd = ['dcos', 'marathon', 'task', 'stop', task_id]
    if wipe is not None:
        cmd.append('--wipe')

    returncode, stdout, stderr = exec_command(cmd)

    if expect_success:
        assert returncode == 0
        assert stderr == b''
        result = json.loads(stdout.decode('utf-8'))
        assert result['id'] == task_id
    else:
        assert returncode == 1


@contextlib.contextmanager
def _zero_instance_app():
    with app('tests/data/marathon/apps/zero_instance_sleep.json',
             'zero-instance-app'):
        yield


@contextlib.contextmanager
def _zero_instance_app_through_http():
    class JSONRequestHandler (BaseHTTPRequestHandler):

        def do_GET(self):  # noqa: N802
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(open(
                'tests/data/marathon/apps/zero_instance_sleep.json',
                'rb').read())

    host = 'localhost'
    port = 12345
    server = HTTPServer((host, port), JSONRequestHandler)
    thread = threading.Thread(target=server.serve_forever)
    thread.setDaemon(True)
    thread.start()

    with app('http://{}:{}'.format(host, port), 'zero-instance-app'):
        try:
            yield
        finally:
            server.shutdown()
