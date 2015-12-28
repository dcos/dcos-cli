#!/bin/bash -x

# This script expects the following env vars:
#   DCOS_URL
#   DCOS_CONFIG (this path will be overwritten)
#   CLI_TEST_SSH_KEY_PATH (path to cluster ssh key)
#   CLI_TEST_MASTER_PROXY (true or false, depending on if DCOS_URL points to an AWS cluster)
#
# CWD is assumed to be the dcos-cli repo root

make clean env
source env/bin/activate
make || exit $?
deactivate

# Move down to the dcoscli package
cd cli

cp tests/data/dcos.toml $DCOS_CONFIG

make clean env
source env/bin/activate
make || exit $?
deactivate
