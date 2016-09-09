DC/OS Command Line Interface
===========================
The DC/OS Command Line Interface (CLI) is a cross-platform command line utility
that provides a user-friendly yet powerful way to manage DC/OS clusters.

Installation and Usage
----------------------

If you're a **user** of DC/OS, please follow the `installation instructions`_.
Otherwise, follow the instructions below to set up your development environment.

Detailed help and usage information is available through the :code:`dcos help`
command and for specific subcommands through :code:`dcos <subcommand> --help`.

Additional documentation for the CLI and for the DC/OS in general is available
in the `Mesosphere docs`_.

Parsing CLI Output
------------------

The CLI outputs either whitespace delimited tables which can be processed by
all of your favourite Unix/Linux tools like sed, awk and grep, or text formatted
as JSON when using the :code:`--json` flag.

If using JSON, you can combine it with the powerful jq_ utility.
The example below installs every package available in the DC/OS repository::

    dcos package search --json | jq '.[0].packages[].name' | xargs -L 1 dcos package install --yes

Developement Dependencies
-------------------------

#. git_ must be installed to download the source code for the DC/OS CLI.

#. python_ version 3.4.x must be installed.

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

#. :code:`source` the setup file to add the :code:`dcos` command line
   interface to your :code:`PATH` and create an empty configuration file::

    source bin/env-setup-dev

#. Configure the CLI, changing the values below as appropriate for your local
   installation of DC/OS::

    dcos config set core.dcos_url http://dcos-ea-1234.us-west-2.elb.amazonaws.com

#. Get started by calling the DC/OS CLI help::

    dcos help

Running Tests
--------------

Setup
#####

Tox, our test runner, tests against Python 3.4. We have a set of tests in
the :code:`dcos` package (root directory) and in the :code:`dcoscli` package
(:code:`cli` directory). When running the tests describe below change
directory to one of those two and follow the instructions.


Initialization
#######

The `config` integration tests use static config files. To run these tests
make sure you set owner only permissions on these files:

:code:`chmod 600 cli/tests/data/dcos.toml`

:code:`chmod 600 cli/tests/config/parse_error.toml`

The :code:`node` integration tests use :code:`CLI_TEST_SSH_KEY_PATH` for ssh
credentials to your cluster.

The :code:`ssl` integration tests resolve :code:`dcos.snakeoil.mesosphere.com`
to test SSL certs. To run this test suite be sure to add this resolution to your
:code:`/etc/hosts` file:

:code:`echo "dcos/cluster/url dcos.snakeoil.mesosphere.com" >> /etc/hosts`


Running
#######

Tox will run unit and integration tests in Python 3.4 using a temporarily
created virtualenv.

You can set :code:`DCOS_CONFIG` to a config file that points to a DC/OS
cluster you want to use for integration tests. This defaults to
:code:`~/.dcos/dcos.toml`

There are two ways to run tests, you can either use the virtualenv created by
:code:`make env` above::

    make test

Or, assuming you have tox installed (via :code:`sudo pip install tox`)::

    tox

Other Useful Commands
#####################

#. List all of the supported test environments::

    tox --listenvs

#. Run a specific set of tests::

    tox -e <testenv>

#. Run a specific integration test module::

    tox -e py34-integration /test_config.py


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
.. _dcoscli: https://pypi.python.org/pypi/dcoscli
.. _jq: http://stedolan.github.io/jq/
.. _git: http://git-scm.com
.. _installation instructions: https://dcos.io/docs/usage/cli/install/
.. _Mesosphere docs: https://docs.mesosphere.com
.. _mesosphere/install-scripts: https://github.com/mesosphere/install-scripts
.. _packages: https://packaging.python.org/en/latest/installing.html#installing-requirements
.. _PEP-440 version scheme: https://www.python.org/dev/peps/pep-0440/
.. _publish_to_pypi.sh script: https://github.com/mesosphere/dcos-cli/blob/master/bin/publish_to_pypi.sh
.. _virtualenv: https://virtualenv.pypa.io/en/latest/
.. _win_bash: https://sourceforge.net/projects/win-bash/files/shell-complete/latest
.. _python: https://www.python.org/
