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
if [[ ${MAJOR} -lt 12 ]]; then
    # TODO(marco): some unexplained behavior in bash makes this script abort
    # just after the call the $(which ... ) below; placing these error messages here, so that the
    # outcome is less baffling for the user; they should actually go into the `if`
    echo "Virtualenv version must be 12 or greater."
    echo "You can upgrade by running: sudo pip install --upgrade virtualenv"
    echo "Trying to find virtualenv-3.4 in your system..."

    # On some (most?) Linux distro, venv for 2.7 is an ancient 1.11.6
    # Let's try and see if we can find virtualenv-3.4 and use that one instead
    # TODO(marco): this line causes the script to mysteriously abort if virtualenv-3.4 is
    # missing; works just fine if it's there.
    VENV=$(which virtualenv-3.4)
    if [[ ! -x ${VENV} ]]; then
        echo "We could not find a suitable version of virtualenv, aborting."
        exit 1
    fi
    echo "Using virtualenv: ${VENV}"
fi

# Let's first setup a virtualenv: we are assuming that the path is absolute
echo "Creating a virtual environment in ${VIRTUAL_ENV_PATH}"
mkdir -p "$VIRTUAL_ENV_PATH"
${VENV} "$VIRTUAL_ENV_PATH"
if [[ $? != 0 ]]; then
    echo "Could not create a virtualenv, aborting."
    exit 1
fi

echo "Installing DCOS CLI from PyPI...";
echo "";

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
dcos config set package.sources '["https://github.com/mesosphere/universe/archive/version-1.x.zip"]'
dcos package update

echo 'Finished installing and configuring DCOS CLI.'
echo ''
echo 'Run this command to set up your environment and to get started:'
echo "source $ENV_SETUP && dcos help"
