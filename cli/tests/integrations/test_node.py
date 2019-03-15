import json
import os
import sys

import pytest
import six

import dcos.util as util
from dcos import mesos
from dcos.util import create_schema

from dcoscli.test.common import (assert_command, assert_lines, exec_command,
                                 fetch_valid_json, ssh_output)
from ..fixtures.node import slave_fixture


def test_help():
    with open('dcoscli/data/help/node.txt') as content:
        stdout = six.b(content.read())
    assert_command(['dcos', 'node', '--help'], stdout=stdout)


def test_info():
    stdout = b"View DC/OS node information\n"
    assert_command(['dcos', 'node', '--info'], stdout=stdout)


def test_node():
    returncode, stdout, stderr = exec_command(['dcos', 'node', '--json'])

    assert returncode == 0
    assert stderr == b''

    nodes = json.loads(stdout.decode('utf-8'))
    slave_nodes = [node for node in nodes if node['type'] == 'agent']
    schema = _get_schema(slave_fixture())
    for node in slave_nodes:
        assert not util.validate_json(node, schema)


def test_node_table():
    returncode, stdout, stderr = exec_command(['dcos', 'node'])

    assert returncode == 0
    assert stderr == b''
    assert len(stdout.decode('utf-8').split('\n')) > 2


def test_node_table_field_option():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'node', '--field=disk_used:used_resources.disk'])

    assert returncode == 0
    assert stderr == b''
    lines = stdout.decode('utf-8').splitlines()
    assert len(lines) > 2
    assert lines[0].split() == ['HOSTNAME', 'IP', 'ID', 'TYPE', 'REGION',
                                'ZONE', 'DISK_USED']


def test_node_table_uppercase_field_option():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'node', '--field=TASK_RUNNING'])

    assert returncode == 0
    assert stderr == b''
    lines = stdout.decode('utf-8').splitlines()
    assert len(lines) > 2
    assert lines[0].split() == ['HOSTNAME', 'IP', 'ID', 'TYPE', 'REGION',
                                'ZONE', 'TASK_RUNNING']


def test_node_log_empty():
    stderr = b"You must choose one of --leader or --mesos-id.\n"
    assert_command(['dcos', 'node', 'log'], returncode=1, stderr=stderr)


def test_node_log_leader():
    assert_lines(['dcos', 'node', 'log', '--leader'], 10, greater_than=True)


def test_node_log_slave():
    slave_id = _node()[0]['id']
    assert_lines(
        ['dcos', 'node', 'log', '--mesos-id={}'.format(slave_id)],
        10,
        greater_than=True)


def test_node_log_missing_slave():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'node', 'log', '--mesos-id=bogus'])

    assert returncode == 1
    assert stdout == b''
    stderr_str = str(stderr)
    assert 'No files exist. Exiting.' in stderr_str


def test_node_log_lines():
    # since we are getting system logs, it's not guaranteed to get back
    # exactly 4 log entries. It must be >= 4
    assert_lines(
        ['dcos', 'node', 'log', '--leader', '--lines=4'],
        4,
        greater_than=True)


def test_node_log_invalid_lines():
    assert_command(['dcos', 'node', 'log', '--leader', '--lines=bogus'],
                   stdout=b'',
                   stderr=b'Error parsing string as int\n',
                   returncode=1)


def test_node_metrics_agent_summary():
    first_node_id = _node()[0]['id']
    assert_lines(
        ['dcos', 'node', 'metrics', 'summary', first_node_id],
        2
    )


def test_node_metrics_agent_summary_json():
    first_node_id = _node()[0]['id']

    node_json = fetch_valid_json(
        ['dcos', 'node', 'metrics', 'summary', first_node_id, '--json']
    )

    names = [d['name'] for d in node_json]
    assert names == ['cpu.total', 'memory.total', 'memory.free',
                     'filesystem.capacity.total', 'filesystem.capacity.used']


def test_node_metrics_agent_details():
    first_node_id = _node()[0]['id']
    assert_lines(
        ['dcos', 'node', 'metrics', 'details', first_node_id],
        100,
        greater_than=True
    )


def test_node_metrics_agent_details_json():
    first_node_id = _node()[0]['id']

    node_json = fetch_valid_json(
        ['dcos', 'node', 'metrics', 'details', first_node_id, '--json']
    )

    names = [d['name'] for d in node_json]
    assert 'system.uptime' in names
    assert 'cpu.cores' in names


def test_node_dns():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'node', 'dns', 'marathon.mesos', '--json'])

    result = json.loads(stdout.decode('utf-8'))

    assert returncode == 0
    assert stderr == b''
    assert result[0]['host'] == "marathon.mesos."
    assert 'ip' in result[0]


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
def test_node_ssh_slave_with_private_ip():
    slave_ip = mesos.DCOSClient().get_state_summary()['slaves'][0]['hostname']
    _node_ssh(['--private-ip={}'.format(slave_ip), '--master-proxy'])


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
              b"--master-proxy/--proxy-ip` depends on `ssh-agent` to safely "
              b"use your private key to hop between nodes in your cluster.  "
              b"Please run `ssh-agent`, then add your private key with "
              b"`ssh-add`.\n")

    assert_command(['dcos', 'node', 'ssh', '--master-proxy', '--leader'],
                   stderr=stderr,
                   returncode=1,
                   env=env)


@pytest.mark.skipif(sys.platform == 'win32',
                    reason='No pseudo terminal on windows')
def test_node_ssh_master_proxy():
    _node_ssh(['--leader', '--master-proxy'])


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


@pytest.mark.skipif(sys.platform == 'win32',
                    reason='No pseudo terminal on windows')
def test_node_ssh_slave_with_separated_command():
    slave = mesos.DCOSClient().get_state_summary()['slaves'][0]
    _node_ssh(['--mesos-id={}'.format(slave['id']), '--master-proxy', '--user',
               os.environ.get('CLI_TEST_SSH_USER'), '--',
               '/opt/mesosphere/bin/detect_ip'], 0, slave['hostname'])


@pytest.mark.skipif(True, reason='The agent should be recommissioned,'
                                 ' but that feature does not exist yet.')
def test_node_decommission():
    agents = mesos.DCOSClient().get_state_summary()['slaves']
    agents_count = len(agents)
    assert agents_count > 0

    agent_id = agents[0]['id']

    returncode, stdout, stderr = exec_command([
        'dcos', 'node', 'decommission', agent_id])

    exp_stdout = "Agent {} has been marked as gone.\n".format(agent_id)

    assert returncode == 0
    assert stdout.decode('utf-8') == exp_stdout
    assert stderr == b''

    new_agents = mesos.DCOSClient().get_state_summary()['slaves']
    assert (agents_count - 1) == len(new_agents)


def test_node_decommission_unexisting_agent():
    returncode, stdout, stderr = exec_command([
        'dcos', 'node', 'decommission', 'not-a-mesos-id'])

    assert returncode == 1
    assert stdout == b''
    assert stderr.startswith(b"Couldn't mark agent not-a-mesos-id as gone :")


def _node_ssh_output(args):
    cli_test_ssh_key_path = os.environ['CLI_TEST_SSH_KEY_PATH']

    if os.environ.get('CLI_TEST_SSH_USER') and \
            not any("--user" in a for a in args):
        args.extend(['--user', os.environ.get('CLI_TEST_SSH_USER')])

    if os.environ.get('CLI_TEST_MASTER_PROXY') and \
            '--master-proxy' not in args:
        args.append('--master-proxy')

    cmd = ('ssh-agent /bin/bash -c "ssh-add {} 2> /dev/null && ' +
           'dcos node ssh --option StrictHostKeyChecking=no ' +
           '    --option ConnectTimeout=5 {}"').format(
        cli_test_ssh_key_path,
        ' '.join(args))

    return ssh_output(cmd)


def _node_ssh(args, expected_returncode=None, expected_stdout=None):
    stdout, stderr, returncode = _node_ssh_output(args)
    assert returncode is expected_returncode, \
        'returncode = %r; stdout: = %s; stderr = %s' % (
            returncode, stdout, stderr)
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

    return [n for n in json.loads(stdout.decode('utf-8'))
            if n['type'] == 'agent']
