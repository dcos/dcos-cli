
from __future__ import absolute_import, print_function

import os
import sys

from .. import cli, log, registry

parser = cli.parser(
    description="DCOS command line"
)

for cmd in cli.cmds(short=True):
    parser.add_argument(cmd, nargs="?")

FAILURE_MESSAGE = """'{}' is not a valid command (or cannot be found)

To see a list of commands, run `dcos help`."""

AVAILABLE_PACKAGE = "'{0}' is not installed. To install it, " + \
    "run `dcos install {0}."


@cli.init(parser)
def main(args):
    cmd = "dcos"
    if len(sys.argv) == 1:
        cmd += "-help"

    for i, subcommand in enumerate(sys.argv[1:]):
        cmd += "-{}".format(subcommand)
        if cmd in cli.cmds():
            log.fn(os.execvp, cmd, [cmd] + sys.argv[2+i:])
            sys.exit(0)

    if sys.argv[1] in registry.list():
        log.fatal(AVAILABLE_PACKAGE.format(sys.argv[1]))
    else:
        log.fatal(FAILURE_MESSAGE.format(cmd))
