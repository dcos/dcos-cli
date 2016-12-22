#!/bin/bash

# This script expects the following env var:
#   AWS_PROD_ACCESS_KEY_ID
#   AWS_PROD_SECRET_ACCESS_KEY

set -xe

wget 'https://downloads.mesosphere.io/dcos-enterprise/testing/master/dcos_generate_config.ee.sh'
mkdir -p genconf
cat <<EOF > genconf/config.yaml
aws_template_storage_bucket: downloads.mesosphere.io
aws_template_storage_bucket_path: dcos-cli/testing/master/all-features
aws_template_upload: true
aws_template_storage_access_key_id: $AWS_PROD_ACCESS_KEY_ID
aws_template_storage_secret_access_key: $AWS_PROD_SECRET_ACCESS_KEY
cosmos_config:
  staged_package_storage_uri: file:///var/lib/dcos/cosmos/staged-packages
  package_storage_uri: file:///var/lib/dcos/cosmos/packages
EOF
bash dcos_generate_config.ee.sh --aws-cloudformation

CF_TEMPLATE_URL='https://s3.amazonaws.com/downloads.mesosphere.io/dcos-cli/testing/master/all-features/cloudformation/ee.single-master.cloudformation.json'
echo "$CF_TEMPLATE_URL"
