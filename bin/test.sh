#!/bin/bash

CURRDIR=$(dirname "${0}")
source ${CURRDIR}/common.sh

echo "Running tests..."
TOXWORKDIR=${BUILDDIR}/${TOX} ${BUILDDIR}/${VENV}/${BIN}/tox${EXE}
echo "Tests completed."
