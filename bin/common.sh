set -o errexit -o nounset
if [ "$(uname)" != "Windows_NT" ]; then
  set -o pipefail
fi

: ${PROMPT:="(dcos-cli) "}

: ${BUILDDIR:=$(pwd -P)}
: ${VENV:=env}
: ${DIST:=dist}
: ${TOX:=.tox}
: ${VENV_DOCKER:=env-docker}
: ${DIST_DOCKER:=dist-docker}
: ${TOX_DOCKER:=.tox-docker}

if [ "$(uname)" = "Windows_NT" ]; then
  BIN=Scripts
  EXE=.exe
  : ${PYTHON:=python${EXE}}
  : ${VIRTUALENV:=virtualenv${EXE}}
else
  BIN=bin
  EXE=
  : ${PYTHON:=python3${EXE}}
fi

BASEDIR=$( cd "$(dirname $(dirname "${0}"))" > /dev/null; pwd -P )
