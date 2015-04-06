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
from dcos.api import cmds, emitting, options, subcommand, util

emitter = emitting.FlatEmitter()


def main():
    err = util.configure_logger_from_environ()
    if err is not None:
        emitter.publish(err)
        return 1

    args = docopt.docopt(
        __doc__,
        version='dcos-help version {}'.format(dcoscli.version))

    returncode, err = cmds.execute(_cmds(), args)
    if err is not None:
        emitter.publish(err)
        emitter.publish(options.make_generic_usage_message(__doc__))
        return 1

    return returncode


def _cmds():
    """
    :returns: All of the supported commands
    :rtype: dcos.api.cmds.Command
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
    commands_message = options.make_command_summary_string(
        sorted(
            subcommand.documentation(command_path)
            for command_path
            in subcommand.list_paths(directory)))

    emitter.publish(
        "Command line utility for the Mesosphere Datacenter Operating\n"
        "System (DCOS). The Mesosphere DCOS is a distributed operating\n"
        "system built around Apache Mesos. This utility provides tools\n"
        "for easy management of a DCOS installation.\n")
    emitter.publish("Available DCOS commands in {!r}:".format(directory))
    emitter.publish(commands_message)
    emitter.publish(
        "\nGet detailed command description with 'dcos <command> --help'.")

    return 0
