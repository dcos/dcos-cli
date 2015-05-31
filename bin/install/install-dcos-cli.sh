#!/bin/bash

set -o errexit -o pipefail

usage()
{ # Show usage information.
  echo "$(basename "$(test -L "$0" && readlink "$0" || echo "$0")") <installation-path> <dcos-url>"
}

if [ "$#" -lt 2 ]; then
  usage;
  exit 1;
fi

ARGS=( "$@" );

VENV="virtualenv"
VIRTUAL_ENV_PATH=$(python -c "import os; print(os.path.realpath('"${ARGS[0]}"'))")
DCOS_URL=${ARGS[1]}

IS_VENV=$(which ${VENV})
if [[ -z "${IS_VENV}" ]]; then
    echo "Cannot find virtualenv. Aborting."
    exit 1
fi

VIRTUALENV_VERSION=$(${VENV} --version)
VERSION_REGEX="s#[^0-9]*\([0-9]*\)[.]\([0-9]*\)[.]\([0-9]*\)\([0-9A-Za-z-]*\)#\1#"

eval MAJOR=`echo $VIRTUALENV_VERSION | sed -e $VERSION_REGEX`
if [ $MAJOR -lt 12 ]; then
    # On some (most?) Linux distro, venv for 2.7 is an ancient 1.11.6
    # Let's try and see if we can find virtualenv-3.4 and use that one instead
    VENV=$(which virtualvenv-3.4)
    if [[ -z ${VENV} ]]; then
        echo "Virtualenv version must be 12 or greater."
        echo "You can upgrade by running: sudo pip install --upgrade virtualenv"
        exit 1
    fi
fi

echo "Installing DCOS CLI from PyPI...";
echo "";

# Let's first setup a virtualenv: we are assuming that the path is absolute
mkdir -p "$VIRTUAL_ENV_PATH"
${VENV} "$VIRTUAL_ENV_PATH"

# Install the DCOS CLI package, using version if set
if [ -z "$DCOS_CLI_VERSION" ]; then
    "$VIRTUAL_ENV_PATH/bin/pip" install --quiet "dcoscli"
else
    "$VIRTUAL_ENV_PATH/bin/pip" install --quiet "dcoscli==$DCOS_CLI_VERSION"
fi

ENV_SETUP="$VIRTUAL_ENV_PATH/bin/env-setup"
source "$ENV_SETUP"
dcos config set core.reporting true
dcos config set core.dcos_url $DCOS_URL
dcos config set package.cache ~/.dcos/cache
dcos config set package.sources '["https://github.com/mesosphere/universe/archive/master.zip"]'
dcos package update

echo "Finished installing and configuring DCOS CLI."
echo "Run the line below to set up the DCOS environment for the current shell:"
echo "source $ENV_SETUP"
echo "Once this is done, run 'dcos help' to get started."
