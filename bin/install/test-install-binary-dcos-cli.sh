#!/usr/bin/env bash

# Installs the binary DC/OS CLI and verifies that it is at the location printed by the installer.
#
# Arguments (required):
#   dcos-url -- URL to DC/OS cluster (ex: http://m1.dcos/)
#
# Usage:
# $ test-install-binary.sh

set -o errexit -o nounset -o pipefail

if [[ -z "${1:-}" ]]; then
  echo >&2 "INVALID USAGE: DC/OS URL must be supplied as the first command argument."
  exit 2
fi

project_dir=$(cd "$(dirname "${BASH_SOURCE}")/../.." && pwd -P)
cd "${project_dir}"

EXE_PATH="$(bin/install/install-binary-dcos-cli.sh "${DCOS_URL}")"
echo "Install Path: ${EXE_PATH}"

if [[ -z "${EXE_PATH}" ]]; then
  echo >&2 "FAILED: Executable path not printed by install script."
  exit 1
fi

if [[ ! -e "${EXE_PATH}" ]]; then
  echo >&2 "FAILED: Executable not found."
  exit 1
fi

rm "${EXE_PATH}"
