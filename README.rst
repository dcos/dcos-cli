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

Tox, our test runner, tests against Python 3.5. We have a set of tests in
the :code:`dcos` package (root directory) and in the :code:`dcoscli` package
(:code:`cli` directory). When running the tests described below, change
directory to one of those two and follow the instructions.


Initialization
##############

Before you can run the DC/OS CLI integration tests, you need to modify your
environment appropriately.

#. Create a temporary directory to hold your DC/OS configuration files for the
   duration of the tests::

    $ export DCOS_DIR=$(mktemp -d)

   *NOTE:* You *must* set the environment variable for :code:`DCOS_DIR` when
   creating this directory. The CLI relies on this variable to know where to
   look store its config data.

   *NOTE:* You don't have to create a new directory every time you run the tests,
   but make sure you clear out :code:`DCOS_DIR` each time you run the tests to
   avoid conflicts with previous runs.


#. Copy a static :code:`dcos.toml` configuration file from the source repo into this
   folder::

    $ cp cli/tests/data/dcos.toml ${DCOS_DIR}


#. Set the proper permissions on this file so that it can be used by the CLI::

    $ chmod 600 ${DCOS_DIR}/dcos.toml


#. Export the :code:`DCOS_CONFIG` environment variable so that the CLI knows to
   use this file for its default config::

    $ export DCOS_CONFIG=${DCOS_DIR}/dcos.toml


#. Set the :code:`CLI_TEST_SSH_KEY_PATH` to point at appropriate ssh credentials to
   your cluster. This is used by the :code:`node` integration tests::

    $ export CLI_TEST_SSH_KEY_PATH=<path-to-ssh-key>


#. Add the following resolution to your :code:`/etc/hosts` file. The :code:`ssl`
   integration tests resolve :code:`dcos.snakeoil.mesosphere.com` to test SSL certs::

    $ echo "<cluster-ip-or-url> dcos.snakeoil.mesosphere.com" >> /etc/hosts


#. Finally, once all of this is set up, you need to launch a DC/OS cluster with
   the appropriate capabilities (see below in the section on :code:`Running`) and
   manually log into it::

    $ dcos cluster setup <cluster-ip-or-url>

Running
#######

There are two ways to run tests, you can either use the virtualenv created by
:code:`make env` above::

    make test

Or, assuming you have tox installed (via :code:`sudo pip install tox`)::

    tox

Either way, tox will run unit and integration tests in Python 3.5 using a
temporarily created virtualenv.

*NOTE:* In order for all the integration tests to pass, your DC/OS cluster must
have the experimental packaging features enabled. In order to enable these
features the :code:`staged_package_storage_uri` and :code:`package_storage_uri`
configuration paramenters must be set at cluster setup.  See `dcos
configuration parameters`_ for more information.

The easiest way to launch a cluster with these capabilities is to use
`dcos-launch`_ with the configuration listed below::

    launch_config_version: 1
    deployment_name: ${DEPLOYMENT_NAME}
    template_url: ${TEMPLATE_URL}
    provider: aws
    aws_region: us-west-2
    template_parameters:
        KeyName: default
        AdminLocation: 0.0.0.0/0
        PublicSlaveInstanceCount: 1
        SlaveInstanceCount: 1


Where :code:`DEPLOYMENT_NAME` is a custom name set by the user, and
:code:`TEMPLATE_URL` is the URL of an appropriate EC2 cloud formation template
for running the integration tests. Unfortunately, the full integration test
suite can only be run against an Enterprise DC/OS cluster (which you need
special permissions to launch).

For Mesosphere employees the URL of this cloud formation template can be found
here::

    https://mesosphere.onelogin.com/notes/45791

For everyone else, you can still run the integration test suite against a non
EE cluster, but please be aware that some of the tests may fail.

Assuming you have :code:`tox` installed, you can avoid running the full test
suite by running a specific test (or any tests matching a specific pattern) by
executing::

    tox -e py35-integration /<test-file>.py -- -k <test-pattern>

Other Useful Commands
#####################

#. List all of the supported test environments::

    tox --listenvs

#. Run a specific set of tests::

    tox -e <testenv>

#. Run a specific integration test module::

    tox -e py35-integration /test_config.py


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
.. _dcos configuration parameters: https://dcos.io/docs/1.9/administration/installing/custom/configuration-parameters/
.. _dcoscli: https://pypi.python.org/pypi/dcoscli
.. _dcos-launch: https://github.com/dcos/dcos-launch
.. _jq: http://stedolan.github.io/jq/
.. _git: http://git-scm.com
.. _installation instructions: https://dcos.io/docs/1.10/cli/install
.. _DCOS docs: https://dcos.io/docs/
.. _mesosphere/install-scripts: https://github.com/mesosphere/install-scripts
.. _packages: https://packaging.python.org/en/latest/installing.html#installing-requirements
.. _PEP-440 version scheme: https://www.python.org/dev/peps/pep-0440/
.. _publish_to_pypi.sh script: https://github.com/mesosphere/dcos-cli/blob/master/bin/publish_to_pypi.sh
.. _virtualenv: https://virtualenv.pypa.io/en/latest/
.. _win_bash: https://sourceforge.net/projects/win-bash/files/shell-complete/latest
.. _python: https://www.python.org/
.. _here: https://cryptography.io/en/latest/installation/
