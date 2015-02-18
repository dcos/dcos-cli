#!/bin/bash -e

BASEDIR=`dirname $0`/..

if [ ! -d "$BASEDIR/env" ]; then
    virtualenv -q $BASEDIR/env --prompt='(dcos-cli) '
    echo "Virtualenv created."
fi

cd $BASEDIR
source $BASEDIR/env/bin/activate
echo "Virtualenv activated."

if [ ! -f "$BASEDIR/env/updated" -o $BASEDIR/setup.py -nt $BASEDIR/env/updated ]; then
    pip install -e $BASEDIR
    touch $BASEDIR/env/updated
    echo "Requirements installed."
fi

pip install tox
echo "Tox installed."

pip install Sphinx
echo "Sphinx installed."
