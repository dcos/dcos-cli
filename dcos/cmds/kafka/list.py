
from __future__ import absolute_import, print_function

from mesos.cli.master import CURRENT as MASTER

from ... import cli

parser = cli.parser(
    description="list kafka brokers"
)

@cli.init(parser)
def main(args):
    name = "kafka"

    tasks = [t for t in MASTER.tasks(active_only=True, fltr=name)
        if t["id"].index(name) == 0]

    print("Number of brokers: {0}".format(len(tasks)))
    print("Hostnames:")
    for t in tasks:
        print("\t{0}".format(t.slave["hostname"]))
