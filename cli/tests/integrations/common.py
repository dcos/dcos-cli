import base64
import collections
import contextlib
import json
import os
import re
import subprocess
import time

import six
from six.moves import urllib

from dcos import config, http


def exec_command(cmd, env=None, stdin=None):
    """Execute CLI command

    :param cmd: Program and arguments
    :type cmd: [str]
    :param env: Environment variables
    :type env: dict | None
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
    :type stdout: bytes
    :param stderr: Expected stderr
    :type stderr: bytes
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


def watch_deployment(deployment_id, count):
    """Wait for a deployment to complete.

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


def watch_job_deployments(count=300):
    """Wait for all deployments to complete.

    :param count: max number of seconds to wait
    :type count: int
    :rtype: None
    """

    deps = list_job_deployments()
    for dep in deps:
        watch_deployment(dep['id'], count)


def watch_all_deployments(count=300):
    """Wait for all deployments to complete.

    :param count: max number of seconds to wait
    :type count: int
    :rtype: None
    """

    deps = list_deployments()
    for dep in deps:
        watch_deployment(dep['id'], count)


def wait_for_service(service_name, number_of_services=1, max_count=300):
    """Wait for service to register with Mesos

    :param service_name: name of service
    :type service_name: str
    :param number_of_services: number of services with that name
    :type number_of_services: int
    :param max_count: max number of seconds to wait
    :type max_count: int
    :rtype: None
    """

    count = 0
    while count < max_count:
        services = get_services()

        if (len([service for service in services
                 if service['name'] == service_name]) >= number_of_services):
            return

        count += 1


def add_job(app_path):
    """ Add a job, and wait for it to deploy

    :param app_path: path to job's json definition
    :type app_path: str
    :param wait: whether to wait for the deploy
    :type wait: bool
    :rtype: None
    """

    assert_command(['dcos', 'job', 'add', app_path])


def add_app(app_path, wait=True):
    """ Add an app, and wait for it to deploy

    :param app_path: path to app's json definition
    :type app_path: str
    :param wait: whether to wait for the deploy
    :type wait: bool
    :rtype: None
    """

    cmd = ['dcos', 'marathon', 'app', 'add', app_path]
    returncode, stdout, stderr = exec_command(cmd)
    assert returncode == 0
    assert re.fullmatch('Created deployment \S+\n', stdout.decode('utf-8'))
    assert stderr == b''

    if wait:
        watch_all_deployments()


def remove_group(group_id):
    assert_command(['dcos', 'marathon', 'group', 'remove', group_id])

    # Let's make sure that we don't return until the deployment has finished
    watch_all_deployments()


def remove_app(app_id):
    """ Remove an app

    :param app_id: id of app to remove
    :type app_id: str
    :rtype: None
    """

    assert_command(['dcos', 'marathon', 'app', 'remove', '--force', app_id])


def remove_job(app_id):
    """ Remove a job

    :param app_id: id of app to remove
    :type app_id: str
    :rtype: None
    """

    assert_command(['dcos', 'job', 'remove',
                    '--stop-current-job-runs', app_id])


def package_install(package, deploy=False, args=[]):
    """ Calls `dcos package install`

    :param package: name of the package to install
    :type package: str
    :param deploy: whether or not to wait for the deploy
    :type deploy: bool
    :param args: extra CLI args
    :type args: [str]
    :rtype: None
    """

    returncode, stdout, stderr = exec_command(
        ['dcos', 'package', 'install', '--yes', package] + args)

    assert returncode == 0
    assert stderr == b''

    if deploy:
        watch_all_deployments()


def package_uninstall(package, args=[], stderr=b''):
    """ Calls `dcos package uninstall`

    :param package: name of the package to uninstall
    :type package: str
    :param args: extra CLI args
    :type args: [str]
    :param stderr: expected string in stderr for package uninstall
    :type stderr: str
    :rtype: None
    """

    assert_command(
        ['dcos', 'package', 'uninstall', package] + args,
        stderr=stderr)


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

    assert returncode == 0
    assert stderr == b''

    services = json.loads(stdout.decode('utf-8'))
    assert isinstance(services, collections.Sequence)
    if expected_count is not None:
        assert len(services) == expected_count

    return services


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


def list_job_deployments(expected_count=None, app_id=None):
    """Get all active deployments.

    :param expected_count: assert that number of active deployments
    equals `expected_count`
    :type expected_count: int
    :param app_id: only get deployments for this app
    :type app_id: str
    :returns: active deployments
    :rtype: [dict]
    """

    cmd = ['dcos', 'job', 'list', '--json']
    if app_id is not None:
        cmd.append(app_id)

    returncode, stdout, stderr = exec_command(cmd)

    result = json.loads(stdout.decode('utf-8'))

    assert returncode == 0
    if expected_count is not None:
        assert len(result) == expected_count
    assert stderr == b''

    return result


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


def show_job(app_id):
    """Show details of a Metronome job.

    :param app_id: The id for the application
    :type app_id: str
    :returns: The requested Metronome job.
    :rtype: dict
    """

    cmd = ['dcos', 'job', 'show', app_id]

    returncode, stdout, stderr = exec_command(cmd)

    assert returncode == 0
    assert stderr == b''

    result = json.loads(stdout.decode('utf-8'))
    assert isinstance(result, dict)
    assert result['id'] == app_id

    return result


def show_job_schedule(app_id, schedule_id):
    """Show details of a Metronome schedule.

    :param app_id: The id for the job
    :type app_id: str
    :param schedule_id: The id for the schedule
    :type schedule_id: str
    :returns: The requested Metronome job.
    :rtype: dict
    """

    cmd = ['dcos', 'job', 'schedule', 'show', app_id, '--json']

    returncode, stdout, stderr = exec_command(cmd)

    assert returncode == 0
    assert stderr == b''

    result = json.loads(stdout.decode('utf-8'))
    assert isinstance(result[0], dict)
    assert result[0]['id'] == schedule_id

    return result[0]


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

    for znode in ['universe', 'cassandra-mesos', 'chronos']:
        delete_zk_node(znode)


def delete_zk_node(znode):
    """Delete Zookeeper node

    :param znode: znode to delete
    :type znode: str
    :rtype: None
    """

    dcos_url = config.get_config_val('core.dcos_url')
    znode_url = urllib.parse.urljoin(
        dcos_url,
        '/exhibitor/exhibitor/v1/explorer/znode/{}'.format(znode))
    http.delete(znode_url)


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


def file_json_ast(path):
    """Returns the JSON AST parsed from file
    :param path: path to file
    :type path: str
    :returns: parsed JSON AST
    """
    with open(path) as f:
        return json.load(f)


def json_ast_format(ast):
    """Returns the given JSON AST formatted as bytes

    :param ast: JSON AST
    :returns: formatted JSON
    :rtype: bytes
    """
    return six.b(
        json.dumps(ast,
                   sort_keys=True,
                   indent=2,
                   separators=(',', ': '))) + b'\n'


def file_json(path):
    """ Returns formatted json from file

    :param path: path to file
    :type path: str
    :returns: formatted json
    :rtype: bytes
    """
    return json_ast_format(file_json_ast(path))


@contextlib.contextmanager
def app(path, app_id, wait=True):
    """Context manager that deploys an app on entrance, and removes it on
    exit.

    :param path: path to app's json definition:
    :type path: str
    :param app_id: app id
    :type app_id: str
    :param wait: whether to wait for the deploy
    :type wait: bool
    :rtype: None
    """

    add_app(path, wait)
    try:
        yield
    finally:
        remove_app(app_id)
        watch_all_deployments()


@contextlib.contextmanager
def job(path, app_id):
    """Context manager that deploys an app on entrance, and removes it on
    exit.

    :param path: path to app's json definition:
    :type path: str
    :param app_id: app id
    :type app_id: str
    :param wait: whether to wait for the deploy
    :type wait: bool
    :rtype: None
    """

    add_job(path)
    try:
        yield
    finally:
        remove_job(app_id)


@contextlib.contextmanager
def update_config(name, value, env=None):
    """ Context manager for altering config for tests

    :param key: <key>
    :type key: str
    :param value: <value>
    :type value: str
    ;param env: env vars
    :type env: dict
    :rtype: None
    """

    returncode, stdout, _ = exec_command(
        ['dcos', 'config', 'show', name], env)

    result = None
    # config param already exists
    if returncode == 0:
        result = json.loads('"' + stdout.decode('utf-8').strip() + '"')

    # if we are setting a value
    if value is not None:
        config_set(name, value, env)
    # only unset if the config param already exists
    elif result is not None:
        config_unset(name, env)

    try:
        yield
    finally:
        # return config to previous state
        if result is not None:
            config_set(name, result, env)
        else:
            exec_command(['dcos', 'config', 'unset', name], env)


@contextlib.contextmanager
def package(package_name, deploy=False, args=[]):
    """Context manager that deploys an app on entrance, and removes it on
    exit.

    :param package_name: package name
    :type package_name: str
    :param deploy: If True, block on the deploy
    :type deploy: bool
    :rtype: None
    """

    package_install(package_name, deploy, args)
    try:
        yield
    finally:
        package_uninstall(package_name)
        watch_all_deployments()


def popen_tty(cmd):
    """Open a process with stdin connected to a pseudo-tty.  Returns a

    :param cmd: command to run
    :type cmd: str
    :returns: (Popen, master) tuple, where master is the master side
       of the of the tty-pair.  It is the responsibility of the caller
       to close the master fd, and to perform any cleanup (including
       waiting for completion) of the Popen object.
    :rtype: (Popen, int)

    """

    import pty
    master, slave = pty.openpty()
    proc = subprocess.Popen(cmd,
                            stdin=slave,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            preexec_fn=os.setsid,
                            close_fds=True,
                            shell=True)
    os.close(slave)

    return (proc, master)


def ssh_output(cmd):
    """ Runs an SSH command and returns the stdout/stderr/returncode.

    :param cmd: command to run
    :type cmd: str
    :rtype: (str, str, int)
    """

    print('SSH COMMAND: {}'.format(cmd))

    # ssh must run with stdin attached to a tty
    proc, master = popen_tty(cmd)

    # wait for the ssh connection
    time.sleep(5)

    proc.poll()
    returncode = proc.returncode

    # kill the whole process group
    try:
        os.killpg(os.getpgid(proc.pid), 15)
    except OSError:
        pass

    os.close(master)
    stdout, stderr = proc.communicate()

    print('SSH STDOUT: {}'.format(stdout.decode('utf-8')))
    print('SSH STDERR: {}'.format(stderr.decode('utf-8')))

    return stdout, stderr, returncode


def config_set(key, value, env=None):
    """ dcos config set <key> <value>

    :param key: <key>
    :type key: str
    :param value: <value>
    :type value: str
    ;param env: env vars
    :type env: dict
    :rtype: None
    """
    returncode, stdout, _ = exec_command(
        ['dcos', 'config', 'set', key, value],
        env=env)

    assert returncode == 0
    assert stdout == b''


def config_unset(key, env=None):
    """ dcos config unset <key> --index=<index>

    :param key: <key>
    :type key: str
    :param env: env vars
    :type env: dict
    :rtype: None
    """

    cmd = ['dcos', 'config', 'unset', key]

    returncode, stdout, stderr = exec_command(cmd, env=env)

    assert returncode == 0
    assert stdout == b''


def base64_to_dict(byte_string):
    """
    :param byte_string: base64 encoded string
    :type byte_string: str
    :return: python dictionary decoding of byte_string
    :rtype dict
    """
    return json.loads(base64.b64decode(byte_string).decode('utf-8'))


UNIVERSE_REPO = "https://universe.mesosphere.com/repo"
UNIVERSE_TEST_REPO = "http://universe.marathon.mesos:8085/repo"


def setup_universe_server():
    # add universe-server with static packages
    add_app('tests/data/universe-v3-stub.json', True)

    assert_command(
        ['dcos', 'package', 'repo', 'remove', 'Universe'])

    assert_command(
        ['dcos', 'package', 'repo', 'add', 'test-universe', UNIVERSE_TEST_REPO]
    )

    # Give the test universe some time to become available
    describe_command = ['dcos', 'package', 'describe', 'helloworld']
    for _ in range(30):
        returncode, _, _ = exec_command(describe_command)
        if returncode == 0:
            break
        time.sleep(1)
    else:
        # Explicitly clean up in this case; pytest will not automatically
        # perform teardowns if setup fails. See the remarks at the end of
        # http://doc.pytest.org/en/latest/xunit_setup.html for more info.
        teardown_universe_server()
        assert False, 'test-universe failed to come up'


def teardown_universe_server():
    assert_command(
        ['dcos', 'package', 'repo', 'remove', 'test-universe'])
    assert_command(
        ['dcos', 'package', 'repo', 'add', 'Universe', UNIVERSE_REPO])
    assert_command(
        ['dcos', 'marathon', 'app', 'remove', '/universe', '--force'])
