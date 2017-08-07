#!/bin/bash -x
set -o errexit -o pipefail

# move the dcos package
cd /dcos-cli

# copy generated pypirc configuration to correct location
cat <<EOF > ~/.pypirc
[distutils]
index-servers =
    pypi

[pypi]
repository: https://pypi.python.org/pypi
username:$PYPI_USERNAME
password:$PYPI_PASSWORD
EOF

# replace SNAPSHOT with tagged version
sed -i "s/version = 'SNAPSHOT'/version = '$TAG_VERSION'/g" dcos/__init__.py

make clean env
source env/bin/activate
env/bin/python setup.py bdist_wheel upload
echo "Wheel should now be online at: https://pypi.python.org/pypi/dcos"
deactivate
