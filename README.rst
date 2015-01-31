DCOS CLI
=======
DCOS CLI with modular subcommands.

Setup
-----

#. Make sure you meet requirements for installing packages_
#. Install the "wheel" project::

    pip install wheel

#. Install the tox project::

    pip install tox

#. Clone git repo for the dcos cli::

    git clone git@github.com:mesosphere/dcos-cli.git

#. Change directory to the repo directory::

    cd dcos-cli

#. Create a virtualenv for the dcos cli project::

    virtualenv --prompt='(dcos-cli) ' env

Configure Development Environment
---------------------------------

#. Activate the virtualenv::

    source env/bin/activate

#. Install project in develop mode::

    pip install -e .

#. Export DCOS_PATH::

    export DCOS_PATH=<path-to-project>/env

#. Export DCOS_CONFIG::

    mkdir $DCOS_PATH/config
    touch $DCOS_PATH/config/Dcos.toml
    export DCOS_CONFIG=$DCOS_PATH/config/Dcos.toml

Running POC
-----------

#. List command help::

    dcos --help

#. Run subcommand::

    dcos config --help

Running Tests:
--------------

#. Run tests using tox::

    tox

#. Run tests using tox through docker::

    CHECKOUT=<path-to-repo> \
    export DOCKER_REPO=mesosphere/python-tox \
    export DOCKER_TAG=v1 \
    sudo docker run -it -v $CHECKOUT:/dcos-cli $DOCKER_REPO:$DOCKER_TAG tox -c /dcos-cli/tox.ini

Notes
-----
Submodule writing notes gathered so far:

#. Because we are using python's pip to install packages it looks like we can't install packages
   that share the same python's package of other installed packages because they will conflict once
   deployed to virtualenv directory structure.

#. Currently we require that subcommands implement an info command. For example dcos-subcommand
   implements ``subcommand info``.

.. _packages: https://packaging.python.org/en/latest/installing.html#installing-requirements
