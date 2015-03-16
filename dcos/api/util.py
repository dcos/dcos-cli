import contextlib
import inspect
import json
import logging
import os
import shutil
import sys
import tempfile

import jsonschema
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
    elif constants.PATH_ENV in os.environ:
        for path in os.environ[constants.PATH_ENV].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return None


def process_executable_path():
    """Returns the real path to the program for this running process

    :returns: the real path to the program
    :rtype: str
    """

    return os.path.realpath(inspect.stack()[-1][1])


def dcos_path():
    """Returns the real path to the DCOS path based on the executable

    :returns: the real path to the DCOS path
    :rtype: str
    """
    return os.path.dirname(os.path.dirname(process_executable_path()))


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


def load_json(reader):
    """Deserialize a reader into a python object

    :param reader: the json reader
    :type reader: a :code:`.read()`-supporting object
    :returns: the deserialized JSON object
    :rtype: (any, Error) where any is one of dict, list, str, int, float or
            bool
    """

    try:
        return (json.load(reader), None)
    except:
        error = sys.exc_info()[0]
        logger = get_logger(__name__)
        logger.error(
            'Unhandled exception while loading JSON: %r',
            error)
        return (None, errors.DefaultError('Error loading JSON.'))


def load_jsons(value):
    """Deserialize a string to a python object

    :param value: The JSON string
    :type value: str
    :returns: The deserialized JSON object
    :rtype: (any, Error) where any is one of dict, list, str, int, float or
            bool
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


def validate_json(instance, schema):
    """Validate an instance under the given schema.

    :param instance: the instance to validate
    :type instance: dict
    :param schema: the schema to validate with
    :type schema: dict
    :returns: an error if the validation failed; None otherwise
    :rtype: Error
    """
    try:
        jsonschema.validate(instance, schema)
        return None
    except jsonschema.ValidationError as ve:
        return errors.DefaultError(ve.message)
