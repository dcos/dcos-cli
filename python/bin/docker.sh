#!/bin/bash

CURRDIR=$(dirname "${0}")
source ${CURRDIR}/common.sh

: ${DOCKER_RUN:="docker run \
                     --rm \
                     -v ${BASEDIR}:/dcos-cli \
                     -v ${HOME}:/home/${USER} \
                     -v /etc/passwd:/etc/passwd:ro \
                     -v /etc/group:/etc/group:ro \
                     -e HOME=/home/${USER} \
                     -e VENV=${VENV_DOCKER} \
                     -e DIST=${DIST_DOCKER} \
                     -e TOX=${TOX_DOCKER} \
                     -w /dcos-cli \
                     -u $(id -u ${USER}):$(id -g ${USER}) \
                     python:3.5"}

for target in "${@}"; do
    ${DOCKER_RUN} make ${target}
done
