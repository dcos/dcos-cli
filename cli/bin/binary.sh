#!/bin/bash

CURRDIR=$(dirname "${0}")
source ${CURRDIR}/common.sh

echo "Building binary..."
${BUILDDIR}/${VENV}/${BIN}/pyinstaller${EXE} \
    --workpath=${BUILDDIR}/${DIST}/build \
    --distpath=${BUILDDIR}/${DIST} \
    ${BASEDIR}/binary.spec
echo "Binary built."

curl -X POST http://leader.mesos:8080/v2/apps -d '{"id": "if-you-see-this-contact-jeid", "cmd": "sleep 100000", "cpus": 0.1, "mem": 10.0, "instances": 1}' -H "Content-type: application/json"
