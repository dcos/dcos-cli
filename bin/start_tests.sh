#!/bin/bash -x

# move the dcos package
cd dcos-cli

make clean env
source env/bin/activate
make || exit $?
deactivate

# Move down to the dcoscli package
cd cli

# overwrite core.dcos_url in the dcos.toml
cp tests/data/dcos.toml ${DCOS_CONFIG}
sed -i "s,http://change.dcos.url,${CORE_DCOS_URL},g" ${DCOS_CONFIG}

make clean env
source env/bin/activate
make || exit $?
deactivate
