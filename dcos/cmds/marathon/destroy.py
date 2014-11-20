
from __future__ import absolute_import, print_function

from ...marathon import completion_helpers
from ... import cli
from ...marathon.scheduler import CURRENT as MARATHON

parser = cli.parser(
    description="""destroys an app

Note that this will remove the app from marathon completely and cause the
destruction of any running tasks."""
)

parser.add_argument(
    'app', help="""Name of the app."""
).completer = completion_helpers.app

@cli.init(parser)
def main(args):
    resp = MARATHON.app(args.app).destroy()
    if resp:
        cli.json_out(resp)
