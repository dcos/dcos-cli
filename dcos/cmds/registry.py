
from __future__ import absolute_import, print_function

import blessings
import prettytable

from .. import cli
from .. import registry


@cli.init()
def main(args):
    term = blessings.Terminal()

    tb = prettytable.PrettyTable(
        ["Service", "Version"],
        border=False,
        max_table_width=term.width,
        hrules=prettytable.NONE,
        vrules=prettytable.NONE,
        left_padding_width=0,
        right_padding_width=1
    )

    for entry in registry.list():
        tb.add_row(entry.values())

    print(tb)
