#!/bin/bash

CURRDIR=$(dirname "${0}")
source ${CURRDIR}/common.sh

echo "Building binary..."
${BUILDDIR}/${VENV}/${BIN}/pyinstaller${EXE} \
    --workpath=${BUILDDIR}/${DIST}/build \
    --distpath=${BUILDDIR}/${DIST} \
    ${BASEDIR}/binary.spec
echo "Binary built."
