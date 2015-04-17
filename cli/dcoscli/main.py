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

import json
import logging
import os
import sys
from subprocess import PIPE, Popen

import dcoscli
import dcoscli.settings as settings
import docopt
import rollbar
from dcos.api import config, constants, emitting, http, subcommand, util
from dcoscli.constants import ROLLBAR_SERVER_POST_KEY

logger = logging.getLogger(__name__)
emitter = emitting.FlatEmitter()


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

    command = args['<command>']
    http.silence_requests_warnings()

    if not command:
        command = "help"

    executable, err = subcommand.command_executables(command, util.dcos_path())
    if err is not None:
        emitter.publish(err)
        return 1

    subproc = Popen([executable,  command] + args['<args>'],
                    stderr=PIPE)

    rollbar.init(ROLLBAR_SERVER_POST_KEY,
                 'prod' if settings.PRODUCTION else 'dev')
    return _wait_and_track(subproc)


def _wait_and_capture(subproc):
    # capture and print stderr
    err = ''
    while subproc.poll() is None:
        err_buff = subproc.stderr.read().decode('utf-8')
        sys.stderr.write(err_buff)
        err += err_buff

    exit_code = subproc.poll()

    return exit_code, err


def _wait_and_track(subproc):
    """
    :param subproc: Subprocess to capture
    :type subproc: Popen
    :returns: exit code of subproc
    :rtype: int
    """

    exit_code, err = _wait_and_capture(subproc)

    conf = config.load_from_path(
        os.environ[constants.DCOS_CONFIG_ENV])

    if err.startswith('Traceback') and conf.get('core.reporting', True):
        _track(exit_code, err, conf)

    return exit_code


def _track(exit_code, err, conf):
    """
    :param exit_code: exit code of tracked process
    :type exit_code: int
    :param err: stderr of tracked process
    :type err: str
    :param conf: dcos config file
    :type conf: Toml
    :rtype: None
    """

    # rollbar analytics
    try:
        rollbar.report_message(err, 'error', extra_data={
            'cmd': ' '.join(sys.argv),
            'exit_code': exit_code,
            'dcoscli.version': dcoscli.version,
            'config': json.dumps(list(conf.property_items()))
        })
    except Exception as e:
        logger.exception(e)


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
