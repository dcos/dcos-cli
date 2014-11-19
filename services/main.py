
from __future__ import absolute_import, print_function

import argparse
import time
import threading

from . import scheduler

parser = argparse.ArgumentParser(
    description="startup a fake framework"
)

parser.add_argument(
    'name', choices=[ "cassandra", "kafka", "spark" ]
)

parser.add_argument('version')

def main(args):
    driver = scheduler.FakeScheduler(args.name, args.version).get_driver()

    t = threading.Thread(target=driver.run)
    t.setDaemon(True)
    t.start()

    while t.isAlive():
        time.sleep(0.5)

if __name__ == "__main__":
    main(parser.parse_args())

Spark
Cassandra
Kafka
Jenkins
Kubernetes
DEIS
HDFS
Hadoop
Yarn
Accumulo
ElasticSearch
Aurora
Marathon
Storm
