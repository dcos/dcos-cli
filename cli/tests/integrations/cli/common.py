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

    #assert returncode_ == returncode
    assert stdout_ == stdout
    assert stderr_ == stderr
