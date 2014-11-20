
from ...marathon import completion_helpers
from ... import cli
from ...marathon.scheduler import CURRENT as MARATHON

parser = cli.parser(
    description="""stops an app

Note that this will stop all the currently running tasks but leave the app
still defined in marathon."""
)

parser.add_argument(
    'app', help="""Name of the app."""
).completer = completion_helpers.app

@cli.init(parser)
def main(args):
    resp = MARATHON.app(args.app).stop()
    if resp:
        cli.json_out(resp)
