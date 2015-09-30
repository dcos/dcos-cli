#!/bin/bash

# You must set DCOS_CLI_VERSION to run this program

if [ -z "$DCOS_CLI_VERSION" ]; then
    echo "Please set the DCOS_CLI_VERSION env var."
    exit 1;
fi

set -e -x

sed -i -e "s/\$docker_cli_version/${DCOS_CLI_VERSION}/g" docker/Dockerfile

pushd docker

docker build -t mesosphere/dcos-cli:${DCOS_CLI_VERSION} .
docker tag -f mesosphere/dcos-cli:${DCOS_CLI_VERSION} mesosphere/dcos-cli:latest
docker push mesosphere/dcos-cli:${DCOS_CLI_VERSION}
docker push mesosphere/dcos-cli:latest

popd
