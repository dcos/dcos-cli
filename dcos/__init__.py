"""
Usage:
    dcos [--mesos=<uri>] <command> [<args>...]
    dcos -h | --help
    dcos --version

Options:
    -h, --help           Show this screen
    --version            Show version
    --mesos=<uri>        URI for the Mesos master
"""

import os
import subprocess
import docopt


def main():
    subcommands = _list_external_subcommands(os.environ['DCOS_PATH'])
    subcommand_summaries = _external_command_documentation(subcommands)

    args = docopt.docopt(
        _extend_usage_docopt(__doc__, subcommand_summaries),
        version='dcos version 0.1.0',  # TODO: grab from setuptool
        options_first=True)

    argv = [args['<command>']] + args['<args>']

    # TODO: We need to figure out a way to make subcommand's discoverable
    if args['<command>'] in subcommands:
        command = 'dcos-{}'.format(args['<command>'])
        exit(subprocess.call([command] + argv))
    else:
        exit(
            '{!r} is not a dcos command. See "dcos --help".'.format(
                args['<command>']))


def _list_external_subcommands(dcos_path):
    # TODO: check that dir_path is directory?
    prefix = 'dcos-'

    return [filename[len(prefix):]

            for dirpath, _, filenames
            in os.walk(os.path.join(dcos_path, "bin"))

            for filename in filenames

            if filename.startswith(prefix)
            and os.access(os.path.join(dirpath, filename), os.X_OK)
            ]


def _external_command_documentation(commands):
    def info(commnand):
        return subprocess.check_output(
            ['dcos-{}'.format(command), command, 'info'])

    return [(command, info(command)) for command in commands]


def _extend_usage_docopt(doc, command_summaries):
    # TODO: make sure that we deal with long commands
    doc += '\nThe dcos commands are:'
    for command, summary in command_summaries:
        doc += '\n\t{:15}\t{}'.format(command, summary.strip())

    return doc
