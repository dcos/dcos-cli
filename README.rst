DCOS Command Line Interface
===========================
The DCOS Command Line Interface (CLI) is a command line utility supporting several commands to
provide an user friendly yet powerful way to manage DCOS installations.

Setup
-----

#. Make sure you meet requirements for installing packages_
#. Clone git repo for the dcos cli::

    git clone git@github.com:mesosphere/dcos-cli.git

#. Change directory to the repo directory::

    cd dcos-cli

#. Make sure that you have virtual env installed. If not type:

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

#. Get started by calling DCOS CLI help::

    dcos --help

Running Tests:
--------------

#. Run all DCOS CLI tests (make sure that you are running Zookeeper, Mesos and Marathon)::

    tox

#. List all of the supported test environments::

    tox --listenvs

#. Run a specific set of tests::

    tox -e <testenv>

.. _packages: https://packaging.python.org/en/latest/installing.html#installing-requirements
