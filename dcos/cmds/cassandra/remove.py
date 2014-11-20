
from __future__ import absolute_import, print_function

import copy

from ... import cli
from ... import fake
from ... import service

parser = cli.parser(description="remove nodes from the cassandra cluster")
parser.add_argument("number", type=int, help="number of nodes to remove")

@cli.init(parser)
def main(args):
    print(fake.stop_tasks(service.find("cassandra"), args.number))
