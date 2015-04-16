DCOS Command Line Interface
===========================
The DCOS Command Line Interface (CLI) is a command line utility supporting
several commands to provide an user friendly yet powerful way to manage DCOS
installations.

Dependencies
------------

#. git_ must be installed and on the system path in order to fetch
   packages from :code:`git` sources.

#. virtualenv_ must be installed and on the system path in order to install
   subcommands.

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

#. Configure Marathon, changing the values below as appropriate for your local
   installation::

    dcos config set marathon.host localhost
    dcos config set marathon.port 8080
    dcos config append package.sources https://github.com/mesosphere/universe/archive/master.zip
    dcos config set package.cache /tmp/dcos
    dcos package update

#. Get started by calling the DCOS CLI help::

    dcos help

Running Tests:
--------------

Setup
#####

Tox, our test runner, tests against both Python 2.7 and Python 3.4
environments.

If you're using OS X, be sure to use the officially distributed Python 3.4
installer_ since the Homebrew version is missing a necessary library.

To support subcommand integration tests, you'll need to clone, package and
configure your environment to point to the packaged `dcos-helloworld` account.

#. Check out the dcos-helloworld_ project

#. :code:`cd dcos-helloworld`

#. :code:`make packages`

#. Set the :code:`DCOS_TEST_WHEEL` environment variable to the path of the created
   wheel package: :code:`export DCOS_TEST_WHEEL=$(pwd)/dist/dcos_helloworld-0.1.0-py2.py3-none-any.whl`

Running
#######

Tox will run unit and integration tests in both Python environments using a
temporarily created virtualenv.

You should ensure :code:`DCOS_CONFIG` is set and that the config file points
to the Marathon instance you want to use for integration tests. If you're
happy to use the default test configuration which assumes there is a Marathon
instance running on localhost, set :code:`DCOS_CONFIG` as follows::

    export DCOS_CONFIG=$(pwd)/tests/data/dcos.toml

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

.. _packages: https://packaging.python.org/en/latest/installing.html#installing-requirements
.. _git: http://git-scm.com
.. _installer: https://www.python.org/downloads/
.. _virtualenv: https://virtualenv.pypa.io/en/latest/
.. _dcos-helloworld: https://github.com/mesosphere/dcos-helloworld
.. _setup: https://github.com/mesosphere/dcos-helloworld#setup
