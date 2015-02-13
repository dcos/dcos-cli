import json

from common import exec_command


def test_help():
    returncode, stdout, stderr = exec_command(['dcos', 'app', '--help'])

    assert returncode == 0
    assert stdout == b"""Usage:
    dcos app add
    dcos app info
    dcos app list
    dcos app remove [--force] <app-id>
    dcos app show [--app-version=<app-version>] <app-id>

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
    assert stdout == b'Deploy and manage applications on Apache Mesos\n'
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


def test_show_app():
    _add_app('tests/data/marathon/zero_instance_sleep.json')
    _show_app('zero-instance-app')
    _remove_app('zero-instance-app')


def test_show_absolute_app_version():
    _add_app('tests/data/marathon/zero_instance_sleep.json')
    _add_app('tests/data/marathon/zero_instance_sleep_v2.json')

    result = _show_app('zero-instance-app')
    _show_app('zero-instance-app', result['version'])

    _remove_app('zero-instance-app')


def test_show_relative_app_version():
    _add_app('tests/data/marathon/zero_instance_sleep.json')
    _add_app('tests/data/marathon/zero_instance_sleep_v2.json')
    _show_app('zero-instance-app', "-1")
    _remove_app('zero-instance-app')


def test_show_missing_relative_app_ersion():
    _add_app('tests/data/marathon/zero_instance_sleep.json')
    _add_app('tests/data/marathon/zero_instance_sleep_v2.json')

    returncode, stdout, stderr = exec_command(
        ['dcos', 'app', 'show', '--app-version=-2', 'zero-instance-app'])

    assert returncode == 1
    assert (stdout ==
            b"Application 'zero-instance-app' only has 2 version(s).\n")
    assert stderr == b''

    _remove_app('zero-instance-app')


def test_show_missing_absolute_app_version():
    _add_app('tests/data/marathon/zero_instance_sleep.json')
    _add_app('tests/data/marathon/zero_instance_sleep_v2.json')

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
    _add_app('tests/data/marathon/zero_instance_sleep_v2.json')

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
    _add_app('tests/data/marathon/zero_instance_sleep_v2.json')

    returncode, stdout, stderr = exec_command(
        ['dcos', 'app', 'show', '--app-version=2', 'zero-instance-app'])

    assert returncode == 1
    assert (stdout == b"Relative versions must be negative: 2\n")
    assert stderr == b''

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
