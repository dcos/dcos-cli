import subprocess

import dcoscli
import docopt
import pkg_resources
from concurrent.futures import ThreadPoolExecutor
from dcos import cmds, emitting, options, subcommand, util
from dcos.errors import DCOSException
from dcoscli.main import decorate_docopt_usage

emitter = emitting.FlatEmitter()
logger = util.get_logger(__name__)


def main():
    try:
        return _main()
    except DCOSException as e:
        emitter.publish(e)
        return 1


@decorate_docopt_usage
def _main():
    util.configure_process_from_environ()

    args = docopt.docopt(
        _doc(),
        version='dcos-help version {}'.format(dcoscli.version))

    return cmds.execute(_cmds(), args)


def _doc():
    """
    :rtype: str
    """
    return pkg_resources.resource_string(
        'dcoscli',
        'data/help/help.txt').decode('utf-8')


def _cmds():
    """
    :returns: All of the supported commands
    :rtype: list of dcos.cmds.Command
    """

    return [
        cmds.Command(
            hierarchy=['help', '--info'],
            arg_keys=[],
            function=_info),

        cmds.Command(
            hierarchy=['help'],
            arg_keys=['<command>'],
            function=_help),
    ]


def _info():
    """
    :returns: process return code
    :rtype: int
    """

    emitter.publish(_doc().split('\n')[0])
    return 0


def _help(command):
    """
    :param command: the command name for which you want to see a help
    :type command: str
    :returns: process return code
    :rtype: int
    """

    if command is not None:
        _help_command(command)
    else:
        logger.debug("DCOS bin path: {!r}".format(util.dcos_bin_path()))

        paths = subcommand.list_paths()
        with ThreadPoolExecutor(max_workers=len(paths)) as executor:
            results = executor.map(subcommand.documentation, paths)
            commands_message = options\
                .make_command_summary_string(sorted(results))

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


def _help_command(command):
    """
    :param command: the command name for which you want to see a help
    :type command: str
    :returns: process return code
    :rtype: int
    """

    executable = subcommand.command_executables(command)
    return subprocess.call([executable, command, '--help'])
