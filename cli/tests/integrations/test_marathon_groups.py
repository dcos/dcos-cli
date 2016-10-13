import contextlib
import json
import re

from .common import (assert_command, assert_lines, exec_command, remove_group,
                     show_app, watch_all_deployments)

GOOD_GROUP = 'tests/data/marathon/groups/good.json'


def test_deploy_group():
    _deploy_group(GOOD_GROUP)
    remove_group('test-group')


def test_group_list_table():
    with _group(GOOD_GROUP, 'test-group'):
        assert_lines(['dcos', 'marathon', 'group', 'list'], 3)


def test_validate_complicated_group_and_app():
    _deploy_group('tests/data/marathon/groups/complicated.json')
    remove_group('test-group')


def test_optional_deploy_group():
    _deploy_group(GOOD_GROUP, False)
    remove_group('test-group')


def test_add_existing_group():
    with _group(GOOD_GROUP, 'test-group'):
        with open(GOOD_GROUP) as fd:
            stderr = b"Group '/test-group' already exists\n"
            assert_command(['dcos', 'marathon', 'group', 'add'],
                           returncode=1,
                           stderr=stderr,
                           stdin=fd)


def test_show_group():
    with _group(GOOD_GROUP, 'test-group'):
        _show_group('test-group')


def test_add_bad_complicated_group():
    with open('tests/data/marathon/groups/complicated_bad.json') as fd:
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'group', 'add'],
            stdin=fd)

        err = b"""{
  "details": [
    {
      "errors": [
        "error.path.missing"
      ],
      "path": "/groups(0)/apps(0)/id"
    }
  ],
  "message": "Invalid JSON"
}
"""
        assert returncode == 1
        assert stdout == b''
        assert err in stderr


def test_update_group():
    with _group(GOOD_GROUP, 'test-group'):
        newapp = json.dumps([{"id": "appadded", "cmd": "sleep 0"}])
        appjson = "apps={}".format(newapp)
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'group', 'update', 'test-group/sleep',
                appjson])

        assert returncode == 0
        assert stdout.decode().startswith('Created deployment ')
        assert stderr == b''

        watch_all_deployments()
        show_app('test-group/sleep/appadded')


def test_update_group_from_stdin():
    with _group(GOOD_GROUP, 'test-group'):
        _update_group(
            'test-group',
            'tests/data/marathon/groups/update_good.json')
        show_app('test-group/updated')


def test_update_missing_group():
    assert_command(['dcos', 'marathon', 'group', 'update', 'missing-id'],
                   stderr=b"Error: Group '/missing-id' does not exist\n",
                   returncode=1)


def test_scale_group():
    _deploy_group('tests/data/marathon/groups/scale.json')
    returncode, stdout, stderr = exec_command(['dcos', 'marathon', 'group',
                                               'scale', 'scale-group', '2'])
    assert stderr == b''
    assert returncode == 0
    watch_all_deployments()
    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'group', 'show',
         'scale-group'])
    res = json.loads(stdout.decode('utf-8'))

    assert res['groups'][0]['apps'][0]['instances'] == 2
    remove_group('scale-group')


def test_scale_group_not_exist():
    returncode, stdout, stderr = exec_command(['dcos', 'marathon', 'group',
                                               'scale', 'scale-group', '2'])
    assert stderr == b''
    watch_all_deployments()
    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'group', 'show',
         'scale-group'])
    res = json.loads(stdout.decode('utf-8'))

    assert len(res['apps']) == 0
    remove_group('scale-group')


def test_scale_group_when_scale_factor_negative():
    _deploy_group('tests/data/marathon/groups/scale.json')
    returncode, stdout, stderr = exec_command(['dcos', 'marathon', 'group',
                                               'scale', 'scale-group', '-2'])
    assert b'Command not recognized' in stdout
    assert returncode == 1
    watch_all_deployments()
    remove_group('scale-group')


def test_scale_group_when_scale_factor_not_float():
    _deploy_group('tests/data/marathon/groups/scale.json')
    returncode, stdout, stderr = exec_command(['dcos', 'marathon', 'group',
                                               'scale', 'scale-group', '1.a'])
    assert stderr == b'Error parsing string as float\n'
    assert returncode == 1
    watch_all_deployments()
    remove_group('scale-group')


def _deploy_group(file_path, stdin=True):
    if stdin:
        with open(file_path) as fd:
            cmd = ['dcos', 'marathon', 'group', 'add']
            returncode, stdout, stderr = exec_command(cmd, stdin=fd)
            assert returncode == 0
            assert re.fullmatch('Created deployment \S+\n',
                                stdout.decode('utf-8'))
            assert stderr == b''
    else:
        cmd = ['dcos', 'marathon', 'group', 'add', file_path]
        returncode, stdout, stderr = exec_command(cmd)
        assert returncode == 0
        assert re.fullmatch('Created deployment \S+\n', stdout.decode('utf-8'))
        assert stderr == b''

    # Let's make sure that we don't return until the deployment has finished
    watch_all_deployments()


def _show_group(group_id, version=None):
    if version is None:
        cmd = ['dcos', 'marathon', 'group', 'show', group_id]
    else:
        cmd = ['dcos', 'marathon', 'group', 'show',
               '--group-version={}'.format(version), group_id]

    returncode, stdout, stderr = exec_command(cmd)

    result = json.loads(stdout.decode('utf-8'))

    assert returncode == 0
    assert isinstance(result, dict)
    assert result['id'] == '/' + group_id
    assert stderr == b''

    return result


def _update_group(group_id, file_path):
    with open(file_path) as fd:
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'group', 'update', group_id],
            stdin=fd)

        assert returncode == 0
        assert stdout.decode().startswith('Created deployment ')
        assert stderr == b''

    # Let's make sure that we don't return until the deployment has finished
    watch_all_deployments()


@contextlib.contextmanager
def _group(path, group_id):
    """Context manager that deploys a group on entrance, and removes it on
    exit.

    :param path: path to group's json definition
    :type path: str
    :param group_id: group id
    :type group_id: str
    :rtype: None
    """

    _deploy_group(path)
    try:
        yield
    finally:
        remove_group(group_id)
