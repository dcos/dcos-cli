
from __future__ import absolute_import, print_function

from ..marathon import completion_helpers
from .. import cli
from ..marathon.scheduler import CURRENT as MARATHON

parser = cli.parser(
    description="""uninstalls a service"""
)

parser.add_argument(
    'service', help="""Name of the app."""
).completer = completion_helpers.service

@cli.init(parser)
def main(args):
    cli.json_out(MARATHON.app("fwk-{0}".format(args.service)).destroy())
