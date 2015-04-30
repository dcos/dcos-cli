#!/bin/bash -x
set -o errexit -o pipefail

# move the dcos package
cd /dcos-cli

# copy generated pypirc configuration to correct location
cp .pypirc ~/.pypirc

TAG_VERSION=`cat tag-version`

# replace SNAPSHOT with tagged version
sed -i "s/SNAPSHOT/$TAG_VERSION/g" dcos/__init__.py

make clean env
source env/bin/activate
env/bin/python setup.py bdist_wheel upload
echo "Wheel should now be online at: https://pypi.python.org/pypi/dcos"
deactivate

# Move down to the dcoscli package
cd cli

# replace SNAPSHOT with tagged version
sed -i "s/SNAPSHOT/$TAG_VERSION/g" dcoscli/__init__.py

make clean env
source env/bin/activate
env/bin/python setup.py bdist_wheel upload
echo "Wheel should now be online at: https://pypi.python.org/pypi/dcoscli"
deactivate
