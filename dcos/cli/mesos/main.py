import os
import sys

from dcos.api import constants, emitting, util
from mesos.cli import cli

emitter = emitting.FlatEmitter()


def main():
    error = util.configure_logger_from_environ()
    if error is not None:
        print(error.error())
        return 1

    if len(sys.argv) == 2:
        cmd = "mesos-help"
    elif sys.argv[2] == "--help":
        cmd = "mesos-help"
    elif sys.argv[2] == "--version":
        return _version()
    elif sys.argv[2] == "info":
        return _info()
    else:
        cmd = "mesos-" + sys.argv[2]

    if cmd in cli.cmds():
        return os.execvp(cmd, [cmd] + sys.argv[3:])


def _version():
    """
    :returns: Process status
    :rtype: int
    """
    emitter.publish('dcos-mesos version {}'.format(constants.version))
    return 0


def _info():
    """
    :returns: Process status
    :rtype: int
    """

    print('Inspect and manage the Apache Mesos installation')
    return 0
