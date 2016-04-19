#!/bin/bash

set -o errexit -o pipefail

usage()
{ # Show usage information.
  echo "$(basename "$(test -L "$0" && readlink "$0" || echo "$0")") <installation-path> <dcos-url> [--add-path yes/no]"
}

post_install_message()
{
    echo 'Finished installing and configuring DCOS CLI.'
    echo ''
    echo 'Run this command to set up your environment and to get started:'
    echo "source $1 && dcos help"
}

RC_NAME=""

write_to_profile()
{
    echo "" >> ~/"$2";
    echo "# path to the DCOS CLI binary" >> ~/"$2";
    echo "if [[ \"\$PATH\" != *\"$1\"* ]];" >> ~/"$2";
    echo "  then export PATH=\$PATH:$1;" >> ~/"$2";
    echo "fi" >> ~/"$2";
}

add_dcos_path_to_profile()
{
    UNAME=`uname`
    case "$UNAME" in
        Linux ) RC_NAME=".bashrc";;
        Darwin ) RC_NAME=".bash_profile";;
        CYGWIN* ) RC_NAME=".bashrc";;
        MINGW* ) RC_NAME=".profile";;
        * ) RC_NAME=".bashrc";;
    esac
    write_to_profile "$1" "$RC_NAME"
}

prompt_add_dcos_path_to_profile()
{
    while true; do
        echo ""
        read -p "Modify your bash profile to add DCOS to your PATH? [yes/no] " ANSWER
        echo ""
        case "$ANSWER" in
            [Yy]* ) add_dcos_path_to_profile "$1"; break;;
            [Nn]* ) break;;
            * ) echo "Please answer yes or no.";;
        esac
    done
}

check_pip_version()
{
    PIP_INFO=$(pip -V);
    REGEX="([0-9]+)\.([0-9]+)";
    [[ $PIP_INFO =~ $REGEX ]];
    MAJOR_PIP_VERSION="${BASH_REMATCH[1]}";
    MINOR_PIP_VERSION="${BASH_REMATCH[2]}";
    if [ "$MAJOR_PIP_VERSION" -lt 1 ] || ([ "$MAJOR_PIP_VERSION" -eq 1 ] && [ "$MINOR_PIP_VERSION" -le 4 ]);
        then echo "Pip version must be greater than 1.4. Aborting.";
        exit 1;
    fi
}

check_dcoscli_version()
{
    if [ ! -z "$DCOS_CLI_VERSION" ]; then
        # result is the larger of the two versions
        COSMOS_VERSION="0.4.0"
        # convert the str to numbers, sort, and return the larger
        result=$(echo -e "$COSMOS_VERSION\n$DCOS_CLI_VERSION" | sed '/^$/d' | sort -nr | head -1)
        # if DCOS_CLI_VERSION < COSMOS_VERSION, exit
        if [ "$result" != "$DCOS_CLI_VERSION" ]; then
                echo "Please use legacy installer for dcoscli versions <0.4.0. Aborting.";
                exit 1;
        fi
    fi
}

validate_dcos_url()
{
    curl -f -k -s ${DCOS_URL} 2>&1 >/dev/null
    echo $?
}

get_dcos_environment_version()
{
    VER=$(curl -f -k -s ${DCOS_URL}/dcos-metadata/dcos-version.json)
    if [ $? -eq 22 ]; then
        echo "1.1"
    else
        echo $VER | python -c 'import json,sys;obj=json.load(sys.stdin);print(obj.get("version", "1.0"))'
    fi
}

if [ "$#" -lt 2 ]; then
  usage;
  exit 1;
fi

check_pip_version;
check_dcoscli_version;

ARGS=( "$@" );

VIRTUAL_ENV_PATH=$(python -c "import os; print(os.path.realpath('"${ARGS[0]}"'))")
if [[ $VIRTUAL_ENV_PATH =~ \  ]];
	then echo "Spaces are not permitted in the installation path. Please try again with another path.";
    exit 1;
fi
DCOS_URL=${ARGS[1]}

hash curl 2>/dev/null || { echo >&2 "Cannot find curl. You may need to install it by following the documentation at https://dcos.io/docs/usage/cli/install/. Aborting."; exit 1; }

command -v virtualenv >/dev/null 2>&1 || { echo "Cannot find virtualenv. You may need to install it by following the documentation at https://dcos.io/docs/usage/cli/install/. Aborting."; exit 1; }

VIRTUALENV_VERSION=$(virtualenv --version)
VERSION_REGEX="s#[^0-9]*\([0-9]*\)[.]\([0-9]*\)[.]\([0-9]*\)\([0-9A-Za-z-]*\)#\1#"

eval MAJOR=`echo $VIRTUALENV_VERSION | sed -e $VERSION_REGEX`
if [ $MAJOR -lt 12 ];
	then echo "Virtualenv version must be 12 or greater. Aborting.";
	exit 1;
fi

echo "Installing DCOS CLI from PyPI...";
echo "";

if [ "$(validate_dcos_url)" -gt 0 ]; then
    echo "dcos-url is invalid. Please double check that the URL is formatted correctly and pointing at a valid cluster."
    exit 1
fi

DCOS_ENVIRONMENT_VERSION=$(get_dcos_environment_version)

compare_version()
{
    python -c "import distutils.version as v, sys; sys.exit(not (v.LooseVersion('"${DCOS_ENVIRONMENT_VERSION}"') < v.LooseVersion('"${1}"')))"
}

# Let's first setup a virtualenv: we are assuming that the path is absolute
mkdir -p "$VIRTUAL_ENV_PATH"
virtualenv "$VIRTUAL_ENV_PATH"


# Install the DCOS CLI package, using version if set
if [ -z "$DCOS_CLI_VERSION" ]; then
    if $(compare_version 1.6.1); then
        "$VIRTUAL_ENV_PATH/bin/pip" install --quiet "dcoscli<0.4.0"
    else
        "$VIRTUAL_ENV_PATH/bin/pip" install --quiet "dcoscli"
    fi
else
    "$VIRTUAL_ENV_PATH/bin/pip" install --quiet "dcoscli==$DCOS_CLI_VERSION"
fi

ENV_SETUP="$VIRTUAL_ENV_PATH/bin/env-setup"
source "$ENV_SETUP"
dcos config set core.reporting true
dcos config set core.dcos_url $DCOS_URL
dcos config set core.ssl_verify false
dcos config set core.timeout 5

ADD_PATH=""
while [ $# -gt 0 ]; do
    case "$1" in
            --add-path ) ADD_PATH="$2"; break;;
            * ) shift;;
    esac
done

case "$ADD_PATH" in
    [Yy]* ) add_dcos_path_to_profile "$VIRTUAL_ENV_PATH/bin";;
    [Nn]* ) ;;
    * ) prompt_add_dcos_path_to_profile "$VIRTUAL_ENV_PATH/bin";;
esac

post_install_message "$ENV_SETUP"
