#!/bin/bash
# Init
# Make sure only root can run our script
if [ "$(id -u)" != "0" ]; then
   echo "This script must be run as root" 1>&2
   exit 1
fi

yum -y install wget
pip install virtualenv
mkdir -p /opt/mesosphere
wget https://downloads.mesosphere.com/dcos-cli/install.sh
./install.sh /opt/mesosphere/cli http://127.0.0.1 --add-path no
tar -cvfz dcos-cli.tgz /opt/mesosphere/cli
bash build-dcos-cli-offline.sh --binary dcos-cli.tgz
