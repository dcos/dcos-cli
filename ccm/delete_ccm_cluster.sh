#!/bin/bash

# This script expects the following env var:
#   CCM_AUTH_TOKEN
#   CLUSTER_ID

set -e
set -o pipefail

http --ignore-stdin DELETE https://ccm.mesosphere.com/api/cluster/${CLUSTER_ID}/ Authorization:"Token ${CCM_AUTH_TOKEN}"
