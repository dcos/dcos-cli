
from __future__ import absolute_import, print_function

import argparse
import sys

from ... import cli
from ... import fake
from ... import service

parser = cli.parser(
    description="run a job"
)

parser.add_argument(
    'config', nargs='?', type=argparse.FileType('r'),
    help="json config to use when creating an app"
)

@cli.init(parser)
def main(args):
    print(fake.start_tasks(service.find("spark"), args.config.read()))

