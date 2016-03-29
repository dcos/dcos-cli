#!/bin/bash -e

BASEDIR=`dirname $0`/..

cd $BASEDIR

PATH=$BASEDIR/../dist:$PATH
source env/bin/activate
cp tests/data/dcos.toml $DCOS_CONFIG
py.test tests/integrations
deactivate
