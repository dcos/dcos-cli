import os
import signal
import sys

import docopt
from six.moves import urllib

import dcoscli
from dcos import config, constants, emitting, errors, http, subcommand, util
from dcos.errors import DCOSException
from dcoscli.subcommand import default_doc, SubcommandMain


logger = util.get_logger(__name__)
emitter = emitting.FlatEmitter()


def main():
    try:
        return _main()
    except DCOSException as e:
        emitter.publish(e)
        return 1


def _get_versions(dcos_url):
    """Print DC/OS and DC/OS-CLI versions

    :param dcos_url: url to DC/OS cluster
    :type dcos_url: str
    :returns: Process status
    :rtype: int
    """

    dcos_info = {}
    try:
        url = urllib.parse.urljoin(
            dcos_url, 'dcos-metadata/dcos-version.json')
        res = http.get(url, timeout=1)
        if res.status_code == 200:
            dcos_info = res.json()
    except Exception as e:
        logger.exception(e)
        pass

    emitter.publish(
        "dcoscli.version={}\n".format(dcoscli.version) +
        "dcos.version={}\n".format(dcos_info.get("version", "N/A")) +
        "dcos.commit={}\n".format(dcos_info.get(
            "dcos-image-commit", "N/A")) +
        "dcos.bootstrap-id={}".format(dcos_info.get("bootstrap-id", "N/A"))
    )
    return 0


def _main():
    signal.signal(signal.SIGINT, signal_handler)

    http.silence_requests_warnings()

    args = docopt.docopt(default_doc("dcos"), options_first=True)

    log_level = args['--log-level']
    if log_level and not _config_log_level_environ(log_level):
        return 1

    if args['--debug']:
        os.environ[constants.DCOS_DEBUG_ENV] = 'true'

    util.configure_process_from_environ()

    if args['--version']:
        return _get_versions(config.get_config_val("core.dcos_url"))

    command = args['<command>']

    if not command:
        command = "help"

    if command in subcommand.default_subcommands():
        sc = SubcommandMain(command, args['<args>'])
    else:
        executable = subcommand.command_executables(command)
        sc = subcommand.SubcommandProcess(
            executable, command, args['<args>'])

    exitcode, _ = sc.run_and_capture()
    return exitcode


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

if __name__ == "__main__":
    sys.exit(main())
