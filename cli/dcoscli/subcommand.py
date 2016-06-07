import traceback
from importlib import import_module

import pkg_resources

from dcos import subcommand


def _default_modules():
    """Dict of the default dcos cli subcommands and their main methods

    :returns: default subcommand -> main method
    :rtype: {}
    """

    defaults = subcommand.default_subcommands()
    return {s: import_module('dcoscli.{}.main'.format(s)) for s in defaults}


def default_doc(command):
    """Returns documentation of command

    :param command: default DC/OS CLI command
    :type command: str
    :returns: config schema of command
    :rtype: dict
    """

    resource = "data/help/{}.txt".format(command)
    return pkg_resources.resource_string(
        'dcoscli',
        resource).decode('utf-8')


def default_command_info(command):
    """top level documentation of default DC/OS CLI command

    :param command: name of command
    :param type: str
    :returns: command summary
    :rtype: str
    """

    doc = default_command_documentation(command)
    return doc.split('\n')[1].strip(".").lstrip()


def default_command_documentation(command):
    """documentation of default DC/OS CLI command

    :param command: name of command
    :param type: str
    :returns: command summary
    :rtype: str
    """

    return default_doc(command).rstrip('\n')


class SubcommandMain():

    def __init__(self, command, args):
        """Representes a subcommand running in the main thread

        :param commad: function to run in thread
        :type command: str
        """

        self._command = command
        self._args = args

    def run_and_capture(self):
        """
        Run a command and capture exceptions. This is a blocking call
        :returns: tuple of exitcode, error (or None)
        :rtype: int, str | None
        """

        m = _default_modules()[self._command]
        err = None
        try:
            exit_code = m.main([self._command] + self._args)
        except Exception:
            err = traceback.format_exc()
            traceback.print_exc()
            exit_code = 1
        return exit_code, err
