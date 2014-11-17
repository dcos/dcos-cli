
from __future__ import absolute_import, print_function

import argparse
import sys

from mesos.cli.master import CURRENT as MASTER

from ...marathon import completion_helpers
from ...marathon.scheduler import CURRENT as MARATHON
from ... import cli

parser = cli.parser(
    description="""scale an app"""
)

parser.add_argument(
    'app', help="""Name of the app."""
).completer = completion_helpers.app

parser.add_argument(
    'instance_count', help="Number of instances to launch.", type=int
)

@cli.init(parser)
def main(args):
    cli.json_out(MARATHON.app(args.app).update({
        "instances": args.instance_count
    }))

