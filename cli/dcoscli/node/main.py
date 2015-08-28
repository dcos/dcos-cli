import os
import subprocess

import dcoscli
import docopt
import pkg_resources
from dcos import cmds, emitting, errors, mesos, util
from dcos.errors import DCOSException, DefaultError
from dcoscli import log, tables
from dcoscli.main import decorate_docopt_usage

logger = util.get_logger(__name__)
emitter = emitting.FlatEmitter()


def main():
    try:
        return _main()
    except DCOSException as e:
        emitter.publish(e)
        return 1


@decorate_docopt_usage
def _main():
    util.configure_process_from_environ()

    args = docopt.docopt(
        _doc(),
        version="dcos-node version {}".format(dcoscli.version))

    return cmds.execute(_cmds(), args)


def _doc():
    """
    :rtype: str
    """
    return pkg_resources.resource_string(
        'dcoscli',
        'data/help/node.txt').decode('utf-8')


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
                      '--user', '--master-proxy'],
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

    emitter.publish(_doc().split('\n')[0])
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


def _ssh(master, slave, option, config_file, user, master_proxy):
    """SSH into a DCOS node using the IP addresses found in master's
       state.json

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
    :param master_proxy: If True, SSH-hop from a master
    :type master_proxy: bool | None
    :rtype: int
    :returns: process return code
    """

    ssh_options = util.get_ssh_options(config_file, option)
    dcos_client = mesos.DCOSClient()

    if master:
        host = mesos.MesosDNSClient().hosts('leader.mesos.')[0]['ip']
    else:
        summary = dcos_client.get_state_summary()
        slave_obj = next((slave_ for slave_ in summary['slaves']
                          if slave_['id'] == slave),
                         None)
        if slave_obj:
            host = mesos.parse_pid(slave_obj['pid'])[1]
        else:
            raise DCOSException('No slave found with ID [{}]'.format(slave))

    master_public_ip = dcos_client.metadata().get('PUBLIC_IPV4')
    if master_proxy:
        if not os.environ.get('SSH_AUTH_SOCK'):
            raise DCOSException(
                "There is no SSH_AUTH_SOCK env variable, which likely means "
                "you aren't running `ssh-agent`.  `dcos node ssh "
                "--master-proxy` depends on `ssh-agent` to safely use your "
                "private key to hop between nodes in your cluster.  Please "
                "run `ssh-agent`, then add your private key with `ssh-add`.")
        if not master_public_ip:
            raise DCOSException(("Cannot use --master-proxy.  Failed to find "
                                 "'PUBLIC_IPV4' at {}").format(
                                     dcos_client.get_dcos_url('metadata')))

        cmd = "ssh -A -t {0}{1}@{2} ssh -A -t {1}@{3}".format(
            ssh_options,
            user,
            master_public_ip,
            host)
    else:
        cmd = "ssh -t {0}{1}@{2}".format(
            ssh_options,
            user,
            host)

    emitter.publish(DefaultError("Running `{}`".format(cmd)))
    if (not master_proxy) and master_public_ip:
        emitter.publish(
            DefaultError("If you are running this command from a separate "
                         "network than DCOS, consider using `--master-proxy`"))

    return subprocess.call(cmd, shell=True)
