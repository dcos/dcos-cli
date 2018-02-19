#!/bin/bash

CURRDIR=$(dirname "${0}")
source ${CURRDIR}/common.sh

export PATH="${BUILDDIR}/${DIST}:${PATH}"
source ${CURRDIR}/test.sh
