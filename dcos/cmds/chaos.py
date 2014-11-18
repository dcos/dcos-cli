
from __future__ import absolute_import, print_function

import sys
import time

from mesos.cli.master import CURRENT as MASTER

from ..marathon import util
from ..marathon.scheduler import CURRENT as MARATHON
from .. import cli

parser = cli.parser(
    description="chaos on your cluster"
)


@cli.init(parser)
def main(args):
    MARATHON.create(util.get_data("chaos.json"))
    app = MARATHON.app("chaos")
    sys.stdout.write("shutting down hosts")
    try:
        while True:
            sys.stdout.write(".")
            time.sleep(1)
    finally:
        app.destroy()

    print("Completed.")
