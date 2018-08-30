import json
import os
import subprocess
import uuid

import pytest


def exec_cmd(cmd, env=None, stdin=None, timeout=None):
    """Execute CLI command

    :param cmd: Program and arguments
    :type cmd: [str]
    :param env: Environment variables
    :type env: dict | None
    :param stdin: File to use for stdin
    :type stdin: file
    :param timeout: The timeout for the process to terminate.
    :type timeout: int
    :raises: subprocess.TimeoutExpired when the timeout is reached
             before the process finished.
    :returns: A tuple with the returncode, stdout and stderr
    :rtype: (int, bytes, bytes)
    """

    print('CMD: {!r}'.format(cmd))

    process = subprocess.Popen(
        cmd,
        stdin=stdin,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env)

    try:
        streams = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        # The child process is not killed if the timeout expires, so in order
        # to cleanup properly a well-behaved application should kill the child
        # process and finish communication.
        # https://docs.python.org/3.5/library/subprocess.html#subprocess.Popen.communicate
        process.kill()
        stdout, stderr = process.communicate()
        print('STDOUT: {}'.format(stdout.decode('utf-8')))
        print('STDERR: {}'.format(stderr.decode('utf-8')))
        raise

    # This is needed to get rid of '\r' from Windows's lines endings.
    stdout, stderr = [stream.replace(b'\r', b'').decode('utf-8') for stream in streams]

    # We should always print the stdout and stderr
    print('STDOUT: {}'.format(stdout))
    print('STDERR: {}'.format(stderr))

    return (process.returncode, stdout, stderr)


@pytest.fixture()
def default_cluster():
    cluster = _setup_cluster('DEFAULT')

    yield cluster

    code, _, _ = exec_cmd(['dcos', 'cluster', 'remove', cluster['cluster_id']])
    assert code == 0


@pytest.fixture()
def default_cluster_with_plugins():
    cluster = _setup_cluster('DEFAULT', with_plugins=True)

    yield cluster

    code, _, _ = exec_cmd(['dcos', 'cluster', 'remove', cluster['cluster_id']])
    assert code == 0


def _setup_cluster(name, with_plugins=False):
    cluster = {
        'variant': os.environ.get('DCOS_TEST_' + name + '_CLUSTER_VARIANT'),
        'username': os.environ.get('DCOS_TEST_' + name + '_CLUSTER_USERNAME'),
        'password': os.environ.get('DCOS_TEST_' + name + '_CLUSTER_PASSWORD'),
        'name': 'test_cluster_' + str(uuid.uuid4()),
    }

    cmd = 'dcos cluster setup --name={} --username={} --password={} http://{}'.format(
        cluster['name'],
        cluster['username'],
        cluster['password'],
        os.environ.get('DCOS_TEST_' + name + '_CLUSTER_HOST'))

    if not with_plugins:
        cmd += ' --no-plugin'

    code, _, _ = exec_cmd(cmd.split(' '))
    assert code == 0

    code, out, _ = exec_cmd(['dcos', 'cluster', 'list', '--json', '--attached'])
    clusters = json.loads(out)
    assert len(clusters) == 1
    assert clusters[0]['name'] == cluster['name']

    cluster['dcos_url'] = clusters[0]['url']
    cluster['version'] = clusters[0]['version']
    cluster['cluster_id'] = clusters[0]['cluster_id']

    return cluster
