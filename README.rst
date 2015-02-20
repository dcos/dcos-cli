DCOS Command Line Interface
===========================
The DCOS Command Line Interface (CLI) is a command line utility supporting several commands to
provide an user friendly yet powerful way to manage DCOS installations.

Dependencies
------------

#. git_ must be installed and on the system path in order to fetch
   packages from `git` sources.

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

Configure Development Environment
---------------------------------

#. Activate the virtualenv::

    source env/bin/activate

#. Export DCOS_PATH::

    export DCOS_PATH=$(pwd)/env

#. Export DCOS_CONFIG::

    export DCOS_CONFIG=$(pwd)/tests/data/Dcos.toml

Running POC
-----------

#. Get started by calling the DCOS CLI help::

    dcos help

Running Tests:
--------------

Setup
#####

Tox, our test runner, tests against both Python 2.7 and Python 3.4 environments.

If you're using OS X, be sure to install the officially distributed Python 3.4 installer_ since the Homebrew version is missing a necessary library.


Running
#######

Tox will run unit and integration tests in both Python environments using a temporarily created virtualenv. For integration tests to work, you need a Marathon instance running on localhost.

There are two ways to run tests, you can either use the virtualenv created by `make env` above::

    make test

Or, assuming you have tox installed (via `sudo pip install tox`)::

    tox


Other Useful Commands
#####################

#. List all of the supported test environments::

    tox --listenvs

#. Run a specific set of tests::

    tox -e <testenv>

.. _packages: https://packaging.python.org/en/latest/installing.html#installing-requirements
.. _git: http://git-scm.com
.. _installer: https://www.python.org/downloads/
