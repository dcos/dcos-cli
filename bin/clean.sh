#!/bin/bash -e

set -o errexit -o nounset -o pipefail

BASEDIR=`dirname $0`/..

rm -rf $BASEDIR/.tox $BASEDIR/env $BASEDIR/dist
echo "Deleted virtualenv and test artifacts."

