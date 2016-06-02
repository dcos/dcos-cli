import os
import subprocess
import requests

import dcoscli
import docopt
from dcos import cmds, emitting, errors, mesos, util
from dcos.errors import DCOSException, DefaultError
from dcoscli import log, tables
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
        default_doc("opendcre"),
        argv=argv,
        version="opendcre version {}".format(dcoscli.version))

    return cmds.execute(_cmds(), args)


def _cmds():
    """
    :returns: All of the supported commands
    :rtype: [Command]
    """

    return [
        cmds.Command(
            hierarchy=['opendcre', '--info'],
            arg_keys=[],
            function=_info),

        cmds.Command(
            hierarchy=['opendcre', 'scan'],
            arg_keys=[],
            function=_scan),

        cmds.Command(
            hierarchy=['opendcre', 'read'],
            arg_keys=['<device-type>', '<board-id>', '<device-id>'],
            function=_read),

        cmds.Command(
            hierarchy=['opendcre', 'asset'],
            arg_keys=['<board-id>', '<device-id>'],
            function=_asset),

    ]


def _info():
    """Print node cli information.

    :returns: process return code
    :rtype: int
    """

    emitter.publish(default_command_info("opendcre"))
    return 0


def _scan():
    """

    :return:
    """
    # FIXME - for the purposes of proof-of-concept, the url is just hardcoded here, should be changed!
    url = 'http://192.168.99.100:5000/vaporcore/1.0/scan'
    r = requests.get(url)

    if r.status_code == 200:
        emitter.publish(r.text)
    else:
        raise DCOSException("Failed to perform scan\n: {}".format(r.text))
    return 0


def _read(device_type, board_id, device_id):
    """

    :param device_type:
    :param board_id:
    :param device_id:
    :return:
    """
    # FIXME - for the purposes of proof-of-concept, the url is just hardcoded here, should be changed!
    url = 'http://192.168.99.100:5000/vaporcore/1.0/read/{}/{}/{}'.format(device_type, board_id, device_id)
    r = requests.get(url)

    if r.status_code == 200:
        emitter.publish(r.text)
    else:
        raise DCOSException("Failed to perform scan\n: {}".format(r.text))
    return 0


def _asset(board_id, device_id):
    """

    :param board_id:
    :param device_id:
    :return:
    """
    # FIXME - for the purposes of proof-of-concept, the url is just hardcoded here, should be changed!
    url = 'http://192.168.99.100:5000/vaporcore/1.0/asset/{}/{}'.format(board_id, device_id)
    r = requests.get(url)

    if r.status_code == 200:
        emitter.publish(r.text)
    else:
        raise DCOSException("Failed to retrieve asset information\n: {}".format(r.text))
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


def _log(follow, lines, leader, slave):
    """ Prints the contents of leader and slave logs.

    :param follow: same as unix tail's -f
    :type follow: bool
    :param lines: number of lines to print
    :type lines: int
    :param leader: whether to print the leading master's log
    :type leader: bool
    :param slave: the slave ID to print
    :type slave: str | None
    :returns: process return code
    :rtype: int
    """

    if not (leader or slave):
        raise DCOSException('You must choose one of --leader or --mesos-id.')

    if lines is None:
        lines = 10
    lines = util.parse_int(lines)

    mesos_files = _mesos_files(leader, slave)

    log.log_files(mesos_files, follow, lines)

    return 0


def _mesos_files(leader, slave_id):
    """Returns the MesosFile objects to log

    :param leader: whether to include the leading master's log file
    :type leader: bool
    :param slave_id: the ID of a slave.  used to include a slave's log
                     file
    :type slave_id: str | None
    :returns: MesosFile objects
    :rtype: [MesosFile]
    """

    files = []
    if leader:
        files.append(mesos.MesosFile('/master/log'))
    if slave_id:
        slave = mesos.get_master().slave(slave_id)
        files.append(mesos.MesosFile('/slave/log', slave=slave))
    return files


def _ssh(leader, slave, option, config_file, user, master_proxy):
    """SSH into a DCOS node using the IP addresses found in master's
       state.json

    :param leader: True if the user has opted to SSH into the leading
                   master
    :type leader: bool | None
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

    if leader:
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
