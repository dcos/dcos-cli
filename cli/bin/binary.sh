#!/bin/bash

CURRDIR=$(dirname "${0}")
source ${CURRDIR}/common.sh

if [ -n "${TAG_NAME-}" ]; then
    echo "Injecting CLI version."
    echo "version = \"${TAG_NAME}\"" > ${BUILDDIR}/../dcos/__init__.py
    echo "version = \"${TAG_NAME}\"" > ${BUILDDIR}/dcoscli/__init__.py
fi

echo "Building binary..."
${BUILDDIR}/${VENV}/${BIN}/pyinstaller${EXE} \
    --workpath=${BUILDDIR}/${DIST}/build \
    --distpath=${BUILDDIR}/${DIST} \
    ${BASEDIR}/binary.spec
echo "Binary built."
