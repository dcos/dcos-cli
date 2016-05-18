#!/bin/bash -e

BASEDIR=`dirname $0`/..

cd $BASEDIR

PATH=$(pwd)/dist:$PATH
cp tests/data/dcos.toml $DCOS_CONFIG
if [ -f "$BASEDIR/env/bin/activate" ]; then
	source $BASEDIR/env/bin/activate
else
	$BASEDIR/env/Scripts/activate
fi
py.test tests/integrations
deactivate
