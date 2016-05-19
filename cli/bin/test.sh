#!/bin/bash -e

BASEDIR=`dirname $0`/..

cd $BASEDIR
if [ -f "$BASEDIR/env/bin/activate" ]; then
	source $BASEDIR/env/bin/activate
else
	$BASEDIR/env/Scripts/activate
fi
echo "Virtualenv activated."

tox
