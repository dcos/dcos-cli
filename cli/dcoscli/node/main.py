"""Manage DCOS nodes

Usage:
    dcos node --info
    dcos node [--json]
    dcos node log [--follow --lines=N --master --slave=<slave-id>]
    dcos node ssh [--option SSHOPT=VAL ...]
                  [--config-file=<path>]
                  [--user=<user>]
                  (--master | --slave=<slave-id>)

Options:
    -h, --help              Show this screen
    --info                  Show a short description of this subcommand
    --json                  Print json-formatted nodes
    --follow                Output data as the file grows
    --lines=N               Output the last N lines [default: 10]
    --master                Access the leading master
    --slave=<slave-id>      Access the slave with the provided ID
    --option SSHOPT=VAL     SSH option (see `man ssh_config`)
    --config-file=<path>    Path to SSH config file
    --user=<user>           SSH user [default: core]
    --version               Show version
"""

import subprocess

import dcoscli
import docopt
from dcos import cmds, emitting, errors, mesos, util
from dcos.errors import DCOSException, DefaultError
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
    util.configure_process_from_environ()

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
            hierarchy=['node', 'ssh'],
            arg_keys=['--master', '--slave', '--option', '--config-file',
                      '--user'],
            function=_ssh),

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
    """List DCOS nodes

    :param json_: If true, output json.
        Otherwise, output a human readable table.
    :type json_: bool
    :returns: process return code
    :rtype: int
    """

    client = mesos.DCOSClient()
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


def _ssh(master, slave, option, config_file, user):
    """SSH into a DCOS node.  Since only the masters are definitely
    publicly available, we first ssh into an arbitrary master, then
    hop to the desired node.

    :param master: True if the user has opted to SSH into the leading
                   master
    :type master: bool | None
    :param slave: The slave ID if the user has opted to SSH into a slave
    :type slave: str | None
    :param option: SSH option
    :type option: [str]
    :param config_file: SSH config file
    :type config_file: str | None
    :param user: SSH user
    :type user: str | None
    :rtype: int
    :returns: process return code
    """

    ssh_options = util.get_ssh_options(config_file, option)

    if master:
        host = mesos.MesosDNSClient().hosts('leader.mesos.')[0]['ip']
    else:
        summary = mesos.DCOSClient().get_state_summary()
        slave_obj = next((slave_ for slave_ in summary['slaves']
                          if slave_['id'] == slave),
                         None)
        if slave_obj:
            host = mesos.parse_pid(slave_obj['pid'])[1]
        else:
            raise DCOSException('No slave found with ID [{}]'.format(slave))

    cmd = "ssh -t {0}{1}@{2}".format(
        ssh_options,
        user,
        host)

    emitter.publish(DefaultError("Running `{}`".format(cmd)))

    return subprocess.call(cmd, shell=True)
