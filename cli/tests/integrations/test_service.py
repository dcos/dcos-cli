import os
import signal
import subprocess
import sys
import time

import pytest

import dcos.util as util
from dcos.util import create_schema

from .helpers.common import (assert_command, assert_lines, delete_zk_node,
                             delete_zk_nodes, exec_command, ssh_output)
from .helpers.marathon import remove_app
from .helpers.package import (package, package_install, setup_universe_server,
                              teardown_universe_server)
from .helpers.service import get_services, service_shutdown, wait_for_service
from ..fixtures.service import framework_fixture


def setup_module(module):
    setup_universe_server()


def teardown_module(module):
    delete_zk_nodes()
    teardown_universe_server()


def test_help():
    with open('dcoscli/data/help/service.txt') as content:
        assert_command(['dcos', 'service', '--help'],
                       stdout=content.read().encode('utf-8'))


def test_info():
    stdout = b"Manage DC/OS services\n"
    assert_command(['dcos', 'service', '--info'], stdout=stdout)


def test_service():
    services = get_services()

    schema = _get_schema(framework_fixture())
    for srv in services:
        assert not util.validate_json(srv, schema)


def test_service_table():
    assert_lines(['dcos', 'service'], 3)


def test_service_inactive_and_completed():
    package_install('kafka', True, ['--app'])
    wait_for_service('kafka')

    # get kafka's framework ID
    kafka_id = None
    for service in get_services():
        if service['name'] == 'kafka':
            kafka_id = service['id']
            break

    assert kafka_id is not None

    # assert kafka is listed
    services = get_services()
    assert any(
        service['name'] == 'kafka' for service in services)

    # kill scheduler and test for inactive...
    exec_command(['dcos', 'marathon', 'app', 'stop', '/kafka', '--force'])

    time.sleep(5)
    # assert kafka is not listed
    assert not any(
        service['name'] == 'kafka' for service in get_services())

    # assert kafka is inactive
    inactive = get_services(args=['--inactive'])
    assert any(service['name'] == 'kafka' for service in inactive)

    # teardown framework and test for completed...
    service_shutdown(kafka_id)
    delete_zk_node('kafka-mesos')

    # assert kafka is not listed
    assert not any(
        service['name'] == 'kafka' for service in get_services())

    # assert kafka is completed
    services = get_services(args=['--completed'])
    assert len(services) >= 3
    assert any(service['id'] == kafka_id for service in services)

    exec_command(['dcos', 'package', 'uninstall', 'kafka', '--yes'])


def test_log():
    with package(
        'cassandra',
        deploy=True,
        args=['--package-version=1.0.25-3.0.10']
    ):
        returncode, stdout, stderr = exec_command(
            ['dcos', 'service', 'log', 'cassandra'])

        assert returncode == 0
        assert len(stdout.decode('utf-8').split('\n')) > 1
        assert stderr == b''

        returncode, stdout, stderr = exec_command(
            ['dcos', 'service', 'log', 'cassandra', 'stderr'])

        assert returncode == 0
        assert len(stdout.decode('utf-8').split('\n')) > 1
        assert stderr == b''

    # Package was uninstalled but its group needs to be removed separately
    exec_command(['dcos', 'marathon', 'group', 'remove', 'cassandra'])


def test_log_marathon_file():
    assert_command(['dcos', 'service', 'log', 'marathon', 'stderr'],
                   stderr=(b'The <file> argument is invalid for marathon. ' +
                           b'The systemd journal is always used for the ' +
                           b'marathon log.\n'),
                   returncode=1)


@pytest.mark.skipif(sys.platform == 'win32',
                    reason='No pseduo terminal on windows')
def test_log_marathon_config():
    stdout, stderr, _ = ssh_output(
        'dcos service log marathon ' +
        '--ssh-config-file=tests/data/node/ssh_config')

    assert stdout == b''
    assert b'ignoring bad proto spec' in stderr


@pytest.mark.skipif(True,
                    reason=(
                        "Now that we test against an AWS cluster, this test "
                        "is blocked on DCOS-3104requires python3.3"))
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


@pytest.mark.skipif(os.environ.get('DCOS_ENABLE_LOG_TEST') != 1,
                    reason='disable python buffering')
def test_log_follow():
    package_install('chronos', deploy=True)

    args = ['dcos', 'service', 'log', 'chronos', '--follow']

    if sys.platform == 'win32':
        proc = subprocess.Popen(
            args,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
    else:
        # disable stdout/stderr buffering:
        # https://docs.python.org/3/using/cmdline.html#cmdoption-u
        my_env = os.environ.copy()
        my_env['PYTHONUNBUFFERED'] = 'x'

        # os.setsid is only available for Unix:
        # https://docs.python.org/2/library/os.html#os.setsid
        proc = subprocess.Popen(
            args,
            preexec_fn=os.setsid,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=my_env)

    time.sleep(10)

    proc.poll()
    assert proc.returncode is None

    if sys.platform == 'win32':
        os.kill(proc.pid, signal.CTRL_BREAK_EVENT)
    else:
        # using Unix-only commands os.killpg + os.getgid
        # https://docs.python.org/2/library/os.html#os.killpg
        # https://docs.python.org/2/library/os.html#os.getpgid
        os.killpg(os.getpgid(proc.pid), 15)

    stdout = proc.stdout.read()
    stderr = proc.stderr.read()

    print('STDOUT: {}'.format(stdout))
    print('STDERR: {}'.format(stderr))
    assert len(stdout.decode('utf-8').split('\n')) > 3

    assert_lines(['dcos', 'service', 'log', 'chronos', '--lines=4'], 4)

    exec_command(['dcos', 'package', 'uninstall', 'chronos', '--yes'])


@pytest.mark.skipif(True, reason='Broken Marathon but we need to release')
def test_log_multiple_apps():
    package_install('marathon',
                    True,
                    ['--options=tests/data/service/marathon-user.json'])
    package_install('marathon',
                    True,
                    ['--options=tests/data/service/marathon-user2.json',
                     '--app-id=marathon-user2'])
    wait_for_service('marathon-user', number_of_services=2)

    try:
        stderr = (b'Multiple marathon apps found for service name ' +
                  b'[marathon-user]: [/marathon-user], [/marathon-user2]\n')
        assert_command(['dcos', 'service', 'log', 'marathon-user'],
                       returncode=1,
                       stderr=stderr)
    finally:
        # We can't use `dcos package uninstall`. The services have the same
        # name. Manually remove the dcos services.
        remove_app('marathon-user')
        remove_app('marathon-user2')
        for service in get_services():
            if service['name'] == 'marathon-user':
                service_shutdown(service['id'])

        delete_zk_node('universe')


def test_log_no_apps():
    assert_command(['dcos', 'service', 'log', 'bogus'],
                   stderr=b'No marathon apps found for service [bogus]\n',
                   returncode=1)


def _get_schema(service):
    schema = create_schema(service.dict(), True)
    schema['required'].remove('reregistered_time')
    schema['required'].remove('pid')
    schema['required'].remove('executors')
    schema['properties']['offered_resources']['required'].remove('ports')
    schema['properties']['resources']['required'].remove('ports')
    schema['properties']['used_resources']['required'].remove('ports')

    return schema
