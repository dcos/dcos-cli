"""
Usage:
    dcos [options] [<command>] [<args>...]

Options:
    --help                      Show this screen
    --version                   Show version
    --log-level=<log-level>     If set then print supplementary messages to
                                stderr at or above this level. The severity
                                levels in the order of severity are: debug,
                                info, warning, error, and critical. E.g.
                                Setting the option to warning will print
                                warning, error and critical messages to stderr.
                                Note: that this does not affect the output sent
                                to stdout by the command.

Environment Variables:
    DCOS_LOG_LEVEL              If set then it specifies that message should be
                                printed to stderr at or above this level. See
                                the --log-level option for details.

    DCOS_CONFIG                 This environment variable points to the
                                location of the DCOS configuration file.

'dcos help' lists all available subcommands. See 'dcos <command> --help'
to read about a specific subcommand.
"""


import logging
import os
import sys
from subprocess import PIPE, Popen

import analytics
import dcoscli
import docopt
import requests
from dcos.api import constants, emitting, subcommand, util

emitter = emitting.FlatEmitter()

WRITE_KEY = '51ybGTeFEFU1xo6u10XMDrr6kATFyRyh'


def main():
    if not _is_valid_configuration():
        return 1

    args = docopt.docopt(
        __doc__,
        version='dcos version {}'.format(dcoscli.version),
        options_first=True)

    if not _config_log_level_environ(args['--log-level']):
        return 1

    err = util.configure_logger_from_environ()
    if err is not None:
        emitter.publish(err)
        return 1

    # The requests package emits INFO logs.  We want to exclude those,
    # even if the user has selected --log-level=INFO.
    logging.getLogger('requests').setLevel(logging.WARNING)

    # urllib3 is printing an SSL warning we want to silence.  See
    # DCOS-1007.
    requests.packages.urllib3.disable_warnings()

    command = args['<command>']

    if not command:
        command = "help"

    executable, err = subcommand.command_executables(command, util.dcos_path())
    if err is not None:
        emitter.publish(err)
        return 1

    subproc = Popen([executable,  command] + args['<args>'],
                    stderr=PIPE)

    return wait_and_track(subproc)


def wait_and_track(subproc):
    # capture and print stderr
    err = ''
    while subproc.poll() is None:
        err_buff = subproc.stderr.read().decode('utf-8')
        sys.stderr.write(err_buff)
        err += err_buff

    exit_code = subproc.poll()

    # segment.io analytics
    analytics.write_key = WRITE_KEY
    try:
        # We don't have user id's right now, but segment.io requires
        # them, so we use a constant (1)
        analytics.track(1, 'dcos-cli', {
            'cmd': ' '.join(sys.argv),
            'exit_code': exit_code,
            'err': err or None
        })

        analytics.flush()
    except:
        # ignore segment.io exceptions
        pass

    return exit_code


def _config_log_level_environ(log_level):
    """
    :param log_level: Log level to set
    :type log_level: str
    :returns: True if the log level was configured correctly; False otherwise.
    :rtype: bool
    """

    if log_level is None:
        os.environ.pop(constants.DCOS_LOG_LEVEL_ENV, None)
        return True

    log_level = log_level.lower()
    if log_level in constants.VALID_LOG_LEVEL_VALUES:
        os.environ[constants.DCOS_LOG_LEVEL_ENV] = log_level
        return True

    msg = 'Log level set to an unknown value {!r}. Valid values are {!r}'
    emitter.publish(msg.format(log_level, constants.VALID_LOG_LEVEL_VALUES))

    return False


def _is_valid_configuration():
    """Validates running environment

    :returns: True if the environment is configure correctly; False otherwise.
    :rtype: bool
    """

    dcos_config = os.environ.get(constants.DCOS_CONFIG_ENV)
    if dcos_config is None:
        msg = 'Environment variable {!r} must be set to the DCOS config file.'
        emitter.publish(msg.format(constants.DCOS_CONFIG_ENV))
        return False

    if not os.path.isfile(dcos_config):
        msg = 'Environment variable {!r} maps to {!r} and it is not a file.'
        emitter.publish(msg.format(constants.DCOS_CONFIG_ENV, dcos_config))
        return False

    return True
