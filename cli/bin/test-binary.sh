#!/bin/bash -e

BASEDIR=`dirname $0`/..

cd $BASEDIR

PATH=$(pwd)/dist:$PATH
if [ -f "$BASEDIR/env/bin/activate" ]; then
        cp tests/data/dcos.toml $DCOS_CONFIG
        source $BASEDIR/env/bin/activate
else
        export DCOS_CONFIG=tests/data/dcos.toml
        $BASEDIR/env/Scripts/activate
fi
py.test tests/integrations
deactivate
