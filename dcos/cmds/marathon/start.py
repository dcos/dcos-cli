
from __future__ import absolute_import, print_function

import argparse
import sys

from mesos.cli.master import CURRENT as MASTER

from ...marathon import util
from ...marathon.scheduler import CURRENT as MARATHON
from ... import cli

parser = cli.parser(
    description="""start an app"""
)

parser.add_argument(
    'config', nargs='?', type=argparse.FileType('r'), default=sys.stdin,
    help="json config to use when creating an app"
)

@cli.init(parser)
def main(args):
    txt = ""

    if cli.has_data(args.config):
        txt = args.config.read()
    if len(txt) == 0:
        txt = cli.edit_txt(re.sub("(\"id\": )\"\"", "\\1\"{0}\"".format(_id),
            util.get_data("new.json")))

    resp = MARATHON.create(txt)
    if resp:
        cli.json_out(resp)
