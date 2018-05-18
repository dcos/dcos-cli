# DC/OS Command Line Interface

The DC/OS Command Line Interface (CLI) is a cross-platform command line
utility that provides a user-friendly yet powerful way to manage DC/OS
clusters.

## Installation and usage

If you're a **user** of DC/OS, please follow the [installation
instructions](https://dcos.io/docs/latest/cli/install/). Otherwise,
follow the instructions below to set up your development environment.

Detailed help and usage information is available through the dcos help
command and for specific subcommands through `dcos <subcommand> --help`.

Additional documentation for the CLI and for the DC/OS in general is
available in the [DC/OS docs](https://dcos.io/docs/).

## Parsing CLI output

The CLI outputs either whitespace delimited tables which can be
processed by all of your favourite Unix/Linux tools like sed, awk and
grep, or text formatted as JSON when using the `--json` flag.

If using JSON, you can combine it with the powerful
[jq](http://stedolan.github.io/jq/) utility. The example below installs
every package available in the DC/OS repository:

    dcos package search --json | jq '.[0].packages[].name' | xargs -L 1 dcos package install --yes

Note: The CLI output supports UTF-8 encoding for stdout and stderr.
Please follow your platform's instructions on how to do that.

## Development dependencies

1.  [git](http://git-scm.com) must be installed to download the source
    code for the DC/OS CLI.
2.  [python](https://www.python.org/) version 3.5.x must be installed.
3.  If `make env` fails you may be missing required dependencies for
    cryptography. See
    [here](https://cryptography.io/en/latest/installation/) for more
    information or use our dockerfile that builds with all necessary
    dependencies.
4.  [virtualenv](https://virtualenv.pypa.io/en/latest/) must be
    installed and on the system path in order to install legacy
    subcommands. New subcommands are packaged as platform specific
    executable or platform specific Zip archives.
5.  [win-bash](https://sourceforge.net/projects/win-bash/files/shell-complete/latest)
    must be installed if you are running this in Windows in order to run
    setup scripts from the Makefiles.

## Basic setup

1.  Make sure you meet requirements for installing
    [packages](https://packaging.python.org/en/latest/installing.html#installing-requirements)
2.  Clone git repo for the dcos cli:

        git clone git@github.com:dcos/dcos-cli.git

3.  Change directory to the repo directory:

        cd dcos-cli

###  Setup virtualenv for the dcos project

        cd python/lib/dcos
        make env

###  Setup virtualenv for the dcoscli project

        cd python/lib/dcoscli
        make env

## Using the DC/OS CLI

1.  From the dcoscli directory, source the virtualenv activation script
    to add the dcos command line interface to your PATH:

        source env/bin/activate

2.  Configure the CLI, changing the values below as appropriate for your
    local installation of DC/OS:

        dcos cluster setup http://dcos-ea-1234.us-west-2.elb.amazonaws.com

3.  Get started by calling the DC/OS CLI help:

        dcos help

## Running tests

### Setup

Before you can run the DC/OS CLI integration tests, you need to get a
cluster up and running to test against. Currently, the test suite only
supports testing against Enterprise DC/OS.

Given these constraints, the easiest way to launch a cluster with these
capabilities is to use
[dcos-launch](https://github.com/dcos/dcos-launch) with the
configuration listed below:

    launch_config_version: 1
    deployment_name: ${CLI_TEST_DEPLOYMENT_NAME}
    installer_url: ${CLI_TEST_INSTALLER_URL}
    platform: aws
    provider: onprem
    aws_region: us-west-2
    aws_key_name: ${CLI_TEST_SSH_KEY_NAME}
    ssh_private_key_filename: ${CLI_TEST_SSH_KEY_PATH}
    os_name: cent-os-7
    instance_type: m4.large
    num_masters: 1
    num_private_agents: 1
    num_public_agents: 1
    dcos_config:
        cluster_name: DC/OS CLI Integration Tests
        resolvers:
            - 10.10.0.2
        dns_search: us-west-2.compute.internal
        master_discovery: static

Where `CLI_TEST_DEPLOYMENT_NAME` is a custom name set by the user,
`CLI_TEST_INSTALLER_URL` is the URL of a dcos_generate_config.ee.sh
script for the desired version of DC/OS to test against,
`CLI_TEST_SSH_KEY_NAME` is the name of an AWS key to install on the
machines deployed by the installer, and `CLI_TEST_SSH_KEY_PATH` is a
local path to the key named by `CLI_TEST_SSH_KEY_NAME`.

Unfortunately, the URL to download `dcos_generate_config.ee.sh` scripts
for Enterprise DC/OS is not publicly available. For Mesosphere employees
the URL to the latest master build of Enterprise DC/OS can be found
here:

    https://mesosphere.onelogin.com/notes/45791

For everyone else, you can still run the integration test suite against
a non-enterprise cluster (i.e. Community DC/OS), but please be aware
that running the full test suite *will* fail. See the section below on
*Running* to see how to limit the set of tests run by the integration
test suite.

The URL to the latest master build of Community DC/OS is:

    https://downloads.dcos.io/dcos/testing/master/dcos_generate_config.sh

### Initialization

Once you have your cluster up and running you need to modify your
environment in order to run the tests. A simple script you can use to
modify your environment can be seen below.

*NOTE*: Make sure you run this script from your Python dcos-cli directory.

*NOTE*: You will need to customize the first few lines in the script
appropriate for your setup. A description of the variables you need to
modify can be found below the script

**CLI_TEST_DCOS_URL**: Holds the URL or IP address of the cluster you
are testing against. If you used `dcos-launch` to launch the cluster, you
can get the IP of the cluster by running `dcos-launch describe`.

**CLI_TEST_SSH_KEY_PATH**: Points to a private key file used to ssh
into nodes on your cluster. If you used `dcos-launch` to launch the
cluster, then this should point to the same file used in your
`dcos-launch` config. This is used by the node integration tests.

**CLI_TEST_SSH_USER**: Holds the username used to ssh into nodes on
your cluster. If you used `dcos-launch` with the configuration listed
above to launch your cluster, then you *must* set this to centos. This
is used by the node integration tests.

### Running

Now that your environment is set up appropriately, we can start running
the tests. We have tests both in the `dcos` package (`python/lib/dcos`) and
in the `dcoscli` package (`python/lib/dcoscli`).

When running the tests, change your current directory to one of those
two locations and follow the instructions below.

*NOTE*: You **must** have your virtualenv *deactivated* in order to run
the tests via the commands below. This is very important and often a
point of much confusion.

If you want to run the full test suite simply run:

    make test

If you want to run only unit tests that match a specific pattern run:

    env/bin/tox -e py35-unit /<test-file>.py -- -k <test-pattern>

If you want to run only integration tests that match a specific pattern
run:

    env/bin/tox -e py35-integration /<test-file>.py -- -k <test-pattern>

### Other Useful Commands

1.  List all of the supported test environments:

        env/bin/tox --listenvs

2.  Run a specific set of tests:

        env/bin/tox -e <testenv>

3.  Run a specific unit test module:

        env/bin/tox -e py35-unit /<test-file>.py

4.  Run a specific integration test module:

        env/bin/tox -e py35-integration /<test-file>.py

## Releasing

Releasing a new version of the DC/OS CLI is only possible through an
[automated TeamCity
build](https://teamcity.mesosphere.io/viewType.html?buildTypeId=DcosIo_DcosCli_Release)
which is triggered automatically when a new tag is added.

The tag is used as the version number and must adhere to the
conventional [PEP-440 version
scheme](https://www.python.org/dev/peps/pep-0440/).

The automated build starts up three jobs to build the platform dependent
executables (for Windows, macOS, and Linux).

The executables are pushed to s3 and available at
<https://downloads.dcos.io/binaries/cli/>\<platform\>/x86-64/\<tag\>/dcos.

## Contributing

Contributions are always welcome! Please refer to our [contributing guidelines](https://github.com/dcos/dcos-cli/blob/master/CONTRIBUTING.md) and [style guide](https://github.com/dcos/dcos-cli/blob/master/STYLEGUIDE.md) first.
