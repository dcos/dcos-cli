=========
dcos-cli
=========

CLI tools to work with dcos.

-----------------------------
What problem does this solve?
-----------------------------

--------------------------
How is the problem solved?
--------------------------

------------
Installation
------------

.. code-block:: bash

    pip install dcos

-------------------
Command Completion
-------------------

Task IDs? File names? Complete all the things! Configure command completion and you'll be able to tab complete most everything.

+++++
BASH
+++++

Add the following to your startup scripts:

.. code-block:: bash

    complete -C dcos-completion dcos

++++
ZSH
++++

Add the following to your `.zshrc`:

.. code-block:: bash

    source dcos-zsh-completion.sh

Note that `bashcompinit` is being used. If you're running an older version of ZSH, it won't work. Take a look at `bin/dcos-zsh-completion.sh` for information.

-------------
Configuration
-------------

Place a configuration file at any of the following:

.. code-block:: bash

    ./.dcos.json
    ~/.dcos.json
    /etc/.dcos.json
    /usr/etc/.dcos.json
    /usr/local/etc/.dcos.json

You can override the location of this config via. `DCOS_CLI_CONFIG`.

If you're using a non-local master, you'll need to configure where the master should be found like so:

.. code-block:: bash

    dcos config master zk://localhost:2181/mesos

Alternatively, you can create the config file yourself.

.. code-block:: json

    {
        "profile": "default",
        "default": {
            "master": "zk://localhost:2181/mesos",
            "log_level": "warning",
            "log_file": "/tmp/dcos-cli.log"
        }
    }

Note that master accepts all values that mesos normally does, eg:

.. code-block:: bash

    localhost:5050
    zk://localhost:2181/mesos
    file:///path/to/config/above

+++++++++
Profiles
+++++++++

Want to access multiple clusters without changing config? You're in luck!

To change your profile, you can run:

.. code-block:: bash

    dcos config profile new-profile

The old config will be maintained and can be switched back to at any point.

+++++++++++++++
Config Options
+++++++++++++++

========
Commands
========

All commands have their own options and parameters. Make sure you run `dcos [command] --help` to get the potential options.

===============
Adding Commands
===============

Commands are all separate scripts. The `dcos` script inspects your path and looks for everything that starts with `dcos-`. To add a new command, just name the script `dcos-new-name` and you'll have a new command. This makes it possible to write new sub-commands in whatever language you'd like.

There are some utils that are nice to have when you're doing a new command. While all of them are available in python via. this package, a subset is available via. existing commands. This allows you to focus on the new functionality you'd like in your command (in the language you're comfortable with).

=======
Testing
=======

There are two ways to do testing. If you'd like to just test with your local setup:

    python setup.py nosetests

For a full virtualenv + specific python versions (py26, py27), you can use tox:

    tox
