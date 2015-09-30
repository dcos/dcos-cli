#!/bin/bash

# You must set DCOS_CLI_VERSION to run this program

set -e -x

sed -i -e "s/\$dcos_cli_version/${DCOS_CLI_VERSION}/g" docker/Dockerfile

pushd docker

docker build -t mesosphere/dcos-cli:${DCOS_CLI_VERSION} .
docker tag -f mesosphere/dcos-cli:${DCOS_CLI_VERSION} mesosphere/dcos-cli:latest
docker push mesosphere/dcos-cli:${DCOS_CLI_VERSION}
docker push mesosphere/dcos-cli:latest

popd
