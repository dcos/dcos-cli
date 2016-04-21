#!/bin/bash

set -e
set -o pipefail

# run tests
CLI_TEST_MASTER_PROXY=true \
CLI_TEST_SSH_KEY_PATH=/dcos-cli/mesosphere-aws.key \
echo "dcos_acs_token = \"$DCOS_ACS_TOKEN\"" >> /dcos-cli/cli/tests/data/dcos.toml && \
./bin/start_tests.sh
