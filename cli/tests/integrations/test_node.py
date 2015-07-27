import json
import re

import dcos.util as util
from dcos import mesos
from dcos.util import create_schema

from ..fixtures.node import slave_fixture
from .common import assert_command, assert_lines, exec_command, ssh_output


def test_help():
    stdout = b"""Manage DCOS nodes

Usage:
    dcos node --info
    dcos node [--json]
    dcos node log [--follow --lines=N --master --slave=<slave-id>]
    dcos node ssh [--option SSHOPT=VAL ...]
                  [--config-file=<path>]
                  [--user=<user>]
                  (--master | --slave=<slave-id>)

Options:
    -h, --help              Show this screen
    --info                  Show a short description of this subcommand
    --json                  Print json-formatted nodes
    --follow                Output data as the file grows
    --lines=N               Output the last N lines [default: 10]
    --master                Access the leading master
    --slave=<slave-id>      Access the slave with the provided ID
    --option SSHOPT=VAL     SSH option (see `man ssh_config`)
    --config-file=<path>    Path to SSH config file
    --user=<user>           SSH user [default: core]
    --version               Show version
"""
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


def _node_ssh_output(args):
    cmd = ('dcos node ssh --option ' +
           'IdentityFile=/host-home/.vagrant.d/insecure_private_key ' +
           '--option StrictHostKeyChecking=no ' +
           '{}').format(' '.join(args))

    return ssh_output(cmd)


def _node_ssh(args):
    stdout, stderr = _node_ssh_output(args)

    assert stdout
    assert b"Running `" in stderr
    num_lines = len(stderr.decode().split('\n'))
    assert (num_lines == 2 or
            (num_lines == 3 and b'Warning: Permanently added' in stderr))


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
