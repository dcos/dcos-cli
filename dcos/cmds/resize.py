
from __future__ import absolute_import, print_function

import subprocess

from .. import cli


parser = cli.parser(
    description="Set the cluster to be a specific size"
)

parser.add_argument(
    "num", type=int
)

cmd = "gcloud preview managed-instance-groups --zone us-central1-a resize demo --new-size {}"

@cli.init(parser)
def main(args):
    print(subprocess.check_output(cmd.format(args.num), shell=True))
