import json
import os
import subprocess
import sys
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

    code, _, _ = exec_cmd(['dcos', 'cluster', 'remove', cluster['name']])
    assert code == 0


def _setup_cluster(name, with_plugins=True):
    cluster = {
        'variant': os.environ.get('DCOS_TEST_' + name + '_CLUSTER_VARIANT'),
        'username': os.environ.get('DCOS_TEST_' + name + '_CLUSTER_USERNAME'),
        'password': os.environ.get('DCOS_TEST_' + name + '_CLUSTER_PASSWORD'),
        'name': 'test_cluster_' + str(uuid.uuid4()),
    }

    cmd = 'dcos cluster setup --name={} --username={} --password={} --no-plugin http://{}'.format(
        cluster['name'],
        cluster['username'],
        cluster['password'],
        os.environ.get('DCOS_TEST_' + name + '_CLUSTER_HOST'))

    code, _, _ = exec_cmd(cmd.split(' '))
    assert code == 0

    if with_plugins:
        # For now we install default plugins manually, this can be changed once universe packages are released.
        plugins = {
            'linux': [
                'https://downloads.dcos.io/cli/plugins/dcos-core-cli/1.12/linux/x86-64/dcos-core-cli.zip',
                'https://downloads.mesosphere.io/cli/binaries/linux/x86-64/1.4.5/61d301f571fe26883b5122d567ac4b79bae7febbd2090c81b6cdda523659eb43/dcos-enterprise-cli',
            ],
            'darwin': [
                'https://downloads.dcos.io/cli/plugins/dcos-core-cli/1.12/darwin/x86-64/dcos-core-cli.zip',
                'https://downloads.mesosphere.io/cli/binaries/darwin/x86-64/1.4.5/d0d160a3f1357e4c22792c3ba27e115f5eb7acb7a3c70ccb6f2bc6358e5e1e66/dcos-enterprise-cli',
            ],
            'win32': [
                'https://downloads.dcos.io/cli/plugins/dcos-core-cli/1.12/windows/x86-64/dcos-core-cli.zip',
                'https://downloads.mesosphere.io/cli/binaries/windows/x86-64/1.4.5/f5a58c636c8c3bb8e146958c7d4d06fcf1ca395757e49ffabb2ef04150e9ece9/dcos-enterprise-cli',
            ],
        }
        for plugin in plugins[sys.platform]:
            code, _, _ = exec_cmd(['dcos', 'plugin', 'add', plugin])
            assert code == 0

    code, out, _ = exec_cmd(['dcos', 'cluster', 'list', '--json', '--attached'])
    clusters = json.loads(out)
    assert len(clusters) == 1
    assert clusters[0]['name'] == cluster['name']

    cluster['dcos_url'] = clusters[0]['url']
    cluster['version'] = clusters[0]['version']

    return cluster
