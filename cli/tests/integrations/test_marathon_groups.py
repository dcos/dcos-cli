import json
import re

from .helpers.common import assert_command, assert_lines, exec_command
from .helpers.marathon import (group, remove_group, show_app,
                               watch_all_deployments)


GOOD_GROUP = 'tests/data/marathon/groups/good.json'
SCALE_GROUP = 'tests/data/marathon/groups/scale.json'


def test_add_group_by_stdin():
    _add_group_by_stdin(GOOD_GROUP)
    remove_group('test-group')


def test_group_list_table():
    with group(GOOD_GROUP, 'test-group'):
        assert_lines(['dcos', 'marathon', 'group', 'list'], 3)


def test_validate_complicated_group_and_app():
    with group('tests/data/marathon/groups/complicated.json', 'test-group'):
        pass


def test_add_existing_group():
    with group(GOOD_GROUP, 'test-group'):
        with open(GOOD_GROUP) as fd:
            stderr = b"Group '/test-group' already exists\n"
            assert_command(['dcos', 'marathon', 'group', 'add'],
                           returncode=1,
                           stderr=stderr,
                           stdin=fd)


def test_add_bad_complicated_group():
    with open('tests/data/marathon/groups/complicated_bad.json') as fd:
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'group', 'add'],
            stdin=fd)

        stderr_end = b"""{"message":"Invalid JSON","details":[{"path":"/groups(0)/apps(0)/id","errors":["\'id\' is undefined on object: {}"]}]}"""  # noqa: E501

        assert returncode == 1
        assert stderr_end in stderr
        assert stdout == b''


def test_update_group_from_stdin():
    with group(GOOD_GROUP, 'test-group'):
        _update_group(
            'test-group',
            'tests/data/marathon/groups/update_good.json')
        show_app('test-group/updated')


def test_update_missing_group():
    assert_command(['dcos', 'marathon', 'group', 'update', 'missing-id'],
                   stderr=b"Error: Group '/missing-id' does not exist\n",
                   returncode=1)


def test_scale_group():
    with group(SCALE_GROUP, 'scale-group'):
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'group', 'scale', 'scale-group', '2'])
        assert stderr == b''
        assert returncode == 0
        watch_all_deployments()
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'group', 'show', 'scale-group'])
        res = json.loads(stdout.decode('utf-8'))

        assert res['groups'][0]['apps'][0]['instances'] == 2


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
    with group(SCALE_GROUP, 'scale-group'):
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'group', 'scale', 'scale-group', '-2'])
        assert b'Invalid subcommand usage' in stdout
        assert returncode == 1


def test_scale_group_when_scale_factor_not_float():
    with group(SCALE_GROUP, 'scale-group'):
        returncode, stdout, stderr = exec_command(
            ['dcos', 'marathon', 'group', 'scale', 'scale-group', '1.a'])
        assert stderr == b'Error parsing string as float\n'
        assert returncode == 1


def _add_group_by_stdin(file_path):
    with open(file_path) as fd:
        cmd = ['dcos', 'marathon', 'group', 'add']
        returncode, stdout, stderr = exec_command(cmd, stdin=fd)
        assert returncode == 0
        assert re.fullmatch('Created deployment \S+\n',
                            stdout.decode('utf-8'))
        assert stderr == b''

    # Let's make sure that we don't return until the deployment has finished
    watch_all_deployments()


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
