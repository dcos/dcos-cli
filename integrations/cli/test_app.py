from common import exec_command


def test_help():
    returncode, stdout, stderr = exec_command(['dcos', 'app', '--help'])

    assert returncode == 0
    assert stdout == b"""Usage:
    dcos app add
    dcos app info
    dcos app list
    dcos app remove [--force] <app-id>

Options:
    -h, --help          Show this screen
    --version           Show version
    --force             This flag disable checks in Marathon during update
                        operations.
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
