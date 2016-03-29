#!/bin/bash -e

BASEDIR=`dirname $0`/..

cd $BASEDIR

PATH=$(pwd)/dist:$PATH
cp tests/data/dcos.toml $DCOS_CONFIG
source env/bin/activate
py.test tests/integrations
deactivate
