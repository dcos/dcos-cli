#!/bin/bash -e

BASEDIR=`dirname $0`/..
if [ -f "$BASEDIR/env/bin/python" ]; then

	PYTHON="$BASEDIR/env/bin/python"
else
	PYTHON="$BASEDIR/env/Scripts/python.exe"
fi

echo "Building wheel..."
"$PYTHON" setup.py bdist_wheel

echo "Building egg..."
"$PYTHON" setup.py sdist
