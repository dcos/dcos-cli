#!/bin/bash -x

# move the dcos package
cd dcos-cli

make clean env
source env/bin/activate
make || exit $?
deactivate

# Move down to the dcoscli package
cd cli

make clean env
source env/bin/activate
make || exit $?
deactivate
