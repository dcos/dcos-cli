#!/bin/bash

CURRDIR=$(dirname "${0}")
source ${CURRDIR}/common.sh

rm -rf ${BUILDDIR}/${VENV} \
       ${BUILDDIR}/${VENV_DOCKER} \
       ${BUILDDIR}/${TOX} \
       ${BUILDDIR}/${TOX_DOCKER} \
       ${BASEDIR}/build \
       ${BASEDIR}/*.egg-info \
       ${BASEDIR}/.coverage \
       ${BASEDIR}/.cache
echo "Deleted virtualenv and test artifacts."
