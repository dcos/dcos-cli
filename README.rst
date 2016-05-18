DCOS Command Line Interface
===========================
The DCOS Command Line Interface (CLI) is a cross-platform command line utility
that provides a user-friendly yet powerful way to manage DCOS installations.

Installation and Usage
----------------------

If you're a **user** of DCOS, please follow the `installation instructions`_.
Otherwise, follow the instructions below to set up your development environment.

Detailed help and usage information is available through the :code:`dcos help`
command and for specific subcommands through :code:`dcos <subcommand> --help`.

Additional documentation for the CLI and for the DCOS in general is available
in the `Mesosphere docs`_.

Parsing CLI Output
------------------

The CLI outputs either whitespace delimited tables which can be processed by
all of your favourite Unix/Linux tools like sed, awk and grep, or text formatted
as JSON when using the :code:`--json` flag.

If using JSON, you can combine it with the powerful jq_ utility.
The example below installs every package available in the DCOS repository::

    dcos package search --json | jq '.[0].packages[].name' | xargs -L 1 dcos package install --yes

Using the CLI without DCOS
--------------------------

You may optionally configure the DCOS CLI to work with open source Mesos and
Marathon_ by setting the following properties::
    dcos config set core.mesos_master_url http://<mesos-master-host>:5050
    dcos config set marathon.url http://<marathon-host>:8080

Note that the DCOS CLI has tight integration with DCOS and certain
functionality may not work as expected or at all when using it directly with
Mesos and Marathon.

Dependencies
------------

#. git_ must be installed and on the system path in order to fetch
   packages from :code:`git` sources.

#. virtualenv_ must be installed and on the system path in order to install
   subcommands.

#. win_bash_ must be installed if you are running this in Windows
   in order to run setup scripts from the Makefiles.

Setup
-----

#. Make sure you meet requirements for installing packages_
#. Clone git repo for the dcos cli::

    git clone git@github.com:mesosphere/dcos-cli.git

#. Change directory to the repo directory::

    cd dcos-cli

#. Make sure that you have virtualenv installed. If not type::

    sudo pip install virtualenv

#. Create a virtualenv and packages for the dcos project::

    make env
    make packages

#. Create a virtualenv for the dcoscli project::

    cd cli
    make env

Configure Environment and Run
-----------------------------

#. :code:`source` the setup file to add the :code:`dcos` command line
   interface to your :code:`PATH` and create an empty configuration file::

    source bin/env-setup-dev

#. Configure the CLI, changing the values below as appropriate for your local
   installation of DCOS::

    dcos config set core.dcos_url http://dcos-ea-1234.us-west-2.elb.amazonaws.com

#. Get started by calling the DCOS CLI help::

    dcos help

Running Tests
--------------

Setup
#####

Tox, our test runner, tests against both Python 2.7 and Python 3.4
environments.

Running
#######

Tox will run unit and integration tests in both Python environments using a
temporarily created virtualenv.

You can set :code:`DCOS_CONFIG` to a config file that points to a DCOS
cluster you want to use for integration tests.  This defaults to
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

    tox -e py27-integration /cli/test_config.py


Releasing
#########

Releasing a new version of the DCOS CLI is only possible through an `automated TeamCity build`_ which is triggered automatically when a new tag is added.

The tag is used as the version number and must adhere to the conventional `PEP-440 version scheme`_.

Once all tests pass successfully, the automated build publishes two packages to PyPI using the `publish_to_pypi.sh script`_:

#. dcos_

#. dcoscli_

These packages are now available to be installed by the DCOS CLI installation script in the `mesosphere/install-scripts`_ repository.


.. _automated TeamCity build: https://teamcity.mesosphere.io/viewType.html?buildTypeId=ClosedSource_DcosCli_PushToPyPI
.. _dcos: https://pypi.python.org/pypi/dcos
.. _dcoscli: https://pypi.python.org/pypi/dcoscli
.. _dcos-helloworld: https://github.com/mesosphere/dcos-helloworld
.. _jq: http://stedolan.github.io/jq/
.. _git: http://git-scm.com
.. _installation instructions: https://dcos.io/docs/usage/cli/install/
.. _Marathon: https://mesosphere.github.io/marathon/
.. _Mesosphere docs: https://docs.mesosphere.com
.. _mesosphere/install-scripts: https://github.com/mesosphere/install-scripts
.. _packages: https://packaging.python.org/en/latest/installing.html#installing-requirements
.. _PEP-440 version scheme: https://www.python.org/dev/peps/pep-0440/
.. _publish_to_pypi.sh script: https://github.com/mesosphere/dcos-cli/blob/master/bin/publish_to_pypi.sh
.. _setup: https://github.com/mesosphere/dcos-helloworld#setup
.. _virtualenv: https://virtualenv.pypa.io/en/latest/
.. _win-bash: https://sourceforge.net/projects/win-bash/files/shell-complete/latest
