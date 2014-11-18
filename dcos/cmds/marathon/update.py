
import argparse
import copy
import json
import sys

from ...marathon import completion_helpers
from ... import cli
from ...marathon import app
from ...marathon.scheduler import CURRENT as MARATHON

parser = cli.parser(
    description="update an existing app"
)

parser.add_argument(
    'app', help="""Name of the app."""
).completer = completion_helpers.app

parser.add_argument(
    'config', nargs='?', type=argparse.FileType('r'), default=sys.stdin,
    help="json config to use when creating an app"
)

@cli.init(parser)
def main(args):
    app = MARATHON.app(args.app)

    txt = ""

    if cli.has_data(args.config):
        txt = args.config.read()
    if len(txt) == 0:
        # XXX - Marathon can't take version as part of the config
        # (it will roll back to that version). There must be a better way to do
        # this.
        cfg = copy.deepcopy(app.config)
        del cfg["version"]
        txt = cli.edit_txt(json.dumps(cfg, indent=4))

    resp = app.update(txt)
    if resp:
        cli.json_out(resp)
