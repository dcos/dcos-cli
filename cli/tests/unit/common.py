import contextlib
import sys

import mock
import six


@contextlib.contextmanager
def mock_args(args):
    """ Context manager that mocks sys.args and captures stdout/stderr

    :param args: sys.args values to mock
    :type args: [str]
    :rtype: None
    """
    with mock.patch('sys.argv', ['dcos'] + args):
        stdout, stderr = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = six.StringIO(), six.StringIO()
        try:
            yield sys.stdout, sys.stderr
        finally:
            sys.stdout, sys.stderr = stdout, stderr


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


def exec_mock(main, args):
    """Call a main function with sys.args mocked, and capture
    stdout/stderr

    :param main: main function to call
    :type main: function
    :param args: sys.args to mock, excluding the initial 'dcos'
    :type args: [str]
    :returns: (returncode, stdout, stderr)
    :rtype: (int, bytes, bytes)
    """

    print('MOCK ARGS: {}'.format(' '.join(args)))

    with mock_args(args) as (stdout, stderr):
        returncode = main(args)

    stdout_val = six.b(stdout.getvalue())
    stderr_val = six.b(stderr.getvalue())

    print('STDOUT: {}'.format(stdout_val))
    print('STDERR: {}'.format(stderr_val))

    return (returncode, stdout_val, stderr_val)


def assert_mock(main,
                args,
                returncode=0,
                stdout=b'',
                stderr=b''):
    """Mock and call a main function, and assert expected behavior.

    :param main: main function to call
    :type main: function
    :param args: sys.args to mock, excluding the initial 'dcos'
    :type args: [str]
    :type returncode: int
    :param stdout: Expected stdout
    :type stdout: str
    :param stderr: Expected stderr
    :type stderr: str
    :rtype: None
    """

    returncode_, stdout_, stderr_ = exec_mock(main, args)

    assert returncode_ == returncode
    assert stdout_ == stdout
    assert stderr_ == stderr
