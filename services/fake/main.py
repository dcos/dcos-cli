
from __future__ import absolute_import, print_function

import argparse
import logging
import os
import sys
import time
import threading

from . import scheduler
from . import server

def setup_logging():
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    root.addHandler(ch)

    server.app.logger.addHandler(root)


def main():
    setup_logging()
    scheduler.CURRENT = scheduler.FakeScheduler(
        os.environ["NAME"], os.environ["VERSION"])

    scheduler.CURRENT.run()
    server.app.run(
        host='0.0.0.0',
        port=int(os.environ["PORT"])
    )

if __name__ == "__main__":
    main()
