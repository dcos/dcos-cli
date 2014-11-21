
from __future__ import absolute_import, print_function

import json

from ..cfg import CURRENT as CFG
from .. import cli
from .. import registry
from ..marathon import util
from ..marathon.scheduler import CURRENT as MARATHON


parser = cli.parser(
    description="Install a Datacenter service on your DCOS"
)

parser.add_argument(
    "service", choices=registry.names()
)

@cli.init(parser)
def main(args):
    data = json.loads(util.get_data("{0}.json".format(args.service)))
    data["env"]["MASTER"] = CFG["master"]

    cli.json_out(MARATHON.create(json.dumps(data)))
    CFG["installed"].append(args.service)
    CFG.save()
