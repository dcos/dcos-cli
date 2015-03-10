DCOS Command Line Interface
===========================
The DCOS Command Line Interface (CLI) is a command line utility supporting several commands to
provide an user friendly yet powerful way to manage DCOS installations.

Dependencies
------------

#. git_ must be installed and on the system path in order to fetch
   packages from :code:`git` sources.

Setup
-----

#. Make sure you meet requirements for installing packages_
#. Clone git repo for the dcos cli::

    git clone git@github.com:mesosphere/dcos-cli.git

#. Change directory to the repo directory::

    cd dcos-cli

#. Make sure that you have virtualenv installed. If not type::

    sudo pip install virtualenv

#. Create a virtualenv for the dcos cli project::

    make env

Configure Environment and Run
-----------------------------

#. :code:`source` the setup file to add the :code:`dcos` command line interface to your
   :code:`PATH` and create an empty configuration file::

    source env/bin/env-setup

#. Configure Marathon, changing the values below as appropriate for your local installation::

    dcos config set marathon.host localhost
    dcos config set marathon.port 8080

#. Get started by calling the DCOS CLI help::

    dcos help

Running Tests:
--------------

Setup
#####

Tox, our test runner, tests against both Python 2.7 and Python 3.4 environments.

If you're using OS X, be sure to use the officially distributed Python 3.4 installer_ since the
Homebrew version is missing a necessary library.


Running
#######

Tox will run unit and integration tests in both Python environments using a temporarily created
virtualenv.

You should ensure :code:`DCOS_CONFIG` is set and that the config file points to the Marathon
instance you want to use for integration tests. If you're happy to use the default test
configuration which assumes there is a Marathon instance running on localhost, set
:code:`DCOS_CONFIG` as follows::

    export DCOS_CONFIG=$(pwd)/tests/data/Dcos.toml

There are two ways to run tests, you can either use the virtualenv created by :code:`make env`
above::

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

.. _packages: https://packaging.python.org/en/latest/installing.html#installing-requirements
.. _git: http://git-scm.com
.. _installer: https://www.python.org/downloads/
