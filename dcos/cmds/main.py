
from __future__ import absolute_import, print_function

import os
import sys

from .. import cli, log, registry

FAILURE_MESSAGE = """'{}' is not a valid command (or cannot be found)

To see a list of commands, run `dcos help`."""

AVAILABLE_PACKAGE = "'{0}' is not installed. To install it, " + \
    "run `dcos install {0}."

def exec_cmd(cmd, args):
    log.fn(os.execvp, cmd, [cmd] + args)
    sys.exit(0)

@cli.init()
def main(args):
    if len(sys.argv) == 1:
        exec_cmd("dcos-help", [])

    cmd = "dcos"
    for i, subcommand in enumerate(sys.argv[1:]):
        cmd += "-{}".format(subcommand)
        if cmd in cli.cmds():
            exec_cmd(cmd, sys.argv[2+i:])

    if len(sys.argv) > 1 and sys.argv[1] in registry.names():
        log.fatal(AVAILABLE_PACKAGE.format(sys.argv[1]))
    else:
        log.fatal(FAILURE_MESSAGE.format(cmd))
