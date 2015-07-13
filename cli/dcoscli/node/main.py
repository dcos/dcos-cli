"""Manage DCOS nodes

Usage:
    dcos node --info
    dcos node [--json --colors]
    dcos node log [--follow --lines=N --master --slave=<slave-id>]

Options:
    -h, --help            Show this screen
    --info                Show a short description of this subcommand
    --json                Print json-formatted nodes
    --colors              Json syntax highlighting
    --follow              Output data as the file grows
    --lines=N             Output the last N lines [default: 10]
    --master              Output the leading master's Mesos log
    --slave=<slave-id>    Output this slave's Mesos log
    --version             Show version
"""

import dcoscli
import docopt
from dcos import cmds, emitting, errors, mesos, util
from dcos.errors import DCOSException
from dcoscli import log, tables

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
            hierarchy=['node', 'log'],
            arg_keys=['--follow', '--lines', '--master', '--slave'],
            function=_log),

        cmds.Command(
            hierarchy=['node'],
            arg_keys=['--json', '--colors'],
            function=_list),
    ]


def _info():
    """Print node cli information.

    :returns: process return code
    :rtype: int
    """

    emitter.publish(__doc__.split('\n')[0])
    return 0


def _list(json_, colors):
    """List dcos nodes

    :param json_: If true, output json.
        Otherwise, output a human readable table.
    :type json_: bool
    :returns: process return code
    :param colors: Json syntax highlighting if True
    :type colors: bool
    :rtype: int
    """
    util.check_if_colors_allowed(json_, colors)

    client = mesos.MesosClient()
    slaves = client.get_state_summary()['slaves']
    if json_:
        emitter.publish(slaves, colors)
    else:
        table = tables.slave_table(slaves)
        output = str(table)
        if output:
            emitter.publish(output)
        else:
            emitter.publish(errors.DefaultError('No slaves found.'))


def _log(follow, lines, master, slave):
    """ Prints the contents of master and slave logs.

    :param follow: same as unix tail's -f
    :type follow: bool
    :param lines: number of lines to print
    :type lines: int
    :param master: whether to print the master log
    :type master: bool
    :param slave: the slave ID to print
    :type slave: str | None
    :returns: process return code
    :rtype: int
    """

    if not (master or slave):
        raise DCOSException('You must choose one of --master or --slave.')

    lines = util.parse_int(lines)

    mesos_files = _mesos_files(master, slave)

    log.log_files(mesos_files, follow, lines)

    return 0


def _mesos_files(master, slave_id):
    """Returns the MesosFile objects to log

    :param master: whether to include the master log file
    :type master: bool
    :param slave_id: the ID of a slave.  used to include a slave's log
                     file
    :type slave_id: str | None
    :returns: MesosFile objects
    :rtype: [MesosFile]
    """

    files = []
    if master:
        files.append(mesos.MesosFile('/master/log'))
    if slave_id:
        slave = mesos.get_master().slave(slave_id)
        files.append(mesos.MesosFile('/slave/log', slave=slave))
    return files
