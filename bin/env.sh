#!/bin/bash

CURRDIR=$(dirname "${0}")
source ${CURRDIR}/common.sh

if [ ! -d "${BUILDDIR}/${VENV}" ]; then
    # Check for required prerequisites.
    echo "Checking prerequisites..."
    if [ ! "$(command -v ${PYTHON})" ]; then
      echo "Cannot find python. Exiting..."
      exit 1
    fi

    PYTHON_MAJOR=$(${PYTHON} -c 'import sys; print(sys.version_info[0])')
    PYTHON_MINOR=$(${PYTHON} -c 'import sys; print(sys.version_info[1])')

    : "${DCOS_EXPERIMENTAL:=""}"
    if [ "${DCOS_EXPERIMENTAL}" = "" ]; then
      if [ "${PYTHON_MAJOR}" != "3" ] || [ "${PYTHON_MINOR}" != "5" ]; then
          echo "Cannot find supported python version 3.5. Exiting..."
          exit 1
      fi
    fi
    if [ "$(uname)" = "Windows_NT" ]; then
      if [ ! "$(command -v ${VIRTUALENV})" ]; then
          echo "Cannot find virtualenv. Exiting..."
      fi
    fi
    echo "Prerequisite checks passed."

    # Create the virtualenv.
    echo "Creating virtualenv..."
    if [ "$(uname)" = "Windows_NT" ]; then
      mkdir -p ${BUILDDIR}/${VENV}; cd ${BUILDDIR}/${VENV}
      ${VIRTUALENV} --python=$(which ${PYTHON}) --prompt="${PROMPT}" --no-site-packages ${BUILDDIR}/${VENV}
      ${VIRTUALENV} --relocatable ${BUILDDIR}/${VENV}
      cd -
    else
      ${PYTHON} -m venv ${BUILDDIR}/${VENV}
      sed -i'' -e "s#(${VENV}) #${PROMPT}#g" ${BUILDDIR}/${VENV}/${BIN}/activate
    fi
    echo "Virtualenv created: ${BUILDDIR}/${VENV}"

    # Install all requirements into the virtualenv.
    echo "Installing virtualenv requirements..."
    if [ "$(uname)" = "Windows_NT" ]; then
      ${PYTHON} -m pip install -U pip
    else
      ${BUILDDIR}/${VENV}/${BIN}/pip${EXE} install --upgrade pip
    fi
    ${BUILDDIR}/${VENV}/${BIN}/pip${EXE} install -r ${BASEDIR}/requirements.txt
    ${BUILDDIR}/${VENV}/${BIN}/pip${EXE} install -e ${BASEDIR}
    if [ "$(uname)" = "Windows_NT" ]; then
      ${VIRTUALENV} --relocatable ${BUILDDIR}/${VENV}
    fi
    echo "Virtualenv requirements installed."
else
    echo "Virtualenv already exists: '${BUILDDIR}/${VENV}'"
fi
