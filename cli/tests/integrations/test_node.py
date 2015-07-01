import json

import dcos.util as util
from dcos.util import create_schema

from ..fixtures.node import slave_fixture
from .common import assert_command, assert_lines, exec_command


def test_help():
    stdout = b"""Manage DCOS nodes

Usage:
    dcos node --info
    dcos node [--json]

Options:
    -h, --help    Show this screen
    --info        Show a short description of this subcommand
    --json        Print json-formatted nodes
    --version     Show version
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
    schema = create_schema(slave_fixture())
    for node in nodes:
        assert not util.validate_json(node, schema)


def test_node_table():
    assert_lines(['dcos', 'node'], 2)
