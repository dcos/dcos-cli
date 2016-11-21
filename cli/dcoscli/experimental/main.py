import docopt
import dcoscli

from dcos import (cmds, emitting, http, util)
from dcos.errors import DCOSException
from dcoscli.subcommand import (default_command_info, default_doc)
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
    return []


def _info():
    """
    :returns: process status
    :rtype: int
    """
    emitter.publish(default_command_info("experimental"))
    return 0

