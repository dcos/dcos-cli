import contextlib
import json
import os

from dcos import constants

import pytest

from .common import (app, assert_command, assert_lines, exec_command,
                     list_deployments, show_app, watch_all_deployments,
                     watch_deployment)


def test_help():
    stdout = b"""Deploy and manage applications on the DCOS

Usage:
    dcos marathon --config-schema
    dcos marathon --info
    dcos marathon about
    dcos marathon app add [<app-resource>]
    dcos marathon app list [--json]
    dcos marathon app remove [--force] <app-id>
    dcos marathon app restart [--force] <app-id>
    dcos marathon app show [--app-version=<app-version>] <app-id>
    dcos marathon app start [--force] <app-id> [<instances>]
    dcos marathon app stop [--force] <app-id>
    dcos marathon app update [--force] <app-id> [<properties>...]
    dcos marathon app scale [--force] <app-id> <instances>
    dcos marathon app version list [--max-count=<max-count>] <app-id>
    dcos marathon deployment list [--json <app-id>]
    dcos marathon deployment rollback <deployment-id>
    dcos marathon deployment stop <deployment-id>
    dcos marathon deployment watch [--max-count=<max-count>]
         [--interval=<interval>] <deployment-id>
    dcos marathon task list [--json <app-id>]
    dcos marathon task show <task-id>
    dcos marathon group add [<group-resource>]
    dcos marathon group list [--json]
    dcos marathon group show [--group-version=<group-version>] <group-id>
    dcos marathon group remove [--force] <group-id>
    dcos marathon group update [--force] <group-id> [<properties>...]
    dcos marathon group scale [--force] <group-id> <scale-factor>

Options:
    -h, --help                       Show this screen

    --info                           Show a short description of this
                                     subcommand

     --json                          Print json-formatted tasks

    --version                        Show version

    --force                          This flag disable checks in Marathon
                                     during update operations

    --app-version=<app-version>      This flag specifies the application
                                     version to use for the command. The
                                     application version (<app-version>) can be
                                     specified as an absolute value or as
                                     relative value. Absolute version values
                                     must be in ISO8601 date format. Relative
                                     values must be specified as a negative
                                     integer and they represent the version
                                     from the currently deployed application
                                     definition

    --group-version=<group-version>  This flag specifies the group version to
                                     use for the command. The group version
                                     (<group-version>) can be specified as an
                                     absolute value or as relative value.
                                     Absolute version values must be in ISO8601
                                     date format. Relative values must be
                                     specified as a negative integer and they
                                     represent the version from the currently
                                     deployed group definition

    --config-schema                  Show the configuration schema for the
                                     Marathon subcommand

    --max-count=<max-count>          Maximum number of entries to try to fetch
                                     and return

    --interval=<interval>            Number of seconds to wait between actions

Positional Arguments:
    <app-id>                    The application id

    <app-resource>              Path to a file containing the app's JSON
                                definition. If omitted, the definition is read
                                from stdin. For a detailed description see
                                (https://mesosphere.github.io/
                                marathon/docs/rest-api.html#post-/v2/apps).

    <deployment-id>             The deployment id

    <group-id>                  The group id

    <group-resource>            Path to a file containing the group's JSON
                                definition. If omitted, the definition is read
                                from stdin. For a detailed description see
                                (https://mesosphere.github.io/
                                marathon/docs/rest-api.html#post-/v2/groups).

    <instances>                 The number of instances to start

    <properties>                Must be of the format <key>=<value>. E.g.
                                cpus=2.0. If omitted, properties are read from
                                stdin.

    <task-id>                   The task id

    <scale-factor>              The value of scale-factor for a group
"""
    assert_command(['dcos', 'marathon', '--help'],
                   stdout=stdout)


def test_version():
    assert_command(['dcos', 'marathon', '--version'],
                   stdout=b'dcos-marathon version SNAPSHOT\n')


def test_info():
    assert_command(['dcos', 'marathon', '--info'],
                   stdout=b'Deploy and manage applications on the DCOS\n')


def test_about():
    returncode, stdout, stderr = exec_command(['dcos', 'marathon', 'about'])

    assert returncode == 0
    assert stderr == b''

    result = json.loads(stdout.decode('utf-8'))
    assert result['name'] == "marathon"


@pytest.fixture
def missing_env():
    env = os.environ.copy()
    env.update({
        constants.PATH_ENV: os.environ[constants.PATH_ENV],
        constants.DCOS_CONFIG_ENV:
            os.path.join("tests", "data", "missing_marathon_params.toml")
    })
    return env


def test_missing_config(missing_env):
    assert_command(
        ['dcos', 'marathon', 'app', 'list'],
        returncode=1,
        stderr=(b'Missing required config parameter: "core.dcos_url".  '
                b'Please run `dcos config set core.dcos_url <value>`.\n'),
        env=missing_env)


def test_empty_list():
    _list_apps()


def test_add_app():
    with _zero_instance_app():
        _list_apps('zero-instance-app')


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
    with _zero_instance_app():
        _update_app(
            'zero-instance-app',
            'tests/data/marathon/apps/update_zero_instance_sleep.json')

        stderr = b"Application 'zero-instance-app' only has 2 version(s).\n"
        assert_command(['dcos', 'marathon', 'app', 'show',
                        '--app-version=-2', 'zero-instance-app'],
                       returncode=1,
                       stderr=stderr)


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
        result = list_deployments(1, 'zero-instance-app')
        watch_deployment(result[0]['id'], 60)

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


def test_update_missing_field():
    with _zero_instance_app():
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'app', 'update',
             'zero-instance-app', 'missing="a string"'])

        assert returncode == 1
        assert stdout == b''
        assert stderr.decode('utf-8').startswith(
            "The property 'missing' does not conform to the expected format. "
            "Possible values are: ")


def test_update_bad_type():
    with _zero_instance_app():
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'app', 'update',
             'zero-instance-app', 'cpus="a string"'])

        assert returncode == 1
        assert stderr.decode('utf-8').startswith(
            "Unable to parse 'a string' as a float: could not convert string "
            "to float: ")
        assert stdout == b''


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
        result = list_deployments(1, 'zero-instance-app')
        watch_deployment(result[0]['id'], 60)

        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'app', 'restart', 'zero-instance-app'])

        assert returncode == 0
        assert stdout.decode().startswith('Created deployment ')
        assert stderr == b''


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
    with _zero_instance_app():
        _list_versions('zero-instance-app', 1)

        _update_app(
            'zero-instance-app',
            'tests/data/marathon/apps/update_zero_instance_sleep.json')
        _list_versions('zero-instance-app', 2)


def test_list_version_max_count():
    with _zero_instance_app():
        _update_app(
            'zero-instance-app',
            'tests/data/marathon/apps/update_zero_instance_sleep.json')

        _list_versions('zero-instance-app', 1, 1)
        _list_versions('zero-instance-app', 2, 2)
        _list_versions('zero-instance-app', 2, 3)


def test_list_empty_deployment():
    list_deployments(0)


def test_list_deployment():
    with _zero_instance_app():
        _start_app('zero-instance-app', 3)
        list_deployments(1)


def test_list_deployment_table():
    """Simple sanity check for listing deployments with a table output.
    The more specific testing is done in unit tests.

    """

    with _zero_instance_app():
        _start_app('zero-instance-app', 3)
        assert_lines(['dcos', 'marathon', 'deployment', 'list'], 2)


def test_list_deployment_missing_app():
    with _zero_instance_app():
        _start_app('zero-instance-app')
        list_deployments(0, 'missing-id')


def test_list_deployment_app():
    with _zero_instance_app():
        _start_app('zero-instance-app', 3)
        list_deployments(1, 'zero-instance-app')


def test_rollback_missing_deployment():
    assert_command(
        ['dcos', 'marathon', 'deployment', 'rollback', 'missing-deployment'],
        returncode=1,
        stderr=b'Error: DeploymentPlan missing-deployment does not exist\n')


def test_rollback_deployment():
    with _zero_instance_app():
        _start_app('zero-instance-app', 3)
        result = list_deployments(1, 'zero-instance-app')

        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'deployment', 'rollback', result[0]['id']])

        result = json.loads(stdout.decode('utf-8'))

        assert returncode == 0
        assert 'deploymentId' in result
        assert 'version' in result
        assert stderr == b''

        list_deployments(0)


def test_stop_deployment():
    with _zero_instance_app():
        _start_app('zero-instance-app', 3)
        result = list_deployments(1, 'zero-instance-app')

        assert_command(
            ['dcos', 'marathon', 'deployment', 'stop', result[0]['id']])

        list_deployments(0)


def test_watching_missing_deployment():
    watch_deployment('missing-deployment', 1)


def test_watching_deployment():
    with _zero_instance_app():
        _start_app('zero-instance-app', 3)
        result = list_deployments(1, 'zero-instance-app')
        watch_deployment(result[0]['id'], 60)
        list_deployments(0, 'zero-instance-app')


def test_list_empty_task():
    _list_tasks(0)


def test_list_empty_task_not_running_app():
    with _zero_instance_app():
        _list_tasks(0)


def test_list_tasks():
    with _zero_instance_app():
        _start_app('zero-instance-app', 3)
        result = list_deployments(1, 'zero-instance-app')
        watch_deployment(result[0]['id'], 60)
        _list_tasks(3)


def test_list_tasks_table():
    with _zero_instance_app():
        _start_app('zero-instance-app', 3)
        watch_all_deployments()
        assert_lines(['dcos', 'marathon', 'task', 'list'], 4)


def test_list_app_tasks():
    with _zero_instance_app():
        _start_app('zero-instance-app', 3)
        result = list_deployments(1, 'zero-instance-app')
        watch_deployment(result[0]['id'], 60)
        _list_tasks(3, 'zero-instance-app')


def test_list_missing_app_tasks():
    with _zero_instance_app():
        _start_app('zero-instance-app', 3)
        result = list_deployments(1, 'zero-instance-app')
        watch_deployment(result[0]['id'], 60)
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
        result = list_deployments(1, 'zero-instance-app')
        watch_deployment(result[0]['id'], 60)
        result = _list_tasks(3, 'zero-instance-app')

        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'task', 'show', result[0]['id']])

        result = json.loads(stdout.decode('utf-8'))

        assert returncode == 0
        assert result['appId'] == '/zero-instance-app'
        assert stderr == b''


def test_bad_configuration():
    assert_command(
        ['dcos', 'config', 'set', 'marathon.url', 'http://localhost:88888'])

    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'app', 'list'])

    assert returncode == 1
    assert stdout == b''
    assert stderr.decode().startswith(
        "Marathon likely misconfigured. Please check your proxy or "
        "Marathon URL settings. See dcos config --help. ")

    assert_command(['dcos', 'config', 'unset', 'marathon.url'])


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


def _list_tasks(expected_count, app_id=None):
    cmd = ['dcos', 'marathon', 'task', 'list', '--json']
    if app_id is not None:
        cmd.append(app_id)

    returncode, stdout, stderr = exec_command(cmd)

    result = json.loads(stdout.decode('utf-8'))

    assert returncode == 0
    assert len(result) == expected_count
    assert stderr == b''

    return result


@contextlib.contextmanager
def _zero_instance_app():
    with app('tests/data/marathon/apps/zero_instance_sleep.json',
             'zero-instance-app'):
        yield
