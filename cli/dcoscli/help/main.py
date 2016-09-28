from concurrent.futures import ThreadPoolExecutor

import docopt

import dcoscli
from dcos import cmds, emitting, options, subcommand, subprocess, util
from dcos.errors import DCOSException
from dcoscli.subcommand import (default_command_documentation,
                                default_command_info, default_doc)
from dcoscli.util import decorate_docopt_usage

emitter = emitting.FlatEmitter()
logger = util.get_logger(__name__)


def main(argv):
    try:
        return _main(argv)
    except DCOSException as e:
        emitter.publish(e)
        return 1


@decorate_docopt_usage
def _main(argv):
    args = docopt.docopt(
        default_doc("help"),
        argv=argv,
        version='dcos-help version {}'.format(dcoscli.version))

    return cmds.execute(_cmds(), args)


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
            arg_keys=['<subcommand>'],
            function=_help),
    ]


def _info():
    """
    :returns: process return code
    :rtype: int
    """

    emitter.publish(default_command_info("help"))
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

        results = [(c, default_command_info(c))
                   for c in subcommand.default_subcommands()]
        paths = subcommand.list_paths()
        with ThreadPoolExecutor(max_workers=max(len(paths), 1)) as executor:
            results += list(executor.map(subcommand.documentation, paths))
            commands_message = options\
                .make_command_summary_string(sorted(results))

        emitter.publish(
            "Command line utility for the Mesosphere Datacenter Operating\n"
            "System (DC/OS). The Mesosphere DC/OS is a distributed operating\n"
            "system built around Apache Mesos. This utility provides tools\n"
            "for easy management of a DC/OS installation.\n")
        emitter.publish("Available DC/OS commands:")
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

    if command in subcommand.default_subcommands():
        emitter.publish(default_command_documentation(command))
        return 0
    else:
        executable = subcommand.command_executables(command)
        return subprocess.Subproc().call([executable, command, '--help'])
