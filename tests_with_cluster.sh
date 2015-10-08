#!/bin/bash

# This script expects the following env var:
#   CLUSTER_NAME
#   DCOS_CONFIG

set -e
set -o pipefail
set -x

#create cluster
http --ignore-stdin \ccm.mesosphere.com/api/cluster/ \
     Authorization:"Token ji4weySp4ix5bueRb0Uj2loM9Jan3juD7Wan3yin9leeT9gEm5" \
     name=$CLUSTER_NAME \
     cloud_provider=AWS \
     region=us-west-2 \
     time=60 \
     channel=stable \
     cluster_desc="DCOS CLI testing cluster" \
     template=single-master.cloudformation.json \
     adminlocation=0.0.0.0/0 \
     public_agents=0 \
     private_agents=1

# wait for cluster to come up
while true; do
    STATUS=$(http --ignore-stdin \
                  ccm.mesosphere.com/api/cluster/active/all/ \
                  Authorization:"Token ji4weySp4ix5bueRb0Uj2loM9Jan3juD7Wan3yin9leeT9gEm5" | \
                    jq ".[] | select(.name == \"$CLUSTER_NAME\") | .status");
    if [ $STATUS -eq 0 ]; then
        break;
    fi;
    sleep 10;
done;

# get dcos_url
CLUSTER_INFO=$(http GET ccm.mesosphere.com/api/cluster/active/all/ Authorization:'Token ji4weySp4ix5bueRb0Uj2loM9Jan3juD7Wan3yin9leeT9gEm5' | jq ".[] | select(.name == \"$CLUSTER_NAME\") | .cluster_info")
CLUSTER_ID=$(http GET ccm.mesosphere.com/api/cluster/active/all/ Authorization:'Token ji4weySp4ix5bueRb0Uj2loM9Jan3juD7Wan3yin9leeT9gEm5' | jq ".[] | select(.name == \"$CLUSTER_NAME\") | .id")
eval CLUSTER_INFO=$CLUSTER_INFO  # unescape json

DCOS_URL=$(echo "$CLUSTER_INFO" | jq ".DnsAddress")
DCOS_URL=${DCOS_URL:1:-1}

# run tests
DCOS_PRODUCTION=false \
               DCOS_URL=$DCOS_URL \
               CLI_TEST_SSH_KEY_PATH=/dcos-cli/mesosphere-aws.key \
               CLI_TEST_AWS=true \
               ./bin/start_tests.sh

# Uncomment this line to delete the cluster after the tests run
# http --ignore-stdin DELETE ccm.mesosphere.com/api/cluster/${CLUSTER_ID}/ Authorization:'Token ji4weySp4ix5bueRb0Uj2loM9Jan3juD7Wan3yin9leeT9gEm5'
