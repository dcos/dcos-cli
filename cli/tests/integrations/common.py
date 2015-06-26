import collections
import contextlib
import json
import os
import subprocess

import requests

from six.moves import urllib


def exec_command(cmd, env=None, stdin=None):
    """Execute CLI command

    :param cmd: Program and arguments
    :type cmd: [str]
    :param env: Environment variables
    :type env: dict
    :param stdin: File to use for stdin
    :type stdin: file
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

    # This is needed to get rid of '\r' from Windows's lines endings.
    stdout, stderr = [std_stream.replace(b'\r', b'')
                      for std_stream in process.communicate()]

    # We should always print the stdout and stderr
    print('STDOUT: {}'.format(_truncate(stdout.decode('utf-8'))))
    print('STDERR: {}'.format(_truncate(stderr.decode('utf-8'))))

    return (process.returncode, stdout, stderr)


def _truncate(s, length=8000):
    if len(s) > length:
        return s[:length-3] + '...'
    else:
        return s


def assert_command(
        cmd,
        returncode=0,
        stdout=b'',
        stderr=b'',
        env=None,
        stdin=None):
    """Execute CLI command and assert expected behavior.

    :param cmd: Program and arguments
    :type cmd: list of str
    :param returncode: Expected return code
    :type returncode: int
    :param stdout: Expected stdout
    :type stdout: str
    :param stderr: Expected stderr
    :type stderr: str
    :param env: Environment variables
    :type env: dict of str to str
    :param stdin: File to use for stdin
    :type stdin: file
    :rtype: None
    """

    returncode_, stdout_, stderr_ = exec_command(cmd, env, stdin)

    assert returncode_ == returncode
    assert stdout_ == stdout
    assert stderr_ == stderr


def mock_called_some_args(mock, *args, **kwargs):
    """Convience method for some mock assertions.  Returns True if the
    arguments to one of the calls of `mock` contains `args` and
    `kwargs`.

    :param mock: the mock to check
    :type mock: mock.Mock
    :returns: True if the arguments to one of the calls for `mock`
    contains `args` and `kwargs`.
    :rtype: bool
    """

    for call in mock.call_args_list:
        call_args, call_kwargs = call

        if any(arg not in call_args for arg in args):
            continue

        if any(k not in call_kwargs or call_kwargs[k] != v
               for k, v in kwargs.items()):
            continue

        return True

    return False


def watch_deployment(deployment_id, count):
    """ Wait for a deployment to complete.

    :param deployment_id: deployment id
    :type deployment_id: str
    :param count: max number of seconds to wait
    :type count: int
    :rtype: None
    """

    returncode, stdout, stderr = exec_command(
        ['dcos', 'marathon', 'deployment', 'watch',
            '--max-count={}'.format(count), deployment_id])

    assert returncode == 0
    assert stderr == b''


def watch_all_deployments(count=300):
    """ Wait for all deployments to complete.

    :param count: max number of seconds to wait
    :type count: int
    :rtype: None
    """

    deps = list_deployments()
    for dep in deps:
        watch_deployment(dep['id'], count)


def list_deployments(expected_count=None, app_id=None):
    """Get all active deployments.

    :param expected_count: assert that number of active deployments
    equals `expected_count`
    :type expected_count: int
    :param app_id: only get deployments for this app
    :type app_id: str
    :returns: active deployments
    :rtype: [dict]
    """

    cmd = ['dcos', 'marathon', 'deployment', 'list', '--json']
    if app_id is not None:
        cmd.append(app_id)

    returncode, stdout, stderr = exec_command(cmd)

    result = json.loads(stdout.decode('utf-8'))

    assert returncode == 0
    if expected_count is not None:
        assert len(result) == expected_count
    assert stderr == b''

    return result


def get_services(expected_count=None, args=[]):
    """Get services

    :param expected_count: assert exactly this number of services are
        running
    :type expected_count: int | None
    :param args: cli arguments
    :type args: [str]
    :returns: services
    :rtype: [dict]
    """

    returncode, stdout, stderr = exec_command(
        ['dcos', 'service', '--json'] + args)

    services = json.loads(stdout.decode('utf-8'))
    assert isinstance(services, collections.Sequence)
    if expected_count is not None:
        assert len(services) == expected_count

    return services


def show_app(app_id, version=None):
    """Show details of a Marathon application.

    :param app_id: The id for the application
    :type app_id: str
    :param version: The version, either absolute (date-time) or relative
    :type version: str
    :returns: The requested Marathon application
    :rtype: dict
    """

    if version is None:
        cmd = ['dcos', 'marathon', 'app', 'show', app_id]
    else:
        cmd = ['dcos', 'marathon', 'app', 'show',
               '--app-version={}'.format(version), app_id]

    returncode, stdout, stderr = exec_command(cmd)

    assert returncode == 0
    assert stderr == b''

    result = json.loads(stdout.decode('utf-8'))
    assert isinstance(result, dict)
    assert result['id'] == '/' + app_id

    return result


def service_shutdown(service_id):
    """Shuts down a service using the command line program

    :param service_id: the id of the service
    :type: service_id: str
    :rtype: None
    """

    assert_command(['dcos', 'service', 'shutdown', service_id])


def delete_zk_nodes():
    """Delete Zookeeper nodes that were created during the tests

    :rtype: None
    """

    base_url = os.environ['EXHIBITOR_URL']
    base_path = 'exhibitor/v1/explorer/znode/{}'

    for znode in ['universe', 'cassandra-mesos', 'chronos']:
        znode_url = urllib.parse.urljoin(
            base_url,
            base_path.format(znode))

        requests.delete(znode_url)


def assert_lines(cmd, num_lines):
    """ Assert stdout contains the expected number of lines

    :param cmd: program and arguments
    :type cmd: [str]
    :param num_lines: expected number of lines for stdout
    :type num_lines: int
    :rtype: None
    """
    returncode, stdout, stderr = exec_command(cmd)

    assert returncode == 0
    assert stderr == b''
    assert len(stdout.decode('utf-8').split('\n')) - 1 == num_lines


def _deploy_app(file_path, stdin=True):
    if stdin:
        with open(file_path) as fd:
            returncode, stdout, stderr = exec_command(
                ['dcos', 'marathon', 'app', 'add'], stdin=fd)
        assert returncode == 0
        assert stdout == b''
        assert stderr == b''
    else:
        assert_command(['dcos', 'marathon', 'app', 'add', file_path])

    # Let's make sure that we don't return until the deployment has finished
    watch_all_deployments()


def _remove_app(app_id):
    assert_command(['dcos', 'marathon', 'app', 'remove', app_id])

    # Let's make sure that we don't return until the deployment has finished
    watch_all_deployments()


@contextlib.contextmanager
def app(path, app_id, stdin=True):
    """Context manager that deploys an app on entrance, and removes it on
    exit.

    :param path: path to app's json definition
    :type path: str
    :param app_id: app id
    :type app_id: str
    :rtype: None
    """

    _deploy_app(path, stdin)
    try:
        yield
    finally:
        _remove_app(app_id)
