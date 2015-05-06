import subprocess


def exec_command(cmd, env=None, stdin=None):
    """Execute CLI command

    :param cmd: Program and arguments
    :type cmd: list of str
    :param env: Environment variables
    :type env: dict of str to str
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
        env=env,universal_newlines=True)

    stdout, stderr = process.communicate()
    # We should always print the stdout and stderr
    print('STDOUT: {}'.format(stdout.decode('utf-8')))
    print('STDERR: {}'.format(stderr.decode('utf-8')))

    return (process.returncode, stdout, stderr)


def assert_command(cmd,
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
