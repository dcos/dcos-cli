import base64
import contextlib
import json
import os
import subprocess
import time
import zipfile

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

    assert returncode_ == returncode, (returncode_, returncode)
    assert stdout_ == stdout, (stdout_, stdout)
    assert stderr_ == stderr, (stderr_, stderr)


def delete_zk_nodes():
    """Delete Zookeeper nodes that were created during the tests

    :rtype: None
    """

    for znode in ['universe', 'dcos-service-cassandra', 'chronos']:
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


def assert_lines(cmd, num_lines, greater_than=False):
    """ Assert stdout contains the expected number of lines

    :param cmd: program and arguments
    :type cmd: [str]
    :param num_lines: expected number of lines for stdout
    :type num_lines: int
    :param greater_than: if True assume there may be at least num_lines or more
    :type greater_than: bool
    :rtype: None
    """

    returncode, stdout, stderr = exec_command(cmd)

    assert returncode == 0
    assert stderr == b''
    lines = len(stdout.decode('utf-8').split('\n')) - 1
    if greater_than:
        assert lines >= num_lines
        return
    assert lines == num_lines


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


def fetch_valid_json(cmd):
    """Assert stdout contains valid JSON

    :param cmd: program and arguments
    :type cmd: [str]
    :returns: parsed JSON AST
    """
    returncode, stdout, stderr = exec_command(cmd)

    assert returncode == 0
    assert stderr == b''
    try:
        return json.loads(stdout.decode('utf-8'))
    except json.JSONDecodeError:
        error_text = 'Command "{}" returned invalid JSON'.format(' '.join(cmd))
        raise Exception(error_text)


def file_json(path):
    """ Returns formatted json from file

    :param path: path to file
    :type path: str
    :returns: formatted json
    :rtype: bytes
    """
    return json_ast_format(file_json_ast(path))


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

    # when we change the dcos_url we remove the acs_token
    # we need to also restore the token if this occurs
    token = None
    if name == "core.dcos_url":
        returncode_, token_val, _ = exec_command(
            ['dcos', 'config', 'show', "core.dcos_acs_token"], env)
        if returncode_ == 0:
            token = token_val.decode('utf-8').strip()

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

    if token:
        config_set("core.dcos_acs_token", token, env)


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
    """ dcos config unset <key>

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


def zip_contents_as_json(path, inner_file):
    with zipfile.ZipFile(path) as zip_file:
        inner_file_contents = zip_file.read(inner_file).decode()
    return json.loads(inner_file_contents)
