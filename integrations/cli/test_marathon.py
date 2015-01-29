import json
from common import exec_command


def test_help():
    returncode, stdout, stderr = exec_command(['dcos', 'marathon', '--help'])

    assert returncode == 0
    assert stdout == b"""Usage:
    dcos marathon describe [--json] <app_id>
    dcos marathon info
    dcos marathon list
    dcos marathon remove [--force] <app_id>
    dcos marathon scale [--force] <app_id> <instances>
    dcos marathon start <app_resource>
    dcos marathon suspend [--force] <app_id>

Options:
    -h, --help          Show this screen
    --version           Show version
    --force             This flag disable checks in Marathon during update
                        operations.
    --json              Outputs JSON format instead of default (TOML) format
"""


def test_version():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', '--version'])

    assert returncode == 0
    assert stdout == b'dcos-marathon version 0.1.0\n'
    assert stderr == b''


def test_info():
    returncode, stdout, stderr = exec_command(['dcos', 'marathon', 'info'])

    assert returncode == 0
    assert stdout == b'Deploy and manage applications on Apache Mesos\n'
    assert stderr == b''


def test_empty_list():
    _list_apps()


def test_start_app():
    _start_app('tests/data/marathon/sleep.json')
    _list_apps('test-app')
    _remove_app('test-app')


def test_remove_app():
    _start_app('tests/data/marathon/sleep.json')
    _remove_app('test-app')
    _list_apps()


# TODO: Let's improve this once we have a fixed version of toml
def test_describe_app():
    _start_app('tests/data/marathon/sleep.json')

    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'describe', 'test-app'])

    assert returncode == 0
    assert stdout != b''
    assert stderr == b''

    _remove_app('test-app')


def test_describe_app_in_json():
    _start_app('tests/data/marathon/sleep.json')

    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'describe', '--json', 'test-app'])

    result = json.loads(stdout.decode('utf-8'))

    assert returncode == 0
    assert isinstance(result, dict)
    assert result['id'] == '/test-app'
    assert stderr == b''

    _remove_app('test-app')


def test_scale_app():
    _start_app('tests/data/marathon/zero_instance_sleep.json')

    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'scale', 'zero-instance-app', '2'])

    assert returncode == 0
    assert stdout.decode('utf-8').startswith('Created deployment ')
    assert stderr == b''

    _remove_app('zero-instance-app')


def test_force_scale_appp():
    _start_app('tests/data/marathon/sleep.json')

    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'scale', '--force', 'test-app', '2'])

    assert returncode == 0
    assert stdout.decode('utf-8').startswith('Created deployment ')
    assert stderr == b''

    _remove_app('test-app')


def test_suspend_app():
    _start_app('tests/data/marathon/zero_instance_sleep.json')

    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'suspend', 'zero-instance-app'])

    assert returncode == 0
    assert stdout.decode('utf-8').startswith('Created deployment ')
    assert stderr == b''

    _remove_app('zero-instance-app')


def test_remove_missing_app():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'remove', 'missing-id'])

    assert returncode == 1
    assert stdout == b"Error: App '/missing-id' does not exist\n"
    assert stderr == b''


def _start_app(file_path):
    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'start', file_path])

    assert returncode == 0
    assert stdout == b''
    assert stderr == b''


def _list_apps(app_id=None):
    returncode, stdout, stderr = exec_command(['dcos', 'marathon', 'list'])

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
        ['dcos', 'marathon', 'remove', app_id])

    assert returncode == 0
    assert stdout == b''
    assert stderr == b''
