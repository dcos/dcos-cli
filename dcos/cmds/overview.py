
from __future__ import absolute_import, print_function

import blessings
import prettytable

from mesos.cli.master import CURRENT as MASTER
import mesos.cli.util

from .. import cli


@cli.init()
def main(args):
    term = blessings.Terminal()

    tb = prettytable.PrettyTable(
        [],
        border=False,
        max_table_width=term.width,
        hrules=prettytable.NONE,
        vrules=prettytable.NONE,
        left_padding_width=0,
        right_padding_width=1
    )

    def sum_resources(a, x):
        t = x["resources"]
        for k in t.keys():
            if k == "ports":
                continue
            a[k] = a.get(k, 0) + t.get(k, 0)
        return a

    resources = reduce(sum_resources, MASTER.slaves(), {})

    tb.add_column("CPUs", [resources["cpus"]])
    tb.add_column("Memory", [mesos.cli.util.humanize_bytes(resources["mem"] * 1024 * 1024)])
    tb.add_column("Disk", [mesos.cli.util.humanize_bytes(resources["disk"] * 1024 * 1024)])

    print(tb)
