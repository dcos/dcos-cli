import json

from common import exec_command


def test_help():
    returncode, stdout, stderr = exec_command(['dcos', 'app', '--help'])

    assert returncode == 0
    assert stdout == b"""Usage:
    dcos app add
    dcos app deployment list [<app-id>]
    dcos app deployment rollback <deployment-id>
    dcos app deployment stop <deployment-id>
    dcos app deployment watch [--max-count=<max-count>] [--interval=<interval>]
         <deployment-id>
    dcos app info
    dcos app list
    dcos app remove [--force] <app-id>
    dcos app restart [--force] <app-id>
    dcos app show [--app-version=<app-version>] <app-id>
    dcos app start [--force] <app-id> [<instances>]
    dcos app stop [--force] <app-id>
    dcos app update [--force] <app-id> [<properties>...]
    dcos app version list [--max-count=<max-count>] <app-id>

Options:
    -h, --help                   Show this screen
    --version                    Show version
    --force                      This flag disable checks in Marathon during
                                 update operations.
    --app-version=<app-version>  This flag specifies the application version to
                                 use for the command. The application version
                                 (<app-version>) can be specified as an
                                 absolute value or as relative value. Absolute
                                 version values must be in ISO8601 date format.
                                 Relative values must be specified as a
                                 negative integer and they represent the
                                 version from the currently deployed
                                 application definition.
    --max-count=<max-count>      Maximum number of entries to try to fetch and
                                 return
    --interval=<interval>        Number of seconds to wait between actions

Positional arguments:
    <app-id>                The application id
    <deployment-id>         The deployment id
    <instances>             The number of instances to start
    <properties>            Optional key-value pairs to be included in the
                            command. The separator between the key and value
                            must be the '=' character. E.g. cpus=2.0
"""
    assert stderr == b''


def test_version():
    returncode, stdout, stderr = exec_command(['dcos', 'app', '--version'])

    assert returncode == 0
    assert stdout == b'dcos-app version 0.1.0\n'
    assert stderr == b''


def test_info():
    returncode, stdout, stderr = exec_command(['dcos', 'app', 'info'])

    assert returncode == 0
    assert stdout == b'Deploy and manage applications on the DCOS\n'
    assert stderr == b''


def test_empty_list():
    _list_apps()


def test_add_app():
    _add_app('tests/data/marathon/zero_instance_sleep.json')
    _list_apps('zero-instance-app')
    _remove_app('zero-instance-app')


def test_remove_app():
    _add_app('tests/data/marathon/zero_instance_sleep.json')
    _remove_app('zero-instance-app')
    _list_apps()


def test_add_bad_json_app():
    with open('tests/data/marathon/bad.json') as fd:
        returncode, stdout, stderr = exec_command(
            ['dcos', 'app', 'add'],
            stdin=fd)

        assert returncode == 1
        assert stdout == b'Error loading JSON.\n'
        assert stderr == b''


def test_add_existing_app():
    _add_app('tests/data/marathon/zero_instance_sleep.json')

    with open('tests/data/marathon/zero_instance_sleep_v2.json') as fd:
        returncode, stdout, stderr = exec_command(
            ['dcos', 'app', 'add'],
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
        ['dcos', 'app', 'show', '--app-version=-2', 'zero-instance-app'])

    assert returncode == 1
    assert (stdout ==
            b"Application 'zero-instance-app' only has 2 version(s).\n")
    assert stderr == b''

    _remove_app('zero-instance-app')


def test_show_missing_absolute_app_version():
    _add_app('tests/data/marathon/zero_instance_sleep.json')
    _update_app(
        'zero-instance-app',
        'tests/data/marathon/update_zero_instance_sleep.json')

    returncode, stdout, stderr = exec_command(
        ['dcos', 'app', 'show', '--app-version=2000-02-11T20:39:32.972Z',
         'zero-instance-app'])

    assert returncode == 1
    assert (stdout ==
            b"Error: App '/zero-instance-app' does not exist\n")
    assert stderr == b''

    _remove_app('zero-instance-app')


def test_show_bad_app_version():
    _add_app('tests/data/marathon/zero_instance_sleep.json')
    _update_app(
        'zero-instance-app',
        'tests/data/marathon/update_zero_instance_sleep.json')

    returncode, stdout, stderr = exec_command(
        ['dcos', 'app', 'show', '--app-version=20:39:32.972Z',
         'zero-instance-app'])

    assert returncode == 1
    assert (stdout ==
            (b'Error: Invalid format: "20:39:32.972Z" is malformed at '
             b'":39:32.972Z"\n'))
    assert stderr == b''

    _remove_app('zero-instance-app')


def test_show_bad_relative_app_version():
    _add_app('tests/data/marathon/zero_instance_sleep.json')
    _update_app(
        'zero-instance-app',
        'tests/data/marathon/update_zero_instance_sleep.json')

    returncode, stdout, stderr = exec_command(
        ['dcos', 'app', 'show', '--app-version=2', 'zero-instance-app'])

    assert returncode == 1
    assert (stdout == b"Relative versions must be negative: 2\n")
    assert stderr == b''

    _remove_app('zero-instance-app')


def test_start_missing_app():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'app', 'start', 'missing-id'])

    assert returncode == 1
    assert stdout == b"Error: App '/missing-id' does not exist\n"
    assert stderr == b''


def test_start_app():
    _add_app('tests/data/marathon/zero_instance_sleep.json')
    _start_app('zero-instance-app')
    _remove_app('zero-instance-app')


def test_start_already_started_app():
    _add_app('tests/data/marathon/zero_instance_sleep.json')
    _start_app('zero-instance-app')

    returncode, stdout, stderr = exec_command(
        ['dcos', 'app', 'start', 'zero-instance-app'])

    assert returncode == 1
    assert (stdout ==
            b"Application 'zero-instance-app' already started: 1 instances.\n")
    assert stderr == b''

    _remove_app('zero-instance-app')


def test_stop_missing_app():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'app', 'stop', 'missing-id'])

    assert returncode == 1
    assert stdout == b"Error: App '/missing-id' does not exist\n"
    assert stderr == b''


def test_stop_app():
    _add_app('tests/data/marathon/zero_instance_sleep.json')
    _start_app('zero-instance-app', 3)
    result = _list_deployments(1, 'zero-instance-app')
    _watch_deployment(result[0]['id'], 60)

    returncode, stdout, stderr = exec_command(
        ['dcos', 'app', 'stop', 'zero-instance-app'])

    assert returncode == 0
    assert stdout.decode().startswith('Created deployment ')
    assert stderr == b''

    _remove_app('zero-instance-app')


def test_stop_already_stopped_app():
    _add_app('tests/data/marathon/zero_instance_sleep.json')

    returncode, stdout, stderr = exec_command(
        ['dcos', 'app', 'stop', 'zero-instance-app'])

    assert returncode == 1
    assert (stdout ==
            b"Application 'zero-instance-app' already stopped: 0 instances.\n")
    assert stderr == b''

    _remove_app('zero-instance-app')


def test_update_missing_app():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'app', 'update', 'missing-id'])

    assert returncode == 1
    assert stdout == b"Error: App '/missing-id' does not exist\n"
    assert stderr == b''


def test_update_missing_field():
    _add_app('tests/data/marathon/zero_instance_sleep.json')

    returncode, stdout, stderr = exec_command(
        ['dcos', 'app', 'update', 'zero-instance-app', 'missing="a string"'])

    assert returncode == 1
    assert stdout.decode('utf-8').startswith(
        "The property 'missing' does not conform to the expected format. "
        "Possible values are: ")
    assert stderr == b''

    _remove_app('zero-instance-app')


def test_update_bad_type():
    _add_app('tests/data/marathon/zero_instance_sleep.json')

    returncode, stdout, stderr = exec_command(
        ['dcos', 'app', 'update', 'zero-instance-app', 'cpus="a string"'])

    assert returncode == 1
    assert stdout.decode('utf-8').startswith(
        "Unable to parse 'a string' as a float: could not convert string to "
        "float: ")
    assert stderr == b''

    _remove_app('zero-instance-app')


def test_update_app():
    _add_app('tests/data/marathon/zero_instance_sleep.json')

    returncode, stdout, stderr = exec_command(
        ['dcos', 'app', 'update', 'zero-instance-app',
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
        ['dcos', 'app', 'restart', 'zero-instance-app'])

    assert returncode == 1
    assert stdout == (
        b"Unable to restart application '/zero-instance-app' "
        b"because it is stopped\n")
    assert stderr == b''

    _remove_app('zero-instance-app')


def test_restarting_missing_app():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'app', 'restart', 'missing-id'])

    assert returncode == 1
    assert stdout == b"Error: App '/missing-id' does not exist\n"
    assert stderr == b''


def test_restarting_app():
    _add_app('tests/data/marathon/zero_instance_sleep.json')
    _start_app('zero-instance-app', 3)
    result = _list_deployments(1, 'zero-instance-app')
    _watch_deployment(result[0]['id'], 60)

    returncode, stdout, stderr = exec_command(
        ['dcos', 'app', 'restart', 'zero-instance-app'])

    assert returncode == 0
    assert stdout.decode().startswith('Created deployment ')
    assert stderr == b''

    _remove_app('zero-instance-app')


def test_list_version_missing_app():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'app', 'version', 'list', 'missing-id'])

    assert returncode == 1
    assert stdout == b"Error: App '/missing-id' does not exist\n"
    assert stderr == b''


def test_list_version_negative_max_count():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'app', 'version', 'list', 'missing-id', '--max-count=-1'])

    assert returncode == 1
    assert stdout == b'Maximum count must be a positive number: -1\n'
    assert stderr == b''


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
        ['dcos', 'app', 'deployment', 'rollback', 'missing-deployment'])

    assert returncode == 1
    assert (stdout ==
            b'Error: DeploymentPlan missing-deployment does not exist\n')
    assert stderr == b''


def test_rollback_deployment():
    _add_app('tests/data/marathon/zero_instance_sleep.json')
    _start_app('zero-instance-app', 3)
    result = _list_deployments(1, 'zero-instance-app')

    returncode, stdout, stderr = exec_command(
        ['dcos', 'app', 'deployment', 'rollback', result[0]['id']])

    assert returncode == 0
    assert stdout == b''
    assert stderr == b''

    _list_deployments(0)

    _remove_app('zero-instance-app')


def test_stop_deployment():
    _add_app('tests/data/marathon/zero_instance_sleep.json')
    _start_app('zero-instance-app', 3)
    result = _list_deployments(1, 'zero-instance-app')

    returncode, stdout, stderr = exec_command(
        ['dcos', 'app', 'deployment', 'stop', result[0]['id']])

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


def _list_apps(app_id=None):
    returncode, stdout, stderr = exec_command(['dcos', 'app', 'list'])

    if app_id is None:
        result = b'No applications to list.\n'
    elif isinstance(app_id, str):
        result = '/{}\n'.format(app_id).encode('utf-8')
    else:
        assert False

    assert returncode == 0
    assert stdout == result
    assert stderr == b''


def _remove_app(app_id):
    returncode, stdout, stderr = exec_command(
        ['dcos', 'app', 'remove', app_id])

    assert returncode == 0
    assert stdout == b''
    assert stderr == b''


def _add_app(file_path):
    with open(file_path) as fd:
        returncode, stdout, stderr = exec_command(
            ['dcos', 'app', 'add'],
            stdin=fd)

        assert returncode == 0
        assert stdout == b''
        assert stderr == b''


def _show_app(app_id, version=None):
    if version is None:
        cmd = ['dcos', 'app', 'show', app_id]
    else:
        cmd = ['dcos', 'app', 'show',
               '--app-version={}'.format(version), app_id]

    returncode, stdout, stderr = exec_command(cmd)

    result = json.loads(stdout.decode('utf-8'))

    assert returncode == 0
    assert isinstance(result, dict)
    assert result['id'] == '/' + app_id
    assert stderr == b''

    return result


def _start_app(app_id, instances=None):
    cmd = ['dcos', 'app', 'start', app_id]
    if instances is not None:
        cmd.append(str(instances))

    returncode, stdout, stderr = exec_command(cmd)

    assert returncode == 0
    assert stdout.decode().startswith('Created deployment ')
    assert stderr == b''


def _update_app(app_id, file_path):
    with open(file_path) as fd:
        returncode, stdout, stderr = exec_command(
            ['dcos', 'app', 'update', app_id],
            stdin=fd)

        assert returncode == 0
        assert stdout == b''
        assert stderr == b''


def _list_versions(app_id, expected_count, max_count=None):
    cmd = ['dcos', 'app', 'version', 'list', app_id]
    if max_count is not None:
        cmd.append('--max-count={}'.format(max_count))

    returncode, stdout, stderr = exec_command(cmd)

    result = json.loads(stdout.decode('utf-8'))

    assert returncode == 0
    assert isinstance(result, list)
    assert len(result) == expected_count
    assert stderr == b''


def _list_deployments(expected_count, app_id=None):
    cmd = ['dcos', 'app', 'deployment', 'list']
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
        ['dcos', 'app', 'deployment', 'watch', '--max-count={}'.format(count),
         deployment_id])

    assert returncode == 0
    assert stderr == b''
