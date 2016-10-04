#!/bin/bash -e

BASEDIR=`dirname $0`/..

cd $BASEDIR

if [ -f "$BASEDIR/env/bin/activate" ]; then
        cp tests/data/dcos.toml $DCOS_CONFIG
        source $BASEDIR/env/bin/activate
else
        export DCOS_CONFIG=tests/data/dcos.toml
        $BASEDIR/env/Scripts/activate
fi

export PATH=$BASEDIR/dist:$PATH
py.test tests/integrations
deactivate
