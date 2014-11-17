
from __future__ import absolute_import, print_function

from ... import cli
from ...marathon.cfg import CURRENT as CFG

parser = cli.parser(
    description="interact with your local cli configuration"
)

parser.add_argument(
    "key", nargs="?", choices=CFG.DEFAULTS.keys() + ["profile"])

parser.add_argument("value", nargs="?")


@cli.init(parser)
def main(args):
    if args.key:
        if args.value:
            CFG[args.key] = args.value
            CFG.save()
        else:
            cli.json_out(CFG[args.key])
    else:
        cli.json_out(CFG)
