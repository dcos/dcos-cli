import contextlib
import json
import logging
import os
import shutil
import sys
import tempfile

from dcos.api import constants, errors


@contextlib.contextmanager
def tempdir():
    """A context manager for temporary directories.

    The lifetime of the returned temporary directory corresponds to the
    lexical scope of the returned file descriptor.

    :return: Reference to a temporary directory
    :rtype: file descriptor
    """

    tmpdir = tempfile.mkdtemp()
    try:
        yield tmpdir
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def which(program):
    """Returns the path to the named executable program.

    :param program: The program to locate:
    :type program: str
    :rtype: str or Error
    """

    def is_exe(file_path):
        return os.path.isfile(file_path) and os.access(file_path, os.X_OK)

    file_path, filename = os.path.split(program)
    if file_path:
        if is_exe(program):
            return program
    else:
        for path in os.environ[constants.PATH_ENV].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return None


def configure_logger_from_environ():
    """Configure the program's logger using the environment variable

    :returns: An Error if we were unable to configure logging from the
              environment; None otherwise
    :rtype: dcos.api.errors.DefaultError
    """

    return configure_logger(os.environ.get(constants.DCOS_LOG_LEVEL_ENV))


def configure_logger(log_level):
    """Configure the program's logger.

    :param log_level: Log level for configuring logging
    :type log_level: str
    :returns: An Error if we were unable to configure logging; None otherwise
    :rtype: dcos.api.errors.DefaultError
    """
    if log_level is None:
        logging.disable(logging.CRITICAL)
        return None

    if log_level in constants.VALID_LOG_LEVEL_VALUES:
        logging.basicConfig(
            format='%(message)s',
            stream=sys.stderr,
            level=log_level.upper())
        return None

    msg = 'Log level set to an unknown value {!r}. Valid values are {!r}'
    return errors.DefaultError(
        msg.format(log_level, constants.VALID_LOG_LEVEL_VALUES))


def get_logger(name):
    """Get a logger

    :param name: The name of the logger. E.g. __name__
    :type name: str
    :returns: The logger for the specified name
    :rtype: logging.Logger
    """

    return logging.getLogger(name)


def load_jsons(value):
    """Deserialize a string to a python object

    :param value: The JSON string
    :type value: str
    :returns: The deserealized JSON object
    :type: (any, Error) where any is one of dict, list, str, int, float or bool
    """

    try:
        return (json.loads(value), None)
    except:
        error = sys.exc_info()[0]
        logger = get_logger(__name__)
        logger.error(
            'Unhandled exception while loading JSON: %r -- %r',
            value,
            error)
        return (None, errors.DefaultError('Error loading JSON.'))
