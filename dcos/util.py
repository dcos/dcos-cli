import collections
import contextlib
import functools
import json
import logging
import os
import platform
import re
import shutil
import sys
import tempfile
import time
import subprocess
import struct

import jsonschema
import pystache
import six
from dcos import config, constants
from dcos.errors import DCOSException


def get_logger(name):
    """Get a logger

    :param name: The name of the logger. E.g. __name__
    :type name: str
    :returns: The logger for the specified name
    :rtype: logging.Logger
    """

    return logging.getLogger(name)


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
    :rtype: str
    """
    if not os.path.isfile(path):
        raise DCOSException('Path [{}] is not a file'.format(path))

    try:
        with open(path) as fd:
            return fd.read()
    except IOError:
        raise DCOSException('Unable to open file [{}]'.format(path))


def get_config():
    """
    :returns: Configuration object
    :rtype: Toml
    """

    return config.load_from_path(
        os.environ[constants.DCOS_CONFIG_ENV])


def get_config_vals(config, keys):
    """Gets config values for each of the keys.  Raises a DCOSException if
    any of the keys don't exist.

    :param config: config
    :type config: Toml
    :param keys: keys in the config dict
    :type keys: [str]
    :returns: values for each of the keys
    :rtype: [object]
    """

    missing = [key for key in keys if key not in config]
    if missing:
        msg = '\n'.join(
            'Missing required config parameter: "{0}".'.format(key) +
            '  Please run `dcos config set {0} <value>`.'.format(key)
            for key in keys)
        raise DCOSException(msg)

    return [config[key] for key in keys]


def which(program):
    """Returns the path to the named executable program.

    :param program: The program to locate:
    :type program: str
    :rtype: str
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
    if is_windows_platform() and not program.endswith('.exe'):
        return which(program + '.exe')
    return None


def dcos_path():
    """Returns the real DCOS path based on the current executable

    :returns: the real path to the DCOS path
    :rtype: str
    """

    return os.path.dirname(os.path.dirname(os.sys.executable))


def configure_logger_from_environ():
    """Configure the program's logger using the environment variable

    :rtype: None
    """

    return configure_logger(os.environ.get(constants.DCOS_LOG_LEVEL_ENV))


def configure_logger(log_level):
    """Configure the program's logger.

    :param log_level: Log level for configuring logging
    :type log_level: str
    :rtype: None
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
    raise DCOSException(
        msg.format(log_level, constants.VALID_LOG_LEVEL_VALUES))


def load_json(reader):
    """Deserialize a reader into a python object

    :param reader: the json reader
    :type reader: a :code:`.read()`-supporting object
    :returns: the deserialized JSON object
    :rtype: dict | list | str | int | float | bool
    """

    try:
        return json.load(reader)
    except Exception as error:
        logger.error(
            'Unhandled exception while loading JSON: %r',
            error)
        raise DCOSException('Error loading JSON: {}'.format(error))


def load_jsons(value):
    """Deserialize a string to a python object

    :param value: The JSON string
    :type value: str
    :returns: The deserialized JSON object
    :rtype: dict | list | str | int | float | bool
    """

    try:
        return json.loads(value)
    except:
        error = sys.exc_info()[0]
        logger.error(
            'Unhandled exception while loading JSON: %r -- %r',
            value,
            error)
        raise DCOSException('Error loading JSON.')


def validate_json(instance, schema):
    """Validate an instance under the given schema.

    :param instance: the instance to validate
    :type instance: dict
    :param schema: the schema to validate with
    :type schema: dict
    :returns: list of errors as strings
    :rtype: list
    """

    def sort_key(ve):
        return six.u(_hack_error_message_fix(ve.message))

    validator = jsonschema.Draft4Validator(schema)
    validation_errors = list(validator.iter_errors(instance))
    validation_errors = sorted(validation_errors, key=sort_key)

    return [_format_validation_error(e) for e in validation_errors]


# TODO(jsancio): clean up this hack
# The error string from jsonschema already contains improperly formatted
# JSON values, so we have to resort to removing the unicode prefix using
# a regular expression.
def _hack_error_message_fix(message):
    """
    :param message: message to fix by removing u'...'
    :type message: str
    :returns: the cleaned up message
    :rtype: str
    """

    # This regular expression matches the character 'u' followed by the
    # single-quote character, all optionally preceded by a left square
    # bracket, parenthesis, curly brace, or whitespace character.
    return re.compile("([\[\(\{\s])u'").sub(
        "\g<1>'",
        re.compile("^u'").sub("'", message))


def _format_validation_error(error):
    """
    :param error: validation error to format
    :type error: jsonchema.exceptions.ValidationError
    :returns: string representation of the validation error
    :rtype: str
    """

    error_message = _hack_error_message_fix(error.message)

    match = re.search("(.+) is a required property", error_message)
    if match:
        message = 'Error: missing required property {}.'.format(
            match.group(1))
    else:
        message = 'Error: {}\n'.format(error_message)
        if len(error.absolute_path) > 0:
            message += 'Path: {}\n'.format(
                       '.'.join([str(path) for path in error.absolute_path]))
        message += 'Value: {}'.format(json.dumps(error.instance))

    return message


def create_schema(obj):
    """ Creates a basic json schema derived from `obj`.

    :param obj: object for which to derive a schema
    :type obj: str | int | float | dict | list
    :returns: json schema
    :rtype: dict
    """

    if isinstance(obj, six.string_types):
        return {'type': 'string'}

    elif isinstance(obj, six.integer_types):
        return {'type': 'integer'}

    elif isinstance(obj, float):
        return {'type': 'number'}

    elif isinstance(obj, collections.Mapping):
        schema = {'type': 'object',
                  'properties': {},
                  'additionalProperties': False,
                  'required': obj.keys()}

        for key, val in obj.items():
            schema['properties'][key] = create_schema(val)

        return schema

    elif isinstance(obj, collections.Sequence):
        schema = {'type': 'array'}
        if obj:
            schema['items'] = create_schema(obj[0])
        return schema

    else:
        raise ValueError(
            'Cannot create schema with object {} of unrecognized type'
            .format(str(obj)))


def list_to_err(errs):
    """convert list of error strings to a single string

    :param errors: list of string errors
    :type errors: list of strings
    :returns: error message
    :rtype: str
    """

    return str.join('\n\n', errs)


def parse_int(string):
    """Parse string and an integer

    :param string: string to parse as an integer
    :type string: str
    :returns: the interger value of the string
    :rtype: int
    """

    try:
        return int(string)
    except:
        error = sys.exc_info()[0]
        logger.error(
            'Unhandled exception while parsing string as int: %r -- %r',
            string,
            error)
        raise DCOSException('Error parsing string as int')


def render_mustache_json(template, data):
    """Render the supplied mustache template and data as a JSON value

    :param template: the mustache template to render
    :type template: str
    :param data: the data to use as a rendering context
    :type data: dict
    :returns: the rendered template
    :rtype: dict | list | str | int | float | bool
    """

    try:
        r = CustomJsonRenderer()
        rendered = r.render(template, data)
    except Exception as e:
        raise DCOSException(e)

    logger.debug('Rendered mustache template: %s', rendered)

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


def duration(fn):
    """ Decorator to log the duration of a function.

    :param fn: function to measure
    :type fn: function
    :returns: wrapper function
    :rtype: function
    """

    @functools.wraps(fn)
    def timer(*args, **kwargs):
        start = time.time()
        try:
            return fn(*args, **kwargs)
        finally:
            logger.debug("duration: {0}.{1}: {2:2.2f}s".format(
                fn.__module__,
                fn.__name__,
                time.time() - start))

    return timer


def humanize_bytes(b):
    """ Return a human representation of a number of bytes.

    :param b: number of bytes
    :type b: number
    :returns: human representation of a number of bytes
    :rtype: str
    """

    abbrevs = (
        (1 << 30, 'GB'),
        (1 << 20, 'MB'),
        (1 << 10, 'kB'),
        (1, 'B')
    )
    for factor, suffix in abbrevs:
        if b >= factor:
            break

    return "{0:.2f} {1}".format(b/float(factor), suffix)


def get_terminal_size():
    """Return terminal width and height works on linux,os x,windows, cygwin(windows)

    :returns: width and height terminal
    :rtype: (width, height)
    """

    tuple_xy = None
    if is_windows_platform():
        tuple_xy = _get_terminal_size_windows()
        if tuple_xy is None:
            tuple_xy = _get_terminal_size_tput()
    current_os = platform.system()
    if current_os in ['Linux', 'Darwin'] or current_os.startswith('CYGWIN'):
        tuple_xy = _get_terminal_size_linux()
    if tuple_xy is None:
        tuple_xy = (80, 25)      # default value
    return tuple_xy


def _get_terminal_size_tput():
    """Return terminal width and height for windows

    :returns: width and height terminal
    :rtype: (width, height)
    """

    try:
        cols = int(subprocess.check_call(shlex.split('tput cols')))
        rows = int(subprocess.check_call(shlex.split('tput lines')))
        return (cols, rows)
    except:
        pass

def _get_terminal_size_windows():
    """Return terminal width and height for windows

    :returns: width and height terminal
    :rtype: (width, height)
    """

    try:
        from ctypes import windll, create_string_buffer
        # stdin handle is -10
        # stdout handle is -11
        # stderr handle is -12
        h = windll.kernel32.GetStdHandle(-12)
        csbi = create_string_buffer(22)
        res = windll.kernel32.GetConsoleScreenBufferInfo(h, csbi)
        if res:
            (bufx, bufy, curx, cury, wattr,
             left, top, right, bottom,
             maxx, maxy) = struct.unpack("hhhhHhhhhhh", csbi.raw)
            sizex = right - left + 1
            sizey = bottom - top + 1
            return sizex, sizey
    except:
        pass


def _get_terminal_size_linux():
    """Return terminal width and height for linux

    :returns: width and height terminal
    :rtype: (width, height)
    """

    def ioctl_GWINSZ(fd):
        try:
            import fcntl
            import termios
            cr = struct.unpack('hh',
                               fcntl.ioctl(fd, termios.TIOCGWINSZ, '1234'))
            return cr
        except:
            pass
    cr = ioctl_GWINSZ(0) or ioctl_GWINSZ(1) or ioctl_GWINSZ(2)
    if not cr:
        try:
            fd = os.open(os.ctermid(), os.O_RDONLY)
            cr = ioctl_GWINSZ(fd)
            os.close(fd)
        except:
            pass
    if not cr:
        try:
            cr = (os.environ['LINES'], os.environ['COLUMNS'])
        except:
            return None
    return int(cr[1]), int(cr[0])

logger = get_logger(__name__)
