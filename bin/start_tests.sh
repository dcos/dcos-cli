#!/bin/bash -x

# move the dcos package
cd dcos-cli

make clean env
source env/bin/activate
make || exit $?
deactivate

# Move down to the dcoscli package
cd cli

cp tests/data/dcos.toml $DCOS_CONFIG
echo "$VBOX_IP dcos.snakeoil.mesosphere.com" | sudo tee -a /etc/hosts > /dev/null

make clean env
source env/bin/activate
make || exit $?
deactivate
