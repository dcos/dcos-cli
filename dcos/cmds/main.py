
from __future__ import absolute_import, print_function

import os
import sys

from .. import cli, log

parser = cli.parser(
    description="DCOS command line"
)

for cmd in cli.cmds(short=True):
    parser.add_argument(cmd, nargs="?")

FAILURE_MESSAGE = """'{}' is not a valid command (or cannot be found)

To see a list of commands, run `dcos help`."""



@cli.init(parser)
def main(args):
    if len(sys.argv) == 1:
        cmd = "dcos-help"
    else:
        cmd = "dcos-" + sys.argv[1]

    if cmd in cli.cmds():
        log.fn(os.execvp, cmd, [cmd] + sys.argv[2:])
    else:
        log.fatal(FAILURE_MESSAGE.format(cmd))
