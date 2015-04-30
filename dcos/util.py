import contextlib
import json
import logging
import os
import platform
import re
import shutil
import sys
import tempfile

import jsonschema
import pystache
import six
from dcos import config, constants, errors


@contextlib.contextmanager
def tempdir():
    """A context manager for temporary directories.

    The lifetime of the returned temporary directory corresponds to the
    lexical scope of the returned file descriptor.

    :return: Reference to a temporary directory
    :rtype: str
    """

    tmpdir = tempfile.mkdtemp()
    try:
        yield tmpdir
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


@contextlib.contextmanager
def temptext():
    """A context manager for temporary files.

    The lifetime of the returned temporary file corresponds to the
    lexical scope of the returned file descriptor.

    :return: reference to a temporary file
    :rtype: (fd, str)
    """

    fd, path = tempfile.mkstemp()
    try:
        yield (fd, path)
    finally:
        # Close the file descriptor and ignore errors
        try:
            os.close(fd)
        except OSError:
            pass

        # delete the path
        shutil.rmtree(path, ignore_errors=True)


def ensure_dir(directory):
    """If `directory` does not exist, create it.

    :param directory: path to the directory
    :type directory: string
    :rtype: None
    """

    if not os.path.exists(directory):
        logger.info('Creating directory: %r', directory)
        os.makedirs(directory, 0o775)


def read_file(path):
    """
    :param path: path to file
    :type path: str
    :returns: contents of file
    :rtype: (str, Error)
    """
    if not os.path.isfile(path):
        return (None, errors.DefaultError(
            'Path [{}] is not a file'.format(path)))

    try:
        with open(path) as fd:
            content = fd.read()
            return (content, None)
    except IOError:
        return (None, errors.DefaultError(
            'Unable to open file [{}]'.format(path)))


def get_config():
    """
    :returns: Configuration object
    :rtype: Toml
    """

    return config.load_from_path(
        os.environ[constants.DCOS_CONFIG_ENV])


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


def dcos_path():
    """Returns the real DCOS path based on the current executable

    :returns: the real path to the DCOS path
    :rtype: str
    """

    dcos_bin_dir = os.path.realpath(sys.argv[0])
    return os.path.dirname(os.path.dirname(dcos_bin_dir))


def configure_logger_from_environ():
    """Configure the program's logger using the environment variable

    :returns: An Error if we were unable to configure logging from the
              environment; None otherwise
    :rtype: dcos.errors.DefaultError
    """

    return configure_logger(os.environ.get(constants.DCOS_LOG_LEVEL_ENV))


def configure_logger(log_level):
    """Configure the program's logger.

    :param log_level: Log level for configuring logging
    :type log_level: str
    :returns: An Error if we were unable to configure logging; None otherwise
    :rtype: dcos.errors.DefaultError
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
    except Exception as error:
        logger = get_logger(__name__)
        logger.error(
            'Unhandled exception while loading JSON: %r',
            error)
        return (
            None,
            errors.DefaultError('Error loading JSON: {}'.format(error))
        )


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
    :returns: list of errors as strings
    :rtype: list
    """

    # TODO: clean up this hack
    #
    # The error string from jsonschema already contains improperly formatted
    # JSON values, so we have to resort to removing the unicode prefix using
    # a regular expression.
    def hack_error_message_fix(message):
        # This regular expression matches the character 'u' followed by the
        # single-quote character, all optionally preceded by a left square
        # bracket, parenthesis, curly brace, or whitespace character.
        return re.compile("([\[\(\{\s])u'").sub(
            "\g<1>'",
            re.compile("^u'").sub("'", message))

    def sort_key(ve):
        return six.u(hack_error_message_fix(ve.message))

    validator = jsonschema.Draft4Validator(schema)
    validation_errors = list(validator.iter_errors(instance))
    validation_errors = sorted(validation_errors, key=sort_key)

    def format(error):
        error_message = hack_error_message_fix(error.message)
        match = re.search("(.+) is a required property", error_message)
        if match:
            return ('Error: missing required property ' +
                    match.group(1) +
                    '. Add to JSON file and pass in /path/to/file with the' +
                    ' --options argument.')
        message = 'Error: {}\n'.format(error_message)
        if len(error.absolute_path) > 0:
            message += 'Path: {}\n'.format('.'.join(error.absolute_path))
        message += 'Value: {}'.format(json.dumps(error.instance))
        return message

    return [format(e) for e in validation_errors]


def list_to_err(errs):
    """convert list of errors to Error

    :param errors: list of string errors
    :type errors: list of strings
    :returns: error message
    :rtype: Error
    """

    errs_as_str = str.join('\n\n', errs)
    return errors.DefaultError(errs_as_str)


def parse_int(string):
    """Parse string and an integer

    :param string: string to parse as an integer
    :type string: str
    :returns: the interger value of the string
    :rtype: (int, Error)
    """

    try:
        return (int(string), None)
    except:
        error = sys.exc_info()[0]
        logger = get_logger(__name__)
        logger.error(
            'Unhandled exception while parsing string as int: %r -- %r',
            string,
            error)
        return (None, errors.DefaultError('Error parsing string as int'))


def render_mustache_json(template, data):
    """Render the supplied mustache template and data as a JSON value

    :param template: the mustache template to render
    :type template: str
    :param data: the data to use as a rendering context
    :type data: dict
    :returns: the rendered template
    :rtype: (any, Error) where any is one of dict, list, str, int, float or
            bool
    """

    try:
        r = CustomJsonRenderer()
        rendered = r.render(template, data)
    except Exception as e:
        return (None, errors.DefaultError(e.message))

    return load_jsons(rendered)


def is_windows_platform():
    """
    :returns: True is program is running on Windows platform, False
     in other case
    :rtype: boolean
    """
    return platform.system() == "Windows"


class CustomJsonRenderer(pystache.Renderer):
    def str_coerce(self, val):
        """
        Coerce a non-string value to a string.
        This method is called whenever a non-string is encountered during the
        rendering process when a string is needed (e.g. if a context value
        for string interpolation is not a string).

        :param val: the mustache template to render
        :type val: any
        :returns: a string containing a JSON representation of the value
        :rtype: str
        """
        return json.dumps(val)

logger = get_logger(__name__)
