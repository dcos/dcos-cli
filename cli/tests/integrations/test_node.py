import json
import os
import re

import dcos.util as util
import six
from dcos import mesos
from dcos.util import create_schema

from ..fixtures.node import slave_fixture
from .common import assert_command, assert_lines, exec_command, ssh_output


def test_help():
    with open('tests/data/help/node.txt') as content:
        stdout = six.b(content.read())
    assert_command(['dcos', 'node', '--help'], stdout=stdout)


def test_info():
    stdout = b"Manage DCOS nodes\n"
    assert_command(['dcos', 'node', '--info'], stdout=stdout)


def test_node():
    returncode, stdout, stderr = exec_command(['dcos', 'node', '--json'])

    assert returncode == 0
    assert stderr == b''

    nodes = json.loads(stdout.decode('utf-8'))
    schema = _get_schema(slave_fixture())
    for node in nodes:
        assert not util.validate_json(node, schema)


def test_node_table():
    returncode, stdout, stderr = exec_command(['dcos', 'node'])

    assert returncode == 0
    assert stderr == b''
    assert len(stdout.decode('utf-8').split('\n')) > 2


def test_node_log_empty():
    stderr = b"You must choose one of --master or --slave.\n"
    assert_command(['dcos', 'node', 'log'], returncode=1, stderr=stderr)


def test_node_log_master():
    assert_lines(['dcos', 'node', 'log', '--master'], 10)


def test_node_log_slave():
    slave_id = _node()[0]['id']
    assert_lines(['dcos', 'node', 'log', '--slave={}'.format(slave_id)], 10)


def test_node_log_missing_slave():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'node', 'log', '--slave=bogus'])

    assert returncode == 1
    assert stdout == b''
    assert stderr == b'No slave found with ID "bogus".\n'


def test_node_log_master_slave():
    slave_id = _node()[0]['id']

    returncode, stdout, stderr = exec_command(
        ['dcos', 'node', 'log', '--master', '--slave={}'.format(slave_id)])

    assert returncode == 0
    assert stderr == b''

    lines = stdout.decode('utf-8').split('\n')
    assert len(lines) == 23
    assert re.match('===>.*<===', lines[0])
    assert re.match('===>.*<===', lines[11])


def test_node_log_lines():
    assert_lines(['dcos', 'node', 'log', '--master', '--lines=4'], 4)


def test_node_log_invalid_lines():
    assert_command(['dcos', 'node', 'log', '--master', '--lines=bogus'],
                   stdout=b'',
                   stderr=b'Error parsing string as int\n',
                   returncode=1)


def test_node_ssh_master():
    _node_ssh(['--master'])


def test_node_ssh_slave():
    slave_id = mesos.DCOSClient().get_state_summary()['slaves'][0]['id']
    _node_ssh(['--slave={}'.format(slave_id)])


def test_node_ssh_option():
    stdout, stderr = _node_ssh_output(
        ['--master', '--option', 'Protocol=0'])
    assert stdout == b''
    assert b'ignoring bad proto spec' in stderr


def test_node_ssh_config_file():
    stdout, stderr = _node_ssh_output(
        ['--master', '--config-file', 'tests/data/node/ssh_config'])
    assert stdout == b''
    assert b'ignoring bad proto spec' in stderr


def test_node_ssh_user():
    stdout, stderr = _node_ssh_output(
        ['--master', '--user=bogus', '--option', 'PasswordAuthentication=no'])
    assert stdout == b''
    assert b'Permission denied' in stderr


def test_node_ssh_master_proxy_no_agent():
    env = os.environ.copy()
    env.pop('SSH_AUTH_SOCK', None)
    stderr = (b"There is no SSH_AUTH_SOCK env variable, which likely means "
              b"you aren't running `ssh-agent`.  `dcos node ssh "
              b"--master-proxy` depends on `ssh-agent` to safely use your "
              b"private key to hop between nodes in your cluster.  Please "
              b"run `ssh-agent`, then add your private key with `ssh-add`.\n")

    assert_command(['dcos', 'node', 'ssh', '--master-proxy', '--master'],
                   stderr=stderr,
                   returncode=1,
                   env=env)


def test_node_ssh_master_proxy():
    _node_ssh(['--master', '--master-proxy'])


def _node_ssh_output(args):
    cli_test_ssh_key_path = os.environ['CLI_TEST_SSH_KEY_PATH']
    cmd = ('ssh-agent /bin/bash -c "ssh-add {} 2> /dev/null && ' +
           'dcos node ssh --option StrictHostKeyChecking=no {}"').format(
               cli_test_ssh_key_path,
               ' '.join(args))

    return ssh_output(cmd)


def _node_ssh(args):
    stdout, stderr = _node_ssh_output(args)

    assert stdout
    assert b"Running `" in stderr
    num_lines = len(stderr.decode().split('\n'))
    expected_num_lines = 2 if '--master-proxy' in args else 3
    assert (num_lines == expected_num_lines or
            (num_lines == (expected_num_lines + 1) and
             b'Warning: Permanently added' in stderr))


def _get_schema(slave):
    schema = create_schema(slave)
    schema['required'].remove('reregistered_time')
    schema['properties']['used_resources']['required'].remove('ports')
    schema['properties']['offered_resources']['required'].remove('ports')
    schema['properties']['attributes']['additionalProperties'] = True

    return schema


def _node():
    returncode, stdout, stderr = exec_command(['dcos', 'node', '--json'])

    assert returncode == 0
    assert stderr == b''

    return json.loads(stdout.decode('utf-8'))
