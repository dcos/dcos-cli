#!/bin/bash -e

set -o errexit -o nounset

BASEDIR=`dirname $0`/..

rm -rf $BASEDIR/.tox $BASEDIR/env $BASEDIR/dist $BASEDIR/build
find $BASEDIR -name '*.pyc' -delete || true
echo "Deleted virtualenv and test artifacts."

