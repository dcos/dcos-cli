import json
import os
import sys

from dcos.api import constants, util
from mesos.cli import cli

def main():
    error = util.configure_logger_from_environ()
    if error is not None:
        print(error.error())
        return 1

    config_path = os.environ[constants.DCOS_CONFIG_ENV]

    if len(sys.argv) == 2:
        cmd = "mesos-help"
    elif sys.argv[2] == "info":
        return _info()
    else:
        cmd = "mesos-" + sys.argv[2]

    if cmd in cli.cmds():
        return os.execvp(cmd, [cmd] + sys.argv[3:])

def _info():
    """Print Mesos CLI information.

    :returns: Process status
    :rtype: int
    """

    print('Interact with the configured Apache Mesos installation')
    return 0
