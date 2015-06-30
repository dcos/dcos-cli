"""Display command line usage information

Usage:
    dcos help --info
    dcos help

Options:
    --help     Show this screen
    --info     Show a short description of this subcommand
    --version  Show version
"""

import dcoscli
import docopt
from concurrent.futures import ThreadPoolExecutor
from dcos import cmds, emitting, options, subcommand, util
from dcos.errors import DCOSException

emitter = emitting.FlatEmitter()
logger = util.get_logger(__name__)


def main():
    try:
        return _main()
    except DCOSException as e:
        emitter.publish(e)
        return 1


def _main():
    util.configure_logger_from_environ()

    args = docopt.docopt(
        __doc__,
        version='dcos-help version {}'.format(dcoscli.version))

    return cmds.execute(_cmds(), args)


def _cmds():
    """
    :returns: All of the supported commands
    :rtype: list of dcos.cmds.Command
    """

    return [
        cmds.Command(
            hierarchy=['help'],
            arg_keys=['--info'],
            function=_help),
    ]


def _help(show_info):
    if show_info:
        emitter.publish(__doc__.split('\n')[0])
        return 0

    directory = util.dcos_path()
    logger.debug("DCOS Path: {!r}".format(directory))

    paths = subcommand.list_paths()
    with ThreadPoolExecutor(max_workers=len(paths)) as executor:
        results = executor.map(subcommand.documentation, paths)
        commands_message = options.make_command_summary_string(sorted(results))

    emitter.publish(
        "Command line utility for the Mesosphere Datacenter Operating\n"
        "System (DCOS). The Mesosphere DCOS is a distributed operating\n"
        "system built around Apache Mesos. This utility provides tools\n"
        "for easy management of a DCOS installation.\n")
    emitter.publish("Available DCOS commands:")
    emitter.publish(commands_message)
    emitter.publish(
        "\nGet detailed command description with 'dcos <command> --help'.")

    return 0
