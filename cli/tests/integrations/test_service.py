import os
import subprocess
import time

import dcos.util as util
from dcos.util import create_schema

from ..fixtures.service import framework_fixture
from .common import (assert_command, assert_lines, delete_zk_node,
                     delete_zk_nodes, exec_command, get_services,
                     package_install, package_uninstall, service_shutdown,
                     ssh_output, watch_all_deployments)


def setup_module(module):
    package_install('chronos', True)


def teardown_module(module):
    package_uninstall(
        'chronos',
        stderr=b'Uninstalled package [chronos] version [2.3.4]\n'
               b'The Chronos DCOS Service has been uninstalled and will no '
               b'longer run.\nPlease follow the instructions at http://docs.'
               b'mesosphere.com/services/chronos/#uninstall to clean up any '
               b'persisted state\n')
    delete_zk_nodes()


def test_help():
    with open('tests/data/help/service.txt') as content:
        assert_command(['dcos', 'service', '--help'],
                       stdout=content.read().encode('utf-8'))


def test_info():
    stdout = b"Manage DCOS services\n"
    assert_command(['dcos', 'service', '--info'], stdout=stdout)


def test_service():
    services = get_services(2)

    schema = _get_schema(framework_fixture())
    for srv in services:
        assert not util.validate_json(srv, schema)


def test_service_table():
    assert_lines(['dcos', 'service'], 3)


def test_service_inactive():
    package_install('cassandra', True)

    # wait long enough for it to register
    time.sleep(5)

    # assert marathon, chronos, and cassandra are listed
    get_services(3)

    # uninstall cassandra using marathon. For now, need to explicitly remove
    # the group that is left by cassandra.  See MARATHON-144
    assert_command(['dcos', 'marathon', 'group', 'remove', '/cassandra'])

    watch_all_deployments()

    # I'm not quite sure why we have to sleep, but it seems cassandra
    # only transitions to "inactive" after a few seconds.
    time.sleep(5)

    # assert only marathon and chronos are active
    get_services(2)

    # assert marathon, chronos, and cassandra are inactive
    services = get_services(args=['--inactive'])
    assert len(services) >= 3

    # shutdown the cassandra framework
    for framework in services:
        if framework['name'] == 'cassandra.dcos':
            service_shutdown(framework['id'])

    # assert marathon, chronos are only listed with --inactive
    get_services(2, ['--inactive'])

    delete_zk_node('cassandra-mesos')


def test_service_completed():
    package_install('cassandra', True)

    time.sleep(5)

    services = get_services(3)

    # get cassandra's framework ID
    cassandra_id = None
    for service in services:
        if service['name'] == 'cassandra.dcos':
            cassandra_id = service['id']
            break

    assert cassandra_id is not None

    assert_command(['dcos', 'marathon', 'group', 'remove', '/cassandra'])
    service_shutdown(cassandra_id)
    delete_zk_node('cassandra-mesos')

    # assert cassandra is not running
    services = get_services(2)
    assert not any(service['id'] == cassandra_id for service in services)

    # assert cassandra is completed
    services = get_services(args=['--completed'])
    assert len(services) >= 3
    assert any(service['id'] == cassandra_id for service in services)


def test_log():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'service', 'log', 'chronos'])

    assert returncode == 0
    assert len(stdout.decode('utf-8').split('\n')) > 1
    assert stderr == b''


def test_log_file():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'service', 'log', 'chronos', 'stderr'])

    assert returncode == 0
    assert len(stdout.decode('utf-8').split('\n')) > 1
    assert stderr == b''


def test_log_marathon_file():
    assert_command(['dcos', 'service', 'log', 'marathon', 'stderr'],
                   stderr=(b'The <file> argument is invalid for marathon. ' +
                           b'The systemd journal is always used for the ' +
                           b'marathon log.\n'),
                   returncode=1)


def test_log_marathon_config():
    stdout, stderr = ssh_output(
        'dcos service log marathon ' +
        '--ssh-config-file=tests/data/node/ssh_config')

    assert stdout == b''
    assert b'ignoring bad proto spec' in stderr


def test_log_marathon():
    stdout, stderr = ssh_output(
        'dcos service log marathon ' +
        '--ssh-config-file=tests/data/service/ssh_config')

    assert len(stdout.decode('utf-8').split('\n')) > 10

    assert b"Running `" in stderr
    num_lines = len(stderr.decode('utf-8').split('\n'))
    assert ((num_lines == 2) or
            (num_lines == 3 and b'Warning: Permanently added' in stderr))


def test_log_config():
    assert_command(
        ['dcos', 'service', 'log', 'chronos', '--ssh-config-file=/path'],
        stderr=(b'The `--ssh-config-file` argument is invalid for '
                b'non-marathon services. SSH is not used.\n'),
        returncode=1)


def test_log_follow():
    proc = subprocess.Popen(['dcos', 'service', 'log', 'chronos', '--follow'],
                            preexec_fn=os.setsid,
                            stdout=subprocess.PIPE)
    time.sleep(3)

    proc.poll()
    assert proc.returncode is None

    os.killpg(os.getpgid(proc.pid), 15)
    assert len(proc.stdout.read().decode('utf-8').split('\n')) > 3


def test_log_lines():
    assert_lines(['dcos', 'service', 'log', 'chronos', '--lines=4'], 4)


def test_log_multiple_apps():
    package_install('marathon', True)
    package_install('marathon', True,
                    ['--options=tests/data/service/marathon-user2.json',
                     '--app-id=marathon-user2'])
    try:
        stderr = (b'Multiple marathon apps found for service name ' +
                  b'[marathon-user]: [/marathon-user], [/marathon-user2]\n')
        assert_command(['dcos', 'service', 'log', 'marathon-user'],
                       returncode=1,
                       stderr=stderr)
    finally:
        # Uninstall notes and message are printed twice because --all will
        # uninstall two packages
        package_uninstall(
            'marathon', ['--all'],
            stderr=b'Uninstalled package [marathon] version [0.9.0]\n'
                   b'The Marathon DCOS Service has been uninstalled and will '
                   b'no longer run.\nPlease follow the instructions at http://'
                   b'docs.mesosphere.com/services/marathon/#uninstall to '
                   b'clean up any persisted state\n'
                   b'Uninstalled package [marathon] version [0.9.0]\n'
                   b'The Marathon DCOS Service has been uninstalled and will '
                   b'no longer run.\nPlease follow the instructions at http://'
                   b'docs.mesosphere.com/services/marathon/#uninstall to '
                   b'clean up any persisted state\n')


def test_log_no_apps():
    assert_command(['dcos', 'service', 'log', 'bogus'],
                   stderr=b'No marathon apps found for service [bogus]\n',
                   returncode=1)


def _get_schema(service):
    schema = create_schema(service.dict())
    schema['required'].remove('reregistered_time')
    schema['required'].remove('pid')
    schema['required'].remove('executors')
    schema['properties']['offered_resources']['required'].remove('ports')
    schema['properties']['resources']['required'].remove('ports')
    schema['properties']['used_resources']['required'].remove('ports')

    return schema
