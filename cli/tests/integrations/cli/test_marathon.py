import json

from common import exec_command


def test_help():
    returncode, stdout, stderr = exec_command(['dcos', 'marathon', '--help'])

    assert returncode == 0
    assert stdout == b"""Deploy and manage applications on the DCOS

Usage:
    dcos marathon --config-schema
    dcos marathon app add [<app-resource>]
    dcos marathon app list
    dcos marathon app remove [--force] <app-id>
    dcos marathon app restart [--force] <app-id>
    dcos marathon app show [--app-version=<app-version>] <app-id>
    dcos marathon app start [--force] <app-id> [<instances>]
    dcos marathon app stop [--force] <app-id>
    dcos marathon app update [--force] <app-id> [<properties>...]
    dcos marathon app version list [--max-count=<max-count>] <app-id>
    dcos marathon deployment list [<app-id>]
    dcos marathon deployment rollback <deployment-id>
    dcos marathon deployment stop <deployment-id>
    dcos marathon deployment watch [--max-count=<max-count>]
         [--interval=<interval>] <deployment-id>
    dcos marathon info
    dcos marathon task list [<app-id>]
    dcos marathon task show <task-id>

Options:
    -h, --help                   Show this screen
    --version                    Show version
    --force                      This flag disable checks in Marathon during
                                 update operations
    --app-version=<app-version>  This flag specifies the application version to
                                 use for the command. The application version
                                 (<app-version>) can be specified as an
                                 absolute value or as relative value. Absolute
                                 version values must be in ISO8601 date format.
                                 Relative values must be specified as a
                                 negative integer and they represent the
                                 version from the currently deployed
                                 application definition
    --config-schema              Show the configuration schema for the Marathon
                                 subcommand
    --max-count=<max-count>      Maximum number of entries to try to fetch and
                                 return
    --interval=<interval>        Number of seconds to wait between actions

Positional arguments:
    <app-id>                    The application id
    <app-resource>              The application resource; for a detailed
                                description see (https://mesosphere.github.io/
                                marathon/docs/rest-api.html#post-/v2/apps)
    <deployment-id>             The deployment id
    <instances>                 The number of instances to start
    <properties>                Optional key-value pairs to be included in the
                                command. The separator between the key and
                                value must be the '=' character. E.g. cpus=2.0
    <task-id>                   The task id
"""
    assert stderr == b''


def test_version():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', '--version'])

    assert returncode == 0
    assert stdout == b'dcos-marathon version 0.1.0\n'
    assert stderr == b''


def test_info():
    returncode, stdout, stderr = exec_command(['dcos', 'marathon', 'info'])

    assert returncode == 0
    assert stdout == b'Deploy and manage applications on the DCOS\n'
    assert stderr == b''


def test_empty_list():
    _list_apps()


def test_add_app():
    _add_app('tests/data/marathon/zero_instance_sleep.json')
    _list_apps('zero-instance-app')
    _remove_app('zero-instance-app')


def test_optional_add_app():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'app', 'add',
            'tests/data/marathon/zero_instance_sleep.json'])

    assert returncode == 0
    assert stdout == b''
    assert stderr == b''

    _list_apps('zero-instance-app')
    _remove_app('zero-instance-app')


def test_remove_app():
    _add_app('tests/data/marathon/zero_instance_sleep.json')
    _remove_app('zero-instance-app')
    _list_apps()


def test_add_bad_json_app():
    with open('tests/data/marathon/bad.json') as fd:
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'app', 'add'],
            stdin=fd)

        assert returncode == 1
        assert stdout == b''
        assert stderr == b'Error loading JSON.\n'


def test_add_existing_app():
    _add_app('tests/data/marathon/zero_instance_sleep.json')

    with open('tests/data/marathon/zero_instance_sleep_v2.json') as fd:
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'app', 'add'],
            stdin=fd)

        assert returncode == 1
        assert stdout == b"Application '/zero-instance-app' already exists\n"
        assert stderr == b''

    _remove_app('zero-instance-app')


def test_show_app():
    _add_app('tests/data/marathon/zero_instance_sleep.json')
    _show_app('zero-instance-app')
    _remove_app('zero-instance-app')


def test_show_absolute_app_version():
    _add_app('tests/data/marathon/zero_instance_sleep.json')
    _update_app(
        'zero-instance-app',
        'tests/data/marathon/update_zero_instance_sleep.json')

    result = _show_app('zero-instance-app')
    _show_app('zero-instance-app', result['version'])

    _remove_app('zero-instance-app')


def test_show_relative_app_version():
    _add_app('tests/data/marathon/zero_instance_sleep.json')
    _update_app(
        'zero-instance-app',
        'tests/data/marathon/update_zero_instance_sleep.json')
    _show_app('zero-instance-app', "-1")
    _remove_app('zero-instance-app')


def test_show_missing_relative_app_version():
    _add_app('tests/data/marathon/zero_instance_sleep.json')
    _update_app(
        'zero-instance-app',
        'tests/data/marathon/update_zero_instance_sleep.json')

    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'app', 'show',
            '--app-version=-2', 'zero-instance-app'])

    assert returncode == 1
    assert stdout == b''
    assert (stderr ==
            b"Application 'zero-instance-app' only has 2 version(s).\n")

    _remove_app('zero-instance-app')


def test_show_missing_absolute_app_version():
    _add_app('tests/data/marathon/zero_instance_sleep.json')
    _update_app(
        'zero-instance-app',
        'tests/data/marathon/update_zero_instance_sleep.json')

    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'app', 'show',
            '--app-version=2000-02-11T20:39:32.972Z', 'zero-instance-app'])

    assert returncode == 1
    assert stdout == b''
    assert stderr.decode('utf-8').startswith(
        "Error: App '/zero-instance-app' does not exist")

    _remove_app('zero-instance-app')


def test_show_bad_app_version():
    _add_app('tests/data/marathon/zero_instance_sleep.json')
    _update_app(
        'zero-instance-app',
        'tests/data/marathon/update_zero_instance_sleep.json')

    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'app', 'show', '--app-version=20:39:32.972Z',
         'zero-instance-app'])

    assert returncode == 1
    assert stdout == b''
    assert (stderr ==
            (b'Error: Invalid format: "20:39:32.972Z" is malformed at '
             b'":39:32.972Z"\n'))

    _remove_app('zero-instance-app')


def test_show_bad_relative_app_version():
    _add_app('tests/data/marathon/zero_instance_sleep.json')
    _update_app(
        'zero-instance-app',
        'tests/data/marathon/update_zero_instance_sleep.json')

    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'app', 'show',
            '--app-version=2', 'zero-instance-app'])

    assert returncode == 1
    assert stdout == b''
    assert (stderr == b"Relative versions must be negative: 2\n")

    _remove_app('zero-instance-app')


def test_start_missing_app():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'app', 'start', 'missing-id'])

    assert returncode == 1
    assert stdout == b''
    assert stderr == b"Error: App '/missing-id' does not exist\n"


def test_start_app():
    _add_app('tests/data/marathon/zero_instance_sleep.json')
    _start_app('zero-instance-app')
    _remove_app('zero-instance-app')


def test_start_already_started_app():
    _add_app('tests/data/marathon/zero_instance_sleep.json')
    _start_app('zero-instance-app')

    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'app', 'start', 'zero-instance-app'])

    assert returncode == 1
    assert (stdout ==
            b"Application 'zero-instance-app' already started: 1 instances.\n")
    assert stderr == b''

    _remove_app('zero-instance-app')


def test_stop_missing_app():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'app', 'stop', 'missing-id'])

    assert returncode == 1
    assert stdout == b''
    assert stderr == b"Error: App '/missing-id' does not exist\n"


def test_stop_app():
    _add_app('tests/data/marathon/zero_instance_sleep.json')
    _start_app('zero-instance-app', 3)
    result = _list_deployments(1, 'zero-instance-app')
    _watch_deployment(result[0]['id'], 60)

    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'app', 'stop', 'zero-instance-app'])

    assert returncode == 0
    assert stdout.decode().startswith('Created deployment ')
    assert stderr == b''

    _remove_app('zero-instance-app')


def test_stop_already_stopped_app():
    _add_app('tests/data/marathon/zero_instance_sleep.json')

    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'app', 'stop', 'zero-instance-app'])

    assert returncode == 1
    assert (stdout ==
            b"Application 'zero-instance-app' already stopped: 0 instances.\n")
    assert stderr == b''

    _remove_app('zero-instance-app')


def test_update_missing_app():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'app', 'update', 'missing-id'])

    assert returncode == 1
    assert stdout == b''
    assert stderr == b"Error: App '/missing-id' does not exist\n"


def test_update_missing_field():
    _add_app('tests/data/marathon/zero_instance_sleep.json')

    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'app', 'update',
            'zero-instance-app', 'missing="a string"'])

    assert returncode == 1
    assert stdout == b''
    assert stderr.decode('utf-8').startswith(
        "The property 'missing' does not conform to the expected format. "
        "Possible values are: ")

    _remove_app('zero-instance-app')


def test_update_bad_type():
    _add_app('tests/data/marathon/zero_instance_sleep.json')

    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'app', 'update',
            'zero-instance-app', 'cpus="a string"'])

    assert returncode == 1
    assert stderr.decode('utf-8').startswith(
        "Unable to parse 'a string' as a float: could not convert string to "
        "float: ")
    assert stdout == b''

    _remove_app('zero-instance-app')


def test_update_app():
    _add_app('tests/data/marathon/zero_instance_sleep.json')

    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'app', 'update', 'zero-instance-app',
         'cpus=1', 'mem=20', "cmd='sleep 100'"])

    assert returncode == 0
    assert stdout.decode().startswith('Created deployment ')
    assert stderr == b''

    _remove_app('zero-instance-app')


def test_update_app_from_stdin():
    _add_app('tests/data/marathon/zero_instance_sleep.json')
    _update_app(
        'zero-instance-app',
        'tests/data/marathon/update_zero_instance_sleep.json')

    _remove_app('zero-instance-app')


def test_restarting_stopped_app():
    _add_app('tests/data/marathon/zero_instance_sleep.json')

    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'app', 'restart', 'zero-instance-app'])

    assert returncode == 1
    assert stdout == (
        b"Unable to restart application '/zero-instance-app' "
        b"because it is stopped\n")
    assert stderr == b''

    _remove_app('zero-instance-app')


def test_restarting_missing_app():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'app', 'restart', 'missing-id'])

    assert returncode == 1
    assert stdout == b''
    assert stderr == b"Error: App '/missing-id' does not exist\n"


def test_restarting_app():
    _add_app('tests/data/marathon/zero_instance_sleep.json')
    _start_app('zero-instance-app', 3)
    result = _list_deployments(1, 'zero-instance-app')
    _watch_deployment(result[0]['id'], 60)

    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'app', 'restart', 'zero-instance-app'])

    assert returncode == 0
    assert stdout.decode().startswith('Created deployment ')
    assert stderr == b''

    _remove_app('zero-instance-app')


def test_list_version_missing_app():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'app', 'version', 'list', 'missing-id'])

    assert returncode == 1
    assert stdout == b''
    assert stderr == b"Error: App '/missing-id' does not exist\n"


def test_list_version_negative_max_count():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'app', 'version', 'list',
            'missing-id', '--max-count=-1'])

    assert returncode == 1
    assert stdout == b''
    assert stderr == b'Maximum count must be a positive number: -1\n'


def test_list_version_app():
    _add_app('tests/data/marathon/zero_instance_sleep.json')
    _list_versions('zero-instance-app', 1)

    _update_app(
        'zero-instance-app',
        'tests/data/marathon/update_zero_instance_sleep.json')
    _list_versions('zero-instance-app', 2)

    _remove_app('zero-instance-app')


def test_list_version_max_count():
    _add_app('tests/data/marathon/zero_instance_sleep.json')
    _update_app(
        'zero-instance-app',
        'tests/data/marathon/update_zero_instance_sleep.json')

    _list_versions('zero-instance-app', 1, 1)
    _list_versions('zero-instance-app', 2, 2)
    _list_versions('zero-instance-app', 2, 3)

    _remove_app('zero-instance-app')


def test_list_empty_deployment():
    _list_deployments(0)


def test_list_deployment():
    _add_app('tests/data/marathon/zero_instance_sleep.json')
    _start_app('zero-instance-app', 3)
    _list_deployments(1)
    _remove_app('zero-instance-app')


def test_list_deployment_missing_app():
    _add_app('tests/data/marathon/zero_instance_sleep.json')
    _start_app('zero-instance-app')
    _list_deployments(0, 'missing-id')
    _remove_app('zero-instance-app')


def test_list_deployment_app():
    _add_app('tests/data/marathon/zero_instance_sleep.json')
    _start_app('zero-instance-app', 3)
    _list_deployments(1, 'zero-instance-app')
    _remove_app('zero-instance-app')


def test_rollback_missing_deployment():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'deployment', 'rollback', 'missing-deployment'])

    assert returncode == 1
    assert stdout == b''
    assert (stderr ==
            b'Error: DeploymentPlan missing-deployment does not exist\n')


def test_rollback_deployment():
    _add_app('tests/data/marathon/zero_instance_sleep.json')
    _start_app('zero-instance-app', 3)
    result = _list_deployments(1, 'zero-instance-app')

    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'deployment', 'rollback', result[0]['id']])

    result = json.loads(stdout.decode('utf-8'))

    assert returncode == 0
    assert 'deploymentId' in result
    assert 'version' in result
    assert stderr == b''

    _list_deployments(0)

    _remove_app('zero-instance-app')


def test_stop_deployment():
    _add_app('tests/data/marathon/zero_instance_sleep.json')
    _start_app('zero-instance-app', 3)
    result = _list_deployments(1, 'zero-instance-app')

    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'deployment', 'stop', result[0]['id']])

    assert returncode == 0
    assert stdout == b''
    assert stderr == b''

    _list_deployments(0)

    _remove_app('zero-instance-app')


def test_watching_missing_deployment():
    _watch_deployment('missing-deployment', 1)


def test_watching_deployment():
    _add_app('tests/data/marathon/zero_instance_sleep.json')
    _start_app('zero-instance-app', 3)
    result = _list_deployments(1, 'zero-instance-app')
    _watch_deployment(result[0]['id'], 60)
    _list_deployments(0, 'zero-instance-app')
    _remove_app('zero-instance-app')


def test_list_empty_task():
    _list_tasks(0)


def test_list_empty_task_not_running_app():
    _add_app('tests/data/marathon/zero_instance_sleep.json')
    _list_tasks(0)
    _remove_app('zero-instance-app')


def test_list_tasks():
    _add_app('tests/data/marathon/zero_instance_sleep.json')
    _start_app('zero-instance-app', 3)
    result = _list_deployments(1, 'zero-instance-app')
    _watch_deployment(result[0]['id'], 60)
    _list_tasks(3)
    _remove_app('zero-instance-app')


def test_list_app_tasks():
    _add_app('tests/data/marathon/zero_instance_sleep.json')
    _start_app('zero-instance-app', 3)
    result = _list_deployments(1, 'zero-instance-app')
    _watch_deployment(result[0]['id'], 60)
    _list_tasks(3, 'zero-instance-app')
    _remove_app('zero-instance-app')


def test_list_missing_app_tasks():
    _add_app('tests/data/marathon/zero_instance_sleep.json')
    _start_app('zero-instance-app', 3)
    result = _list_deployments(1, 'zero-instance-app')
    _watch_deployment(result[0]['id'], 60)
    _list_tasks(0, 'missing-id')
    _remove_app('zero-instance-app')


def test_show_missing_task():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'task', 'show', 'missing-id'])

    stderr = stderr.decode('utf-8')

    assert returncode == 1
    assert stdout == b''
    assert stderr.startswith("Task '")
    assert stderr.endswith("' does not exist\n")


def test_show_task():
    _add_app('tests/data/marathon/zero_instance_sleep.json')
    _start_app('zero-instance-app', 3)
    result = _list_deployments(1, 'zero-instance-app')
    _watch_deployment(result[0]['id'], 60)
    result = _list_tasks(3, 'zero-instance-app')

    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'task', 'show', result[0]['id']])

    result = json.loads(stdout.decode('utf-8'))

    assert returncode == 0
    assert result['appId'] == '/zero-instance-app'
    assert stderr == b''

    _remove_app('zero-instance-app')


def _list_apps(app_id=None):
    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'app', 'list'])

    result = json.loads(stdout.decode('utf-8'))

    if app_id is None:
        assert len(result) == 0
    else:
        assert len(result) == 1
        assert result[0]['id'] == '/' + app_id

    assert returncode == 0
    assert stderr == b''

    return result


def _remove_app(app_id):
    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'app', 'remove', app_id])

    assert returncode == 0
    assert stdout == b''
    assert stderr == b''


def _add_app(file_path):
    with open(file_path) as fd:
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'app', 'add'],
            stdin=fd)

        assert returncode == 0
        assert stdout == b''
        assert stderr == b''


def _show_app(app_id, version=None):
    if version is None:
        cmd = ['dcos', 'marathon', 'app', 'show', app_id]
    else:
        cmd = ['dcos', 'marathon', 'app', 'show',
               '--app-version={}'.format(version), app_id]

    returncode, stdout, stderr = exec_command(cmd)

    result = json.loads(stdout.decode('utf-8'))

    assert returncode == 0
    assert isinstance(result, dict)
    assert result['id'] == '/' + app_id
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
        assert stdout == b''
        assert stderr == b''


def _list_versions(app_id, expected_count, max_count=None):
    cmd = ['dcos', 'marathon', 'app', 'version', 'list', app_id]
    if max_count is not None:
        cmd.append('--max-count={}'.format(max_count))

    returncode, stdout, stderr = exec_command(cmd)

    result = json.loads(stdout.decode('utf-8'))

    assert returncode == 0
    assert isinstance(result, list)
    assert len(result) == expected_count
    assert stderr == b''


def _list_deployments(expected_count, app_id=None):
    cmd = ['dcos', 'marathon', 'deployment', 'list']
    if app_id is not None:
        cmd.append(app_id)

    returncode, stdout, stderr = exec_command(cmd)

    result = json.loads(stdout.decode('utf-8'))

    assert returncode == 0
    assert len(result) == expected_count
    assert stderr == b''

    return result


def _watch_deployment(deployment_id, count):
    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'deployment', 'watch',
            '--max-count={}'.format(count), deployment_id])

    assert returncode == 0
    assert stderr == b''


def _list_tasks(expected_count, app_id=None):
    cmd = ['dcos', 'marathon', 'task', 'list']
    if app_id is not None:
        cmd.append(app_id)

    returncode, stdout, stderr = exec_command(cmd)

    result = json.loads(stdout.decode('utf-8'))

    assert returncode == 0
    assert len(result) == expected_count
    assert stderr == b''

    return result
