#!/bin/bash -x

# This script expects the following env vars:
#   DCOS_URL
#   DCOS_CONFIG (this path will be overwritten)
#   CLI_TEST_SSH_KEY_PATH (path to cluster ssh key)
#   CLI_TEST_AWS (true or false, depending on if DCOS_URL points to an AWS cluster)
#
# CWD is assumed to be the dcos-cli repo root

make clean env
source env/bin/activate
make || exit $?
deactivate

# Move down to the dcoscli package
cd cli

# overwrite core.dcos_url in the dcos.toml
cp ./tests/data/dcos.toml $DCOS_CONFIG
sed -i "s/change.dcos.url/$DCOS_URL/g" $DCOS_CONFIG

make clean env
source env/bin/activate
make || exit $?
deactivate
