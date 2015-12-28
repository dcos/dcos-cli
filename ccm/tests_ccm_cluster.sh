#!/bin/bash

# This script expects the following env var:
#   CLI_TEST_SSH_KEY_PATH

set -e
set -o pipefail
set -x

# run tests
DCOS_PRODUCTION=false \
CLI_TEST_MASTER_PROXY=true \
CLI_TEST_SSH_KEY_PATH=/dcos-cli/mesosphere-aws.key \
./bin/start_tests.sh
