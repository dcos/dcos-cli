
from __future__ import absolute_import, print_function

import sys

from .. import cli


USAGE = """Usage: dcos {name} <command> [OPTIONS]

Available commands:
\t{cmds}
"""


@cli.init()
def main(args=None):
    cmd = sys.argv[0].split("-")[-2]

    print(USAGE.format(name=cmd, cmds='\n\t'.join(map(lambda x: x.split("-")[-1],
        filter(lambda x: cmd in x, cli.cmds(short=True))))))
