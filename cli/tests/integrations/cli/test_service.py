import collections
import json
import time

import dcos.util as util
from dcos.mesos import Framework
from dcos.util import create_schema
from dcoscli.service.main import _service_table

import pytest
from common import assert_command, exec_command, watch_all_deployments


@pytest.fixture
def service():
    service = Framework({
        "active": True,
        "checkpoint": True,
        "completed_tasks": [],
        "failover_timeout": 604800,
        "hostname": "mesos.vm",
        "id": "20150502-231327-16842879-5050-3889-0000",
        "name": "marathon",
        "offered_resources": {
            "cpus": 0.0,
            "disk": 0.0,
            "mem": 0.0,
            "ports": "[1379-1379, 10000-10000]"
        },
        "offers": [],
        "pid":
        "scheduler-a58cd5ba-f566-42e0-a283-b5f39cb66e88@172.17.8.101:55130",
        "registered_time": 1431543498.31955,
        "reregistered_time": 1431543498.31959,
        "resources": {
            "cpus": 0.2,
            "disk": 0,
            "mem": 32,
            "ports": "[1379-1379, 10000-10000]"
        },
        "role": "*",
        "tasks": [],
        "unregistered_time": 0,
        "used_resources": {
            "cpus": 0.2,
            "disk": 0,
            "mem": 32,
            "ports": "[1379-1379, 10000-10000]"
        },
        "user": "root",
        "webui_url": "http://mesos:8080"
    })

    return service


def test_help():
    stdout = b"""Get the status of DCOS services

Usage:
    dcos service --info
    dcos service [--inactive --json]

Options:
    -h, --help    Show this screen

    --info        Show a short description of this subcommand

    --json        Print json-formatted services

    --inactive    Show inactive services in addition to active ones.
                  Inactive services are those that have been disconnected from
                  master, but haven't yet reached their failover timeout.

    --version     Show version
"""
    assert_command(['dcos', 'service', '--help'], stdout=stdout)


def test_info():
    stdout = b"Get the status of DCOS services\n"
    assert_command(['dcos', 'service', '--info'], stdout=stdout)


def test_service(service):
    returncode, stdout, stderr = exec_command(['dcos', 'service', '--json'])

    services = _get_services(1)

    schema = _get_schema(service)
    for srv in services:
        assert not util.validate_json(srv, schema)


def _get_schema(service):
    schema = create_schema(service.dict())
    schema['required'].remove('reregistered_time')
    schema['required'].remove('pid')
    schema['properties']['offered_resources']['required'].remove('ports')
    schema['properties']['resources']['required'].remove('ports')
    schema['properties']['used_resources']['required'].remove('ports')

    return schema


def test_service_inactive():
    # install cassandra
    stdout = b"""Installing package [cassandra] version \
[0.1.0-SNAPSHOT-447-master-3ad1bbf8f7]
The Apache Cassandra DCOS Service implementation is alpha and there may \
be bugs, incomplete features, incorrect documentation or other discrepancies.
In order for Cassandra to start successfully, all resources must be \
available in the cluster, including ports, CPU shares, RAM and disk.

\tDocumentation: http://mesosphere.github.io/cassandra-mesos/
\tIssues: https://github.com/mesosphere/cassandra-mesos/issues
"""
    assert_command(['dcos', 'package', 'install', 'cassandra'],
                   stdout=stdout)

    # wait for it to deploy
    watch_all_deployments(300)

    # wait long enough for it to register
    time.sleep(5)

    # assert marathon and cassandra are listed
    _get_services(2)

    # uninstall cassandra.  For now, need to explicitly remove the
    # group that is left by cassandra.  See MARATHON-144
    assert_command(['dcos', 'package', 'uninstall', 'cassandra'])
    assert_command(['dcos', 'marathon', 'group', 'remove', '/cassandra'])

    watch_all_deployments(300)

    # I'm not quite sure why we have to sleep, but it seems cassandra
    # only transitions to "inactive" after a few seconds.
    time.sleep(5)

    # assert only marathon is active
    _get_services(1)
    # assert marathon and cassandra are listed with --inactive
    services = _get_services(None, ['--inactive'])
    assert len(services) >= 2


# not an integration test
def test_task_table(service):
    table = _service_table([service])

    stdout = """\
   NAME      HOST    ACTIVE  TASKS  CPU  MEM  DISK                     ID\
                   \n\
 marathon  mesos.vm   True     0    0.2   32   0    \
20150502-231327-16842879-5050-3889-0000 """
    assert str(table) == stdout


def _get_services(expected_count=None, args=[]):
    """Get services

    :param expected_count: assert exactly this number of services are
        running
    :type expected_count: int
    :param args: cli arguments
    :type args: [str]
    :returns: services
    :rtype: [dict]
    """

    returncode, stdout, stderr = exec_command(
        ['dcos', 'service', '--json'] + args)

    assert returncode == 0
    assert stderr == b''

    services = json.loads(stdout.decode('utf-8'))
    assert isinstance(services, collections.Sequence)
    if expected_count is not None:
        assert len(services) == expected_count

    return services
