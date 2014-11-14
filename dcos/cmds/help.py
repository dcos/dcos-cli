
from __future__ import absolute_import, print_function

from .. import cli


USAGE = """Usage: dcos <command> [OPTIONS]

Available commands:
\t{cmds}
"""


@cli.init()
def main(args=None):
    print(USAGE.format(cmds="\n\t".join(cli.cmds(short=True))))
