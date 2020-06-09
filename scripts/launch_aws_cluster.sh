#!/bin/sh
set -euxo pipefail

export AWS_REGION="us-east-1"
export TF_VAR_dcos_user=$DCOS_TEST_DEFAULT_CLUSTER_USERNAME
export TF_VAR_dcos_pass_hash=$(perl -e 'print crypt($ENV{DCOS_TEST_DEFAULT_CLUSTER_PASSWORD},"\$6\$1234567890\$")')
export TF_VAR_dcos_license_key_contents=$DCOS_TEST_LICENSE
export TF_VAR_custom_dcos_download_path=$DCOS_TEST_INSTALLER_URL
export CLI_TEST_SSH_KEY_PATH
export TF_INPUT=false
export TF_IN_AUTOMATION=1
wget -q https://releases.hashicorp.com/terraform/0.11.14/terraform_0.11.14_linux_amd64.zip -O terraform_0.11.14_linux_amd64.zip
unzip -qq -o terraform_0.11.14_linux_amd64.zip
mkdir -p $HOME/.ssh
eval $(ssh-agent) >&2
ssh-add $CLI_TEST_SSH_KEY_PATH >&2
ssh-keygen -y -f $CLI_TEST_SSH_KEY_PATH > $HOME/.ssh/id_rsa.pub
./terraform init -no-color >&2
./terraform  apply -auto-approve -no-color >&2
./terraform output master_public_ip