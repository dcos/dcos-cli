"""Display command line usage information

Usage:
    dcos help
    dcos help --all
    dcos help info

Options:
    --help              Show this screen
    --version           Show version
    --all               Prints all available commands to the standard output
"""
import dcoscli
import docopt
from dcos.api import emitting, options, subcommand, util

emitter = emitting.FlatEmitter()


def main():
    err = util.configure_logger_from_environ()
    if err is not None:
        emitter.publish(err)
        return 1

    args = docopt.docopt(
        __doc__,
        version='dcos-help version {}'.format(dcoscli.version))

    if args['help'] and args['info']:
        emitter.publish(__doc__.split('\n')[0])
    # Note: this covers --all also.
    # Eventually we will only show commonly used commands for help
    # and use --all to show, well, all commands.
    elif args['help']:
        directory = util.dcos_path()
        commands_message = options.make_command_summary_string(
            sorted(
                subcommand.documentation(command_path)
                for command_path
                in subcommand.list_paths(directory)))

        emitter.publish(
            "Command line utility for the Mesosphere DataCenter Operating "
            "System (DCOS). The Mesosphere DCOS is a distributed operating "
            "system built around Apache Mesos. This utility provides tools "
            "for easy management of a DCOS installation.\n")
        emitter.publish("Available DCOS commands in {!r}:".format(directory))
        emitter.publish(commands_message)
        emitter.publish(
            "\nGet detailed command description with 'dcos <command> --help'.")

        return 0
    else:
        emitter.publish(options.make_generic_usage_message(__doc__))
        return 1
