import time

import dcos.util as util
from dcos.util import create_schema

import pytest

from ..fixtures.service import framework_fixture
from .common import (assert_command, assert_lines, delete_zk_nodes,
                     get_services, service_shutdown, watch_all_deployments)


@pytest.fixture(scope="module")
def zk_znode(request):
    request.addfinalizer(delete_zk_nodes)
    return request


def test_help():
    stdout = b"""Manage DCOS services

Usage:
    dcos service --info
    dcos service [--inactive --json --colors]
    dcos service shutdown <service-id>

Options:
    -h, --help    Show this screen

    --info        Show a short description of this subcommand

    --json        Print json-formatted services

    --colors      Json syntax highlighting

    --inactive    Show inactive services in addition to active ones.
                  Inactive services are those that have been disconnected from
                  master, but haven't yet reached their failover timeout.

    --version     Show version

Positional Arguments:
    <service-id>  The ID for the DCOS Service
"""
    assert_command(['dcos', 'service', '--help'], stdout=stdout)


def test_info():
    stdout = b"Manage DCOS services\n"
    assert_command(['dcos', 'service', '--info'], stdout=stdout)


def test_service():
    services = get_services(1)

    schema = _get_schema(framework_fixture())
    for srv in services:
        assert not util.validate_json(srv, schema)


def test_service_table():
    assert_lines(['dcos', 'service'], 2)


def test_service_inactive(zk_znode):
    # install cassandra
    stdout = b"""The Apache Cassandra DCOS Service implementation is alpha \
and there may be bugs, incomplete features, incorrect documentation or other \
discrepancies.
The default configuration requires 3 nodes each with 0.3 CPU shares, 1184MB \
of memory and 272MB of disk.
Installing package [cassandra] version [0.1.0-1]
Thank you for installing the Apache Cassandra DCOS Service.

\tDocumentation: http://mesosphere.github.io/cassandra-mesos/
\tIssues: https://github.com/mesosphere/cassandra-mesos/issues
"""
    assert_command(['dcos', 'package', 'install', 'cassandra', '--yes'],
                   stdout=stdout)

    # wait for it to deploy
    watch_all_deployments(300)

    # wait long enough for it to register
    time.sleep(5)

    # assert marathon and cassandra are listed
    get_services(2)

    # uninstall cassandra using marathon. For now, need to explicitly remove
    # the group that is left by cassandra.  See MARATHON-144
    assert_command(['dcos', 'marathon', 'group', 'remove', '/cassandra'])

    watch_all_deployments(300)

    # I'm not quite sure why we have to sleep, but it seems cassandra
    # only transitions to "inactive" after a few seconds.
    time.sleep(5)

    # assert only marathon is active
    get_services(1)
    # assert marathon and cassandra are listed with --inactive
    services = get_services(None, ['--inactive'])
    assert len(services) >= 2

    # shutdown the cassandra framework
    for framework in get_services(args=['--inactive']):
        if framework['name'] == 'cassandra.dcos':
            service_shutdown(framework['id'])

    # assert marathon is only listed with --inactive
    get_services(1, ['--inactive'])


def _get_schema(service):
    schema = create_schema(service.dict())
    schema['required'].remove('reregistered_time')
    schema['required'].remove('pid')
    schema['properties']['offered_resources']['required'].remove('ports')
    schema['properties']['resources']['required'].remove('ports')
    schema['properties']['used_resources']['required'].remove('ports')

    return schema
