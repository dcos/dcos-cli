#!/bin/bash -e

BASEDIR=`dirname $0`/..

cd $BASEDIR

if [ -f "$BASEDIR/env/bin/activate" ]; then
        source $BASEDIR/env/bin/activate
else
        $BASEDIR/env/Scripts/activate
fi

pip install pyinstaller==3.1.1
pyinstaller $BASEDIR/binary/binary.spec

deactivate
