#!/bin/bash

CURRDIR=$(dirname "${0}")
source ${CURRDIR}/common.sh

rm -rf ${BUILDDIR}/${DIST} \
       ${BUILDDIR}/${DIST_DOCKER}
echo "Deleted distribution artifacts."
