#!/bin/bash -e

BASEDIR=`dirname $0`/..

cd $BASEDIR
source $BASEDIR/env/bin/activate
echo "Virtualenv activated."

sphinx-build -W -b html pydoc pydoc/_build
