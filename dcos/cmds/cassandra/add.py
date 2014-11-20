
from __future__ import absolute_import, print_function

from ... import cli
from ... import service

parser = cli.parser(
    description="add nodes to a cassandra cluster"
)

parser.add_argument(
    "number", type=int, help="number of nodes to add"
)

@cli.init(parser)
def main(args):
    print(service.find("cassandra"))
