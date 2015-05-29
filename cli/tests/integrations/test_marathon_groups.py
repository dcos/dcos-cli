import json

from .common import (assert_command, assert_lines, exec_command,
                     list_deployments, watch_all_deployments, watch_deployment)


def test_add_group():
    _add_group('tests/data/marathon/groups/good.json')
    _list_groups('test-group/sleep/goodnight')
    result = list_deployments(None, 'test-group/sleep/goodnight')
    if len(result) != 0:
        watch_deployment(result[0]['id'], 60)
    _remove_group('test-group')


def test_group_list_table():
    _add_group('tests/data/marathon/groups/good.json')
    watch_all_deployments()
    assert_lines(['dcos', 'marathon', 'group', 'list'], 3)
    _remove_group('test-group')


def test_validate_complicated_group_and_app():
    _add_group('tests/data/marathon/groups/complicated.json')
    result = list_deployments(None, 'test-group/moregroups/moregroups/sleep1')
    if len(result) != 0:
        watch_deployment(result[0]['id'], 60)
    _remove_group('test-group')


def test_optional_add_group():
    assert_command(['dcos', 'marathon', 'group', 'add',
                    'tests/data/marathon/groups/good.json'])

    _list_groups('test-group/sleep/goodnight')
    result = list_deployments(None, 'test-group/sleep/goodnight')
    if len(result) != 0:
        watch_deployment(result[0]['id'], 60)
    _remove_group('test-group')


def test_add_existing_group():
    _add_group('tests/data/marathon/groups/good.json')

    result = list_deployments(None, 'test-group/sleep/goodnight')
    if len(result) != 0:
        watch_deployment(result[0]['id'], 60)

    with open('tests/data/marathon/groups/good.json') as fd:
        stderr = b"Group '/test-group' already exists\n"
        assert_command(['dcos', 'marathon', 'group', 'add'],
                       returncode=1,
                       stderr=stderr,
                       stdin=fd)

    result = list_deployments(None, 'test-group/sleep/goodnight')
    if len(result) != 0:
        watch_deployment(result[0]['id'], 60)
    _remove_group('test-group')


def test_show_group():
    _add_group('tests/data/marathon/groups/good.json')
    _list_groups('test-group/sleep/goodnight')
    result = list_deployments(None, 'test-group/sleep/goodnight')
    if len(result) != 0:
        watch_deployment(result[0]['id'], 60)
    _show_group('test-group')
    _remove_group('test-group')


def test_add_bad_app():
    with open('tests/data/marathon/groups/bad_app.json') as fd:
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'group', 'add'],
            stdin=fd)

        expected = "Error: Additional properties are not allowed" + \
                   " ('badtype' was unexpected)"
        assert returncode == 1
        assert stdout == b''
        assert stderr.decode('utf-8').startswith(expected)


def test_add_bad_group():
    with open('tests/data/marathon/groups/bad_group.json') as fd:
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'group', 'add'],
            stdin=fd)

        expected = "Error: Additional properties are not allowed" + \
                   " ('fakeapp' was unexpected)"
        assert returncode == 1
        assert stdout == b''
        assert stderr.decode('utf-8').startswith(expected)


def test_add_bad_complicated_group():
    with open('tests/data/marathon/groups/complicated_bad.json') as fd:
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'group', 'add'],
            stdin=fd)

        err = "Error: missing required property 'id'"
        assert returncode == 1
        assert stdout == b''
        assert err in stderr.decode('utf-8')


def _list_groups(group_id=None):
    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'group', 'list', '--json'])

    result = json.loads(stdout.decode('utf-8'))

    if group_id is None:
        assert len(result) == 0
    else:
        groups = None
        for g in group_id.split("/")[:-1]:
            if groups is None:
                result = result[0]
                groups = "/{}".format(g)
            else:
                result = result['groups'][0]
                groups += g
            assert result['id'] == groups
            groups += "/"
        assert result['apps'][0]['id'] == "/" + group_id

    assert returncode == 0
    assert stderr == b''

    return result


def _remove_group(group_id):
    assert_command(['dcos', 'marathon', 'group', 'remove', group_id])

    # Let's make sure that we don't return until the deployment has finished
    result = list_deployments(None, group_id)
    if len(result) != 0:
        watch_deployment(result[0]['id'], 60)


def _add_group(file_path):
    with open(file_path) as fd:
        assert_command(['dcos', 'marathon', 'group', 'add'], stdin=fd)


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
