
from __future__ import absolute_import, print_function

import importlib
import os
import sys

from .. import registry
from .. import log
from .. import cli

"""Provide tab completions for python subcommands.

To debug, add `_ARC_DEBUG` to your env.
"""

EXIT = sys.exit


def complete_cmd(name=""):
    print("\n".join([x for x in cli.cmds(short=True) if x.startswith(name)]))


def cmd_options(cmd):
    os.environ["_ARGCOMPLETE_IFS"] = "\n"
    os.environ["_ARGCOMPLETE_WORDBREAKS"] = os.environ.get(
        "COMP_WORDBREAKS", "")
    os.environ["_ARGCOMPLETE"] = "2"

    try:
        mod = importlib.import_module(
            ".{0}".format('.'.join(cmd)), package="dcos.cmds")
    except ImportError, e:
        return

    if not hasattr(mod, 'parser'):
        return

    importlib.import_module("argcomplete").autocomplete(
        mod.parser,
        output_stream=sys.stdout,
        exit_method=EXIT
    )


def usage():
    print("""Please look at the README for instructions on setting command
completion up for your shell.""")


@cli.init()
def main(args):
    cmdline = os.environ.get('COMP_LINE') or \
        os.environ.get('COMMAND_LINE') or ''
    cmdpoint = int(os.environ.get('COMP_POINT') or len(cmdline))

    words = cmdline[:cmdpoint].split()

    if len(words) == 0:
        return usage()
    elif len(words) == 1:
        return complete_cmd()
    elif len(words) == 2:
        if cmdline[-1] == " ":
            return cmd_options(words[1])
        else:
            return complete_cmd(words[1])
    else:
        w = [words[1]]

        # XXX - This is really, really horrible. Without altering, argcomplete
        # can't find the right argument positioning.
        if w[0] in registry.list():
            w.append(words[2])
            os.environ['COMP_LINE'] = "-".join(words[:2]) + " " + \
                " ".join(words[2:])
        return cmd_options(w)
