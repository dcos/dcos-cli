#!/usr/bin/env bash

# Installs the binary DC/OS CLI.
#
# Auto-detects the DC/OS version by asking an existing DC/OS cluster.
# Auto-detects the local operating system to download the right DC/OS CLI binary.
#
# Arguments (required):
#   dcos-url -- URL to DC/OS cluster (ex: http://m1.dcos/)
#
# Variables (optional):
#   DCOS_VERSION -- Version of DC/OS the CLI should be compatible with (default: query from dcos-url)
#   INSTALL_PATH -- Directory path to install into (default: platform dependent)
#
# Usage:
# $ install-binary-dcos-cli.sh <dcos-url>
# $ dcos --version
#
# Save executable location:
# $ EXE="$(install-binary-dcos-cli.sh <dcos-url> 2>/dev/null)"
# $ ${EXE} --version
#
# Specify DC/OS version (no cluster required):
# $ DCOS_VERSION=1.10.0 install-binary-dcos-cli.sh <dcos-url>
# $ dcos --version
#
# Remote Usage:
# $ curl https://downloads.dcos.io/dcos-cli/bin/install/install-binary-dcos-cli.sh | bash -s <dcos-url>
# $ dcos --version

set -o errexit -o nounset -o pipefail

# Show usage information.
function usage() {
  echo "$(basename "$(test -L "$0" && readlink "$0" || echo "$0")") <dcos-url>"
}

# Query the DC/OS API for the DC/OS version
function detect_dcos_version() {
  # Auto-detect version (unauthenticated)
  DCOS_VERSION_JSON="$(curl --insecure --fail --location --silent --show-error ${DCOS_URL%/}/dcos-metadata/dcos-version.json)"
  # Extract version from metadata
  # Warning: requires json to be pretty-printed with line breaks
  # Full json parsing would require a dependency like python or jq.
  DCOS_VERSION="$(echo "${DCOS_VERSION_JSON}" | grep 'version' | cut -d ':' -f 2 | cut -d '"' -f 2)"
  echo "${DCOS_VERSION}"
}

function create_temp_dir() {
  TMPDIR="${TMPDIR:-/tmp/}"
  echo "$(mktemp -d "${TMPDIR%/}/dcos-install-cli.XXXXXXXXXXXX")"
}

function download_cli() {
  DCOS_VERSION="${1}"
  DOWNLOAD_PATH="${2}"
  PLATFORM="$(detect_platform)"
  DCOS_MAJOR_VERSION="$(dcos_major_version "${DCOS_VERSION}")"
  EXE_NAME="$(detect_exe_name)"
  DCOS_CLI_URL="https://downloads.dcos.io/binaries/cli/${PLATFORM}/dcos-${DCOS_MAJOR_VERSION}/${EXE_NAME}"
  echo >&2 "Download URL: ${DCOS_CLI_URL}"
  echo >&2 "Download Path: ${DOWNLOAD_PATH}/${EXE_NAME}"
  echo >&2 "Downloading..."
  curl --fail --location --silent --show-error -o "${DOWNLOAD_PATH}/${EXE_NAME}" "${DCOS_CLI_URL}"
  echo "${DOWNLOAD_PATH}/${EXE_NAME}"
}

function install_cli() {
  DOWNLOAD_PATH="${1}"
  INSTALL_PATH="${2}"
  echo >&2 "Installing..."
  EXE_PATH="${INSTALL_PATH}/$(basename "${DOWNLOAD_PATH}")"
  chmod a+x "${DOWNLOAD_PATH}"
  # only use sudo if required
  if [[ -w "${INSTALL_PATH}" ]]; then
    mv "${DOWNLOAD_PATH}" "${EXE_PATH}"
  else
    sudo mv "${DOWNLOAD_PATH}" "${EXE_PATH}"
  fi
  echo "${EXE_PATH}"
}

function detect_cli_version() {
  dcos --version | grep dcoscli.version | cut -d '=' -f 2
}

function detect_platform() {
  case "${OSTYPE}" in
    darwin*)  PLATFORM='darwin/x86-64' ;;
    linux*)   PLATFORM='linux/x86-64' ;;
    msys*)    PLATFORM='windows/x86-64' ;;
    *)        echo >&2 "Unsupported operating system: ${OSTYPE}"; exit 1 ;;
  esac
  echo "${PLATFORM}"
}

function detect_install_path() {
  case "${OSTYPE}" in
    darwin*)  INSTALL_PATH='/usr/local/bin' ;;
    linux*)   INSTALL_PATH='/usr/local/bin' ;;
    msys*)    INSTALL_PATH="${HOME}/AppData/Local/Microsoft/WindowsApps" ;;
    *)        echo >&2 "Unsupported operating system: ${OSTYPE}"; exit 1 ;;
  esac
  echo "${INSTALL_PATH}"
}

function detect_exe_name() {
  case "${OSTYPE}" in
    darwin*)  EXE_NAME='dcos' ;;
    linux*)   EXE_NAME='dcos' ;;
    msys*)    EXE_NAME='dcos.exe' ;;
    *)        echo >&2 "Unsupported operating system: ${OSTYPE}"; exit 1 ;;
  esac
  echo "${EXE_NAME}"
}

# Convert from DC/OS version to "major" version used by CLI URL
function dcos_major_version() {
  DCOS_VERSION="${1}"
  echo "$(echo "${DCOS_VERSION}" | sed -e "s#[^0-9]*\([0-9][0-9]*[.][0-9][0-9]*\).*#\1#")"
}

if [[ "$#" -lt 1 ]]; then
  usage;
  exit 1;
fi

# DC/OS URL (required)
DCOS_URL="${1}"
echo >&2 "DC/OS URL: ${DCOS_URL}"

# DC/OS Version (optional)
if [[ -z "${DCOS_VERSION:-}" ]]; then
  # auto-detect version, if not provided
  DCOS_VERSION="$(detect_dcos_version)"
fi
echo >&2 "DC/OS Version: ${DCOS_VERSION}"

# Install Path (optional)
if [[ -z "${INSTALL_PATH:-}" ]]; then
  # auto-detect install path, if not provided
  INSTALL_PATH="$(detect_install_path)"
fi
echo >&2 "Install Path: ${INSTALL_PATH}"

# Use temp dir to download into before install, delete on script exit
DOWNLOAD_PATH="$(create_temp_dir)"
trap "rm -rf ${DOWNLOAD_PATH}" EXIT

EXE_PATH="$(download_cli "${DCOS_VERSION}" "${DOWNLOAD_PATH}")"
EXE_PATH="$(install_cli "${EXE_PATH}" "${INSTALL_PATH}")"

CLI_VERSION="$(detect_cli_version)"
echo >&2 "CLI Version: ${CLI_VERSION}"

# Print install path to STDOUT to enable script chaining
echo >&2 "Executable Path:"
echo "${EXE_PATH}"
