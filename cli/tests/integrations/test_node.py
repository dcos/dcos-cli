import json
import os
import re
import sys

import pytest
import six

import dcos.util as util
from dcos import mesos
from dcos.util import create_schema

from .common import assert_command, assert_lines, exec_command, ssh_output
from ..fixtures.node import slave_fixture


def test_help():
    with open('tests/data/help/node.txt') as content:
        stdout = six.b(content.read())
    assert_command(['dcos', 'node', '--help'], stdout=stdout)


def test_info():
    stdout = b"Administer and manage DC/OS cluster nodes\n"
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
    stderr = b"You must choose one of --leader or --mesos-id.\n"
    assert_command(['dcos', 'node', 'log'], returncode=1, stderr=stderr)


def test_node_log_leader():
    assert_lines(['dcos', 'node', 'log', '--leader'], 10)


def test_node_log_slave():
    slave_id = _node()[0]['id']
    assert_lines(['dcos', 'node', 'log', '--mesos-id={}'.format(slave_id)], 10)


def test_node_log_missing_slave():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'node', 'log', '--mesos-id=bogus'])

    assert returncode == 1
    assert stdout == b''
    assert stderr == b'No slave found with ID "bogus".\n'


def test_node_log_leader_slave():
    slave_id = _node()[0]['id']

    returncode, stdout, stderr = exec_command(
        ['dcos', 'node', 'log', '--leader', '--mesos-id={}'.format(slave_id)])

    assert returncode == 0
    assert stderr == b''

    lines = stdout.decode('utf-8').split('\n')
    assert len(lines) == 23
    assert re.match('===>.*<===', lines[0])
    assert re.match('===>.*<===', lines[11])


def test_node_log_lines():
    assert_lines(['dcos', 'node', 'log', '--leader', '--lines=4'], 4)


def test_node_log_invalid_lines():
    assert_command(['dcos', 'node', 'log', '--leader', '--lines=bogus'],
                   stdout=b'',
                   stderr=b'Error parsing string as int\n',
                   returncode=1)


@pytest.mark.skipif(sys.platform == 'win32',
                    reason='No pseudo terminal on windows')
def test_node_ssh_leader():
    _node_ssh(['--leader'])


@pytest.mark.skipif(sys.platform == 'win32',
                    reason='No pseudo terminal on windows')
def test_node_ssh_slave():
    slave_id = mesos.DCOSClient().get_state_summary()['slaves'][0]['id']
    _node_ssh(['--mesos-id={}'.format(slave_id), '--master-proxy'])


@pytest.mark.skipif(sys.platform == 'win32',
                    reason='No pseudo terminal on windows')
def test_node_ssh_option():
    stdout, stderr, _ = _node_ssh_output(
        ['--leader', '--option', 'Protocol=0'])
    assert stdout == b''
    assert b'ignoring bad proto spec' in stderr


@pytest.mark.skipif(sys.platform == 'win32',
                    reason='No pseudo terminal on windows')
def test_node_ssh_config_file():
    stdout, stderr, _ = _node_ssh_output(
        ['--leader', '--config-file', 'tests/data/node/ssh_config'])
    assert stdout == b''
    assert b'ignoring bad proto spec' in stderr


@pytest.mark.skipif(sys.platform == 'win32',
                    reason='No pseudo terminal on windows')
def test_node_ssh_user():
    stdout, stderr, _ = _node_ssh_output(
        ['--master-proxy', '--leader', '--user=bogus', '--option',
         'BatchMode=yes'])
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

    assert_command(['dcos', 'node', 'ssh', '--master-proxy', '--leader'],
                   stderr=stderr,
                   returncode=1,
                   env=env)


@pytest.mark.skipif(sys.platform == 'win32',
                    reason='No pseudo terminal on windows')
def test_node_ssh_master_proxy():
    _node_ssh(['--leader', '--master-proxy'])


def test_master_arg_deprecation_notice():
    stderr = b"--master has been deprecated. Please use --leader.\n"
    assert_command(['dcos', 'node', 'log', '--master'],
                   stderr=stderr,
                   returncode=1)
    assert_command(['dcos', 'node', 'ssh', '--master'],
                   stderr=stderr,
                   returncode=1)


def test_slave_arg_deprecation_notice():
    stderr = b"--slave has been deprecated. Please use --mesos-id.\n"
    assert_command(['dcos', 'node', 'log', '--slave=bogus'],
                   stderr=stderr,
                   returncode=1)
    assert_command(['dcos', 'node', 'ssh', '--slave=bogus'],
                   stderr=stderr,
                   returncode=1)


@pytest.mark.skipif(sys.platform == 'win32',
                    reason='No pseudo terminal on windows')
def test_node_ssh_with_command():
    leader_hostname = mesos.DCOSClient().get_state_summary()['hostname']
    _node_ssh(['--leader', '--master-proxy', '/opt/mesosphere/bin/detect_ip'],
              0, leader_hostname)


@pytest.mark.skipif(sys.platform == 'win32',
                    reason='No pseudo terminal on windows')
def test_node_ssh_slave_with_command():
    slave = mesos.DCOSClient().get_state_summary()['slaves'][0]
    _node_ssh(['--mesos-id={}'.format(slave['id']), '--master-proxy',
              '/opt/mesosphere/bin/detect_ip'], 0, slave['hostname'])


def _node_ssh_output(args):
    cli_test_ssh_key_path = os.environ['CLI_TEST_SSH_KEY_PATH']

    cmd = ('ssh-agent /bin/bash -c "ssh-add {} 2> /dev/null && ' +
           'dcos node ssh --option StrictHostKeyChecking=no {}"').format(
               cli_test_ssh_key_path,
               ' '.join(args))

    return ssh_output(cmd)


def _node_ssh(args, expected_returncode=None, expected_stdout=None):
    if os.environ.get('CLI_TEST_MASTER_PROXY') and \
            '--master-proxy' not in args:
        args.append('--master-proxy')

    stdout, stderr, returncode = _node_ssh_output(args)
    assert returncode is expected_returncode
    if expected_stdout is not None:
        assert stdout.decode('utf-8').startswith(expected_stdout)
    assert b"Running `" in stderr


def _get_schema(slave):
    schema = create_schema(slave, True)
    schema['required'].remove('reregistered_time')

    schema['required'].remove('reserved_resources')
    schema['properties']['reserved_resources']['required'] = []

    schema['required'].remove('unreserved_resources')
    schema['properties']['unreserved_resources']['required'] = []

    schema['properties']['used_resources']['required'].remove('ports')
    schema['properties']['offered_resources']['required'].remove('ports')

    schema['required'].remove('version')
    return schema


def _node():
    returncode, stdout, stderr = exec_command(['dcos', 'node', '--json'])

    assert returncode == 0
    assert stderr == b''

    return json.loads(stdout.decode('utf-8'))
