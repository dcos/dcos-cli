import traceback

import pkg_resources


# must also add subcommand name to dcos.subcommand.default_subcommands
def _default_modules():
    """Dict of the default dcos cli subcommands and their main methods

    :returns: default subcommand -> main method
    :rtype: {}
    """

    # avoid circular imports
    from dcoscli.auth import main as auth_main
    from dcoscli.config import main as config_main
    from dcoscli.help import main as help_main
    from dcoscli.job import main as job_main
    from dcoscli.marathon import main as marathon_main
    from dcoscli.node import main as node_main
    from dcoscli.package import main as package_main
    from dcoscli.service import main as service_main
    from dcoscli.task import main as task_main

    return {'auth': auth_main,
            'config': config_main,
            'help': help_main,
            'job': job_main,
            'marathon': marathon_main,
            'node': node_main,
            'package': package_main,
            'service': service_main,
            'task': task_main
            }


def default_doc(command):
    """Returns documentation of command

    :param command: default DC/OS CLI command
    :type command: str
    :returns: config schema of command
    :rtype: str
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
    return doc.splitlines()[1].strip(".").lstrip()


def default_command_documentation(command):
    """documentation of default DC/OS CLI command

    :param command: name of command
    :param type: str
    :returns: command summary
    :rtype: str
    """

    return default_doc(command).rstrip('\r\n')


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
