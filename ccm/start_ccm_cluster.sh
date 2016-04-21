#!/bin/bash

# This script expects the following env var:
#   CLUSTER_NAME
#   CCM_AUTH_TOKEN
#   DCOS_CHANNEL

set -e

# create cluster
CLUSTER_ID=$(http --ignore-stdin \https://ccm.mesosphere.com/api/cluster/ \
     Authorization:"Token ${CCM_AUTH_TOKEN}" \
     name=$CLUSTER_NAME \
     cloud_provider=0 \
     region=us-west-2 \
     time=120 \
     channel=$DCOS_CHANNEL \
     cluster_desc="DCOS CLI testing cluster" \
     template=single-master.cloudformation.json \
     adminlocation=0.0.0.0/0 \
     public_agents=0 \
     private_agents=1 | \
     jq ".id");

echo $CLUSTER_ID
