DC/OS Command Line Interface
============================
The DC/OS Command Line Interface (CLI) is a cross-platform command line utility
that provides a user-friendly yet powerful way to manage DC/OS clusters.

Installation and Usage
----------------------

If you're a **user** of DC/OS, please follow the `installation instructions`_.
Otherwise, follow the instructions below to set up your development environment.

Detailed help and usage information is available through the :code:`dcos help`
command and for specific subcommands through :code:`dcos <subcommand> --help`.

Additional documentation for the CLI and for the DC/OS in general is available
in the `DCOS docs`_.

Parsing CLI Output
------------------

The CLI outputs either whitespace delimited tables which can be processed by
all of your favourite Unix/Linux tools like sed, awk and grep, or text formatted
as JSON when using the :code:`--json` flag.

If using JSON, you can combine it with the powerful jq_ utility.
The example below installs every package available in the DC/OS repository::

    dcos package search --json | jq '.[0].packages[].name' | xargs -L 1 dcos package install --yes

Note: The CLI output supports support UTF-8 encoding for stdout and stderr.
Please follow your platform's instructions on how to do that.

Development Dependencies
------------------------

#. git_ must be installed to download the source code for the DC/OS CLI.

#. python_ version 3.5.x must be installed.

#. If :code:`make env` fails you may be missing required dependencies for
   cryptography. See here_ for more information or use our dockerfile that
   builds with all necessary dependencies.

#. virtualenv_ must be installed and on the system path in order to install
   legacy subcommands. New subcommands are packaged as platform specific
   executable or platform specific Zip archives.

#. win_bash_ must be installed if you are running this in Windows
   in order to run setup scripts from the Makefiles.

Setup
-----

#. Make sure you meet requirements for installing packages_
#. Clone git repo for the dcos cli::

    git clone git@github.com:dcos/dcos-cli.git

#. Change directory to the repo directory::

    cd dcos-cli

#. Create a python virtual env for the dcos project::

    make env

#. Create a virtualenv for the dcoscli project::

    cd cli
    make env

Configure Environment and Run
-----------------------------

#. From the :code:`cli` directory, :code:`source` the virtualenv activation
   script to add the :code:`dcos` command line interface to your :code:`PATH`::

    source env/bin/activate

#. Configure the CLI, changing the values below as appropriate for your local
   installation of DC/OS::

    dcos cluster setup http://dcos-ea-1234.us-west-2.elb.amazonaws.com

#. Get started by calling the DC/OS CLI help::

    dcos help

Running Tests
-------------

Setup
#####

Before you can run the DC/OS CLI integration tests, you need to get a cluster
up and running to test against. Currently, the test suite only supports testing
against Enterprise DC/OS.

Given these constraints, the easiest way to launch a cluster with these
capabilities is to use `dcos-launch`_ with the configuration listed below::

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

Where :code:`CLI_TEST_DEPLOYMENT_NAME` is a custom name set by the user,
:code:`CLI_TEST_INSTALLER_URL` is the URL of a
:code:`dcos_generate_config.ee.sh` script for the desired version of DC/OS to
test against, :code:`CLI_TEST_SSH_KEY_NAME` is the name of an AWS key to
install on the machines deployed by the installer, and
:code:`CLI_TEST_SSH_KEY_PATH` is a local path to the key named by
:code:`CLI_TEST_SSH_KEY_NAME`.

Unfortunately, the URL to download :code:`dcos_generate_config.ee.sh` scripts
for Enterprise DC/OS is not publicly available. For Mesosphere employees the
URL to the latest master build of Enterprise DC/OS can be found here::

    https://mesosphere.onelogin.com/notes/45791

For everyone else, you can still run the integration test suite against a
non-enterprise cluster (i.e. Community DC/OS), but please be aware that running
the full test suite *will* fail. See the section below on `Running`_ to see
how to limit the set of tests run by the integration test suite.

The URL to the latest master build of Community DC/OS is::

    https://downloads.dcos.io/dcos/testing/master/dcos_generate_config.sh

Initialization
##############

Once you have your cluster up and running you need to modify your environment
in order to run the tests. A simple script you can use to modify your
environment can be seen below.

*NOTE*: Make sure you run this script from your **top-level**
:code:`dcos-cli` directory (i.e. **not** inside :code:`dcos-cli/cli`).

*NOTE*: You will need to customize the first few lines in the script
appropriate for your setup. A description of the variables you need to modify
can be found below the script

*NOTE*: The script will modify your **global** :code:`/etc/hosts` file. This
is necessary because we rely on a statically named host to run our
integration tests against. In the future we hope to remove this limitation::

    # You must set these variables yourself.
    export CLI_TEST_DCOS_URL=<cluster-ip-or-url>
    export CLI_TEST_SSH_KEY_PATH=<path-to-ssh-key>
    export CLI_TEST_SSH_USER=<ssh-user-name>

    # With the variables set above, run the script below verbatim
    export DCOS_DIR=$(mktemp -d)
    export CLI_TEST_MASTER_PROXY=true

    deactivate > /dev/null 2>&1 || true
    cd cli
    make clean env
    source env/bin/activate
    dcos cluster setup ${CLI_TEST_DCOS_URL} \
        --insecure \
        --username=bootstrapuser \
        --password=deleteme
    dcos config set core.reporting false
    dcos config set core.timeout 5
    deactivate
    cd -

**CLI_TEST_DCOS_URL**: Holds the URL or IP address of the cluster you
are testing against. If you used :code:`dcos-launch` to launch the cluster,
you can get the IP of the cluster by running :code:`dcos-launch describe`.

**CLI_TEST_SSH_KEY_PATH**: Points to a private key file used to ssh into
nodes on your cluster. If you used :code:`dcos-launch` to launch the cluster,
then this should point to the same file used in your :code:`dcos-launch`
config. This is used by the :code:`node` integration tests.

**CLI_TEST_SSH_USER**: Holds the username used to ssh into nodes on your
cluster. If you used :code:`dcos-launch` with the configuration listed above
to launch your cluster, then you *must* set this to `centos`. This is used
by the :code:`node` integration tests.

Running
#######

Now that your environment is set up appropriately, we can start running the
tests. We have tests both in the :code:`dcos` package (root directory)
and in the :code:`dcoscli` package (:code:`cli` directory).

When running the tests, change your current directory to one of those two
locations and follow the instructions below.

*NOTE*: You **must** have your virtualenv *deactivated* in order to run the
tests via the commands below. This is very important and often a point of
much confusion.

If you want to run the full test suite simply run::

    make test

If you want to run only unit tests that match a specific pattern run::

    env/bin/tox -e py35-unit /<test-file>.py -- -k <test-pattern>

If you want to run only integration tests that match a specific pattern run::

    env/bin/tox -e py35-integration /<test-file>.py -- -k <test-pattern>

Other Useful Commands
#####################

#. List all of the supported test environments::

    env/bin/tox --listenvs

#. Run a specific set of tests::

    env/bin/tox -e <testenv>

#. Run a specific unit test module::

    env/bin/tox -e py35-unit /<test-file>.py

#. Run a specific integration test module::

    env/bin/tox -e py35-integration /<test-file>.py

Releasing
#########

Releasing a new version of the DC/OS CLI is only possible through an
`automated TeamCity build`_ which is triggered automatically when a new tag is
added.

The tag is used as the version number and must adhere to the conventional
`PEP-440 version scheme`_.

The automated build starts up three jobs to build the platform dependent executables
(in Windows, OS X, and Linux).

The executables are pushed to s3 and available at https://downloads.dcos.io/binaries/cli/<platform>/x86-64/<tag>/dcos.
The links to each of the platform executables and the release notes are published at: https://github.com/dcos/dcos-cli/releases/tag/<tag>

The automated build also publishes two packages to PyPI using the `publish_to_pypi.sh script`_:

#. dcos_

#. dcoscli_

These packages are available to be installed by the DC/OS CLI installation script in the `mesosphere/install-scripts`_ repository.

.. _automated TeamCity build: https://teamcity.mesosphere.io/viewType.html?buildTypeId=DcosIo_DcosCli_Release
.. _dcos: https://pypi.python.org/pypi/dcos
.. _dcos configuration parameters: https://dcos.io/docs/latest/installing/custom/configuration/configuration-parameters/
.. _dcoscli: https://pypi.python.org/pypi/dcoscli
.. _dcos-launch: https://github.com/dcos/dcos-launch
.. _jq: http://stedolan.github.io/jq/
.. _git: http://git-scm.com
.. _installation instructions: https://dcos.io/docs/latest/cli/install/
.. _DCOS docs: https://dcos.io/docs/
.. _mesosphere/install-scripts: https://github.com/mesosphere/install-scripts
.. _packages: https://packaging.python.org/en/latest/installing.html#installing-requirements
.. _PEP-440 version scheme: https://www.python.org/dev/peps/pep-0440/
.. _publish_to_pypi.sh script: https://github.com/mesosphere/dcos-cli/blob/master/bin/publish_to_pypi.sh
.. _virtualenv: https://virtualenv.pypa.io/en/latest/
.. _win_bash: https://sourceforge.net/projects/win-bash/files/shell-complete/latest
.. _python: https://www.python.org/
.. _here: https://cryptography.io/en/latest/installation/
