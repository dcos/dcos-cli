
from __future__ import absolute_import, print_function

import sys

from .marathon.scheduler import CURRENT as MARATHON

def find(name):
    tasks = MARATHON.app("fwk-{0}".format(name)).tasks
    if len(tasks) == 0:
        sys.exit(1)

    return "http://{0}:{1}".format(tasks[0]["host"], tasks[0]["ports"][0])
