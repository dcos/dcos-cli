#!/bin/bash

CURRDIR=$(dirname "${0}")
source ${CURRDIR}/common.sh

echo "Building documentation..."
${BUILDDIR}/${VENV}/${BIN}/sphinx-build${EXE} -W -b html pydoc pydoc/_build
echo "Documentation built."
