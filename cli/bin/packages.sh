#!/bin/bash -e

BASEDIR=`dirname $0`/..

echo "Building wheel..."

# configure wheel with production settings
ln -sf prod_settings.py "$BASEDIR/dcoscli/settings.py"
"$BASEDIR/env/bin/python" setup.py bdist_wheel
ln -sf dev_settings.py "$BASEDIR/dcoscli/settings.py"

echo "Building egg..."
"$BASEDIR/env/bin/python" setup.py sdist
