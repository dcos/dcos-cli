
from __future__ import absolute_import, print_function

import copy

from ... import cli
from ... import fake
from ... import service

parser = cli.parser(description="remove brokers from the kafka cluster")
parser.add_argument("number", type=int, help="number of brokers to remove")

@cli.init(parser)
def main(args):
    print(fake.stop_tasks(service.find("kafka"), args.number))
