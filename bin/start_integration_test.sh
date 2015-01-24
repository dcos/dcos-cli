#!/bin/bash

# Start zookeeper
/usr/share/zookeeper/bin/zkServer.sh start

# Start Mesos and redirect stdout to /dev/null
/usr/bin/mesos-local --num_slaves=2 --quiet &

# Start Marathon
/etc/init.d/marathon start

# Give all of the processes above some time.
sleep 2

# Run the tox integration tests
tox -c /dcos-cli/tox.ini
