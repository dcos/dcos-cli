import logging
import subprocess


def exec_command(cmd, env=None):
    """Execute CLI command

    :param cmd: Program and arguments
    :type cmd: list of str
    :param env: Environment variables
    :type env: dict of str to str
    :returns: A tuple with the returncode, stdout and stderr
    :rtype: (int, bytes, bytes)
    """

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env)

    stdout, stderr = process.communicate()

    # We should always print the stdout and stderr
    logging.error('STDOUT: %s', stdout.decode('utf-8'))
    logging.error('STDERR: %s', stderr.decode('utf-8'))

    return (process.returncode, stdout, stderr)
