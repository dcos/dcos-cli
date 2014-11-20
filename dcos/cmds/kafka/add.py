
from __future__ import absolute_import, print_function

import copy

from ... import cli
from ... import fake
from ... import service

parser = cli.parser(
    description="add brokers to a kafka cluster"
)

parser.add_argument(
    "number", type=int, help="number of brokers to add"
)

NODE_CONFIG = {
    "mem": 10,
    "cpus": 0.1
}

@cli.init(parser)
def main(args):
    cfg = copy.copy(NODE_CONFIG)
    cfg["num"] = args.number
    print(fake.start_tasks(service.find("kafka"), cfg))
