
from __future__ import absolute_import, print_function

from ... import cli
from ... import fake

parser = cli.parser(
    description="list running spark jobs"
)

@cli.init(parser)
def main(args):
    fake.list_tasks("spark")
