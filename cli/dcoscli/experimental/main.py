import docopt

import dcoscli

from dcos import cmds, emitting, http, util
from dcos.errors import DCOSException
from dcos.package import get_package_manager
from dcoscli.subcommand import default_command_info, default_doc
from dcoscli.util import decorate_docopt_usage


logger = util.get_logger(__name__)
emitter = emitting.FlatEmitter()


def main(argv):
    try:
        return _main(argv)
    except DCOSException as e:
        emitter.publish(e)
        return 1


@decorate_docopt_usage
def _main(argv):
    args = docopt.docopt(
        default_doc("experimental"),
        argv=argv,
        version='dcos-experimental version {}'.format(dcoscli.version))
    http.silence_requests_warnings()
    return cmds.execute(_cmds(), args)


def _cmds():
    """
    :returns: All of the supported commands
    :rtype: dcos.cmds.Command
    """
    return [
        cmds.Command(
            hierarchy=['experimental', 'package', 'add'],
            arg_keys=['<dcos-package>'],
            function=_add),
    ]


def _info():
    """
    :returns: process status
    :rtype: int
    """
    emitter.publish(default_command_info("experimental"))
    return 0


def _add(dcos_package):
    """
    Adds a DC/OS package to DC/OS

    :param dcos_package: path to the DC/OS package
    :type dcos_package: str
    :return: process status
    :rtype: int
    """
    package_manager = get_package_manager()
    response = package_manager.experimental_package_add(dcos_package)
    emitter.publish(response.json())
    return 0
