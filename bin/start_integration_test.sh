#!/bin/bash

# List installed versions of external systems
dpkg -l marathon mesos zookeeper | grep '^ii'

# Start zookeeper
/usr/share/zookeeper/bin/zkServer.sh start

# Start Mesos master
mesos-master --zk=zk://localhost:2181/mesos --quorum=1 --log_dir=/var/log/mesos \
--work_dir=/var/lib/mesos 1>/dev/null 2>/dev/null &

# Start Mesos slave
mesos-slave --master=zk://localhost:2181/mesos --log_dir=/var/log/mesos \
 1>/dev/null 2>/dev/null &

# Start Marathon
service marathon start

# Give all of the processes above some time.
sleep 2

# move the dcos package
cd /dcos-cli

make clean env
source env/bin/activate
make || exit $?
deactivate

# Move down to the dcoscli package
cd cli

make clean env
source env/bin/activate
make || exit $?
deactivate
