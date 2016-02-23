import os
import signal
import sys
from functools import wraps
from subprocess import PIPE, Popen

import dcoscli
import docopt
import pkg_resources
from dcos import (auth, constants, emitting, errors, http, mesos, subcommand,
                  util)
from dcos.errors import DCOSAuthenticationException, DCOSException
from dcoscli import analytics

logger = util.get_logger(__name__)
emitter = emitting.FlatEmitter()


def main():
    try:
        return _main()
    except DCOSException as e:
        emitter.publish(e)
        return 1


def _main():
    signal.signal(signal.SIGINT, signal_handler)

    args = docopt.docopt(
        _doc(),
        version='dcos version {}'.format(dcoscli.version),
        options_first=True)

    log_level = args['--log-level']
    if log_level and not _config_log_level_environ(log_level):
        return 1

    if args['--debug']:
        os.environ[constants.DCOS_DEBUG_ENV] = 'true'

    util.configure_process_from_environ()

    if args['<command>'] != 'config' and \
       not auth.check_if_user_authenticated():
        auth.force_auth()

    config = util.get_config()
    set_ssl_info_env_vars(config)

    command = args['<command>']
    http.silence_requests_warnings()

    if not command:
        command = "help"

    executable = subcommand.command_executables(command)

    cluster_id = None
    if dcoscli.version != 'SNAPSHOT' and command and \
            command not in ["config", "help"]:
        try:
            cluster_id = mesos.DCOSClient().metadata().get('CLUSTER_ID')
        except DCOSAuthenticationException:
                raise
        except:
            msg = 'Unable to get the cluster_id of the cluster.'
            logger.exception(msg)

    # the call to retrieve cluster_id must happen before we run the subcommand
    # so that if you have auth enabled we don't ask for user/pass multiple
    # times (with the text being out of order) before we can cache the auth
    # token
    subproc = Popen([executable,  command] + args['<args>'],
                    stderr=PIPE)

    if dcoscli.version != 'SNAPSHOT':
        return analytics.wait_and_track(subproc, cluster_id)
    else:
        return analytics.wait_and_capture(subproc)[0]


def _doc():
    """
    :rtype: str
    """
    return pkg_resources.resource_string(
        'dcoscli',
        'data/help/dcos.txt').decode('utf-8')


def _config_log_level_environ(log_level):
    """
    :param log_level: Log level to set
    :type log_level: str
    :returns: True if the log level was configured correctly; False otherwise.
    :rtype: bool
    """

    log_level = log_level.lower()

    if log_level in constants.VALID_LOG_LEVEL_VALUES:
        os.environ[constants.DCOS_LOG_LEVEL_ENV] = log_level
        return True

    msg = 'Log level set to an unknown value {!r}. Valid values are {!r}'
    emitter.publish(msg.format(log_level, constants.VALID_LOG_LEVEL_VALUES))

    return False


def signal_handler(signal, frame):
    emitter.publish(
        errors.DefaultError("User interrupted command with Ctrl-C"))
    sys.exit(0)


def decorate_docopt_usage(func):
    """Handle DocoptExit exception

    :param func: function
    :type func: function
    :return: wrapped function
    :rtype: function
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
        except docopt.DocoptExit as e:
            emitter.publish("Command not recognized\n")
            emitter.publish(e)
            return 1
        return result
    return wrapper


def set_ssl_info_env_vars(config):
    """Set SSL info from config to environment variable if enviornment
       variable doesn't exist

    :param config: config
    :type config: Toml
    :rtype: None
    """

    if 'core.ssl_verify' in config and (
            not os.environ.get(constants.DCOS_SSL_VERIFY_ENV)):

        os.environ[constants.DCOS_SSL_VERIFY_ENV] = str(
            config['core.ssl_verify'])
