#!/bin/bash

# Need to first update the local repo before installing anything
apt-get -y update

# Install Git (TODO(CD): Remove this, for testing only)
apt-get -y install git

# Install the latest Marathon
apt-get -y install marathon

# List installed versions of external systems
dpkg -l marathon mesos zookeeper | grep '^ii'

# Start zookeeper
/usr/share/zookeeper/bin/zkServer.sh start

# Start Mesos and redirect stdout to /dev/null
/usr/bin/mesos-local --num_slaves=2 --quiet &

# Start Marathon
/etc/init.d/marathon start

# Give all of the processes above some time.
sleep 2

# Clean and recreate environment
cd /dcos-cli
make clean env

# Activate the virtual environment so that we can run make
source env/bin/activate

# Run the default target: E.g. test and package
make
