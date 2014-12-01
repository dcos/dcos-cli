
from __future__ import absolute_import, print_function

import subprocess

from .. import cli


parser = cli.parser(
    description="Set the cluster to be a specific size"
)

parser.add_argument(
    "num", type=int
)

cmd = "gcloud --project modern-saga-648 preview managed-instance-groups --zone us-central1-a resize demo --new-size 50"

@cli.init(parser)
def main(args):
    print(subprocess.check_output(cmd, shell=True))
