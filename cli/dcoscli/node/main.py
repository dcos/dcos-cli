"""Manage DCOS nodes

Usage:
    dcos node --info
    dcos node [--json]

Options:
    -h, --help    Show this screen
    --info        Show a short description of this subcommand
    --json        Print json-formatted nodes
    --version     Show version
"""

import dcoscli
import docopt
from dcos import cmds, emitting, errors, mesos, util
from dcos.errors import DCOSException
from dcoscli import tables

logger = util.get_logger(__name__)
emitter = emitting.FlatEmitter()


def main():
    try:
        return _main()
    except DCOSException as e:
        emitter.publish(e)
        return 1


def _main():
    util.configure_logger_from_environ()

    args = docopt.docopt(
        __doc__,
        version="dcos-node version {}".format(dcoscli.version))

    return cmds.execute(_cmds(), args)


def _cmds():
    """
    :returns: All of the supported commands
    :rtype: [Command]
    """

    return [
        cmds.Command(
            hierarchy=['node', '--info'],
            arg_keys=[],
            function=_info),

        cmds.Command(
            hierarchy=['node'],
            arg_keys=['--json'],
            function=_list),
    ]


def _info():
    """Print node cli information.

    :returns: process return code
    :rtype: int
    """

    emitter.publish(__doc__.split('\n')[0])
    return 0


def _list(json_):
    """List dcos nodes

    :param json_: If true, output json.
        Otherwise, output a human readable table.
    :type json_: bool
    :returns: process return code
    :rtype: int
    """

    client = mesos.MesosClient()
    slaves = client.get_state_summary()['slaves']
    if json_:
        emitter.publish(slaves)
    else:
        table = tables.slave_table(slaves)
        output = str(table)
        if output:
            emitter.publish(output)
        else:
            emitter.publish(errors.DefaultError('No slaves found.'))
