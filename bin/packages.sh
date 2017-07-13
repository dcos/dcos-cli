#!/bin/bash

CURRDIR=$(dirname "${0}")
source ${CURRDIR}/common.sh

cd ${BASEDIR}

mkdir -p ${BUILDDIR}/${DIST}/build
rm -rf ${BUILDDIR}/${DIST}/build/packages

echo "Building wheel..."
${BUILDDIR}/${VENV}/${BIN}/python${EXE} setup.py bdist_wheel \
    --dist-dir=${BUILDDIR}/${DIST}

echo "Building egg..."
${BUILDDIR}/${VENV}/${BIN}/python${EXE} setup.py sdist \
    --dist-dir=${BUILDDIR}/${DIST}

mv build ${BUILDDIR}/${DIST}/build/packages
echo "Packages built."
