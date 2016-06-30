import functools
import os
import subprocess

import dcoscli
import docopt
import six
from dcos import (cmds, config, cosmospackage, emitting, errors, http, mesos,
                  util)
from dcos.errors import DCOSException, DefaultError
from dcoscli import log, tables
from dcoscli.package.main import confirm, get_cosmos_url
from dcoscli.subcommand import default_command_info, default_doc
from dcoscli.util import decorate_docopt_usage

from six.moves import urllib

logger = util.get_logger(__name__)
emitter = emitting.FlatEmitter()

SNAPSHOT_BASE_URL = '/system/health/v1/report/snapshot/'

# if snapshot size if more then 100Mb then warn user.
SNAPSHOT_WARN_SIZE = 1000000


def main(argv):
    try:
        return _main(argv)
    except DCOSException as e:
        emitter.publish(e)
        return 1


@decorate_docopt_usage
def _main(argv):
    args = docopt.docopt(
        default_doc("node"),
        argv=argv,
        version="dcos-node version {}".format(dcoscli.version))

    if args.get('--master'):
        raise DCOSException(
            '--master has been deprecated. Please use --leader.'
        )
    elif args.get('--slave'):
        raise DCOSException(
            '--slave has been deprecated. Please use --mesos-id.'
        )

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
            arg_keys=['--follow', '--lines', '--leader', '--mesos-id'],
            function=_log),

        cmds.Command(
            hierarchy=['node', 'ssh'],
            arg_keys=['--leader', '--mesos-id', '--option', '--config-file',
                      '--user', '--master-proxy', '<command>'],
            function=_ssh),

        cmds.Command(
            hierarchy=['node', 'snapshot', 'create'],
            arg_keys=['<nodes>'],
            function=_snapshot_create),

        cmds.Command(
            hierarchy=['node', 'snapshot', 'delete'],
            arg_keys=['<snapshot>'],
            function=_snapshot_delete),

        cmds.Command(
            hierarchy=['node', 'snapshot', 'download'],
            arg_keys=['<snapshot>', '--location'],
            function=_snapshot_download),

        cmds.Command(
            hierarchy=['node', 'snapshot'],
            arg_keys=['--list', '--status', '--cancel', '--json'],
            function=_snapshot_manage),

        cmds.Command(
            hierarchy=['node'],
            arg_keys=['--json'],
            function=_list)
    ]


def snapshot_error(fn):
    @functools.wraps(fn)
    def check_for_snapshot_error(*args, **kwargs):
        response = fn(*args, **kwargs)
        if response.status_code != 200:
            err_msg = ('Error making {} request\nURL: '
                       '{}, status_code: {}.'.format(args[1], args[0],
                                                     response.status_code))
            if not kwargs.get('stream'):
                err_status = _read_http_response_body(response).get('status')
                if err_status:
                    err_msg = err_status
            raise DCOSException(err_msg)
        return response
    return check_for_snapshot_error


def _check_3dt_version():
    """
    The function checks if cluster has snapshot capability.

    :raises: DCOSException if cluster does not have snapshot capability
    """

    cosmos = cosmospackage.Cosmos(get_cosmos_url())
    if not cosmos.has_capability('SUPPORT_CLUSTER_REPORT'):
        raise DCOSException(
            'DC/OS backend does not support snapshot capabilities in this '
            'version. Must be DC/OS >= 1.8')


# http://stackoverflow.com/questions/1094841/reusable-library-to-get-human-readable-version-of-file-size  # noqa
def sizeof_fmt(num, suffix='B'):
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


def _get_snapshots_json():
    """
    Get a json with a list of snapshots

    :return: available snapshots on a cluster.
    :rtype: dict
    """

    return _do_snapshot_request(
        urllib.parse.urljoin(SNAPSHOT_BASE_URL, 'list/all'),
        'GET')


def _get_snapshots_list():
    """
    Get a list of tuples (snapshot_file_name, file_size), ..

    :return: list of snapshots
    :rtype: list of tuples
    """

    available_snapshots = []
    for _, snapshot_files in _get_snapshots_json().items():
        if snapshot_files is None:
            continue
        for snapshot_file_obj in snapshot_files:
            if ('file_name' not in snapshot_file_obj
                    or 'file_size' not in snapshot_file_obj):
                raise DCOSException(
                    'Request to get a list of available snapshot returned '
                    'unexpected response {}'.format(snapshot_file_obj))

            available_snapshots.append(
                (os.path.basename(snapshot_file_obj['file_name']),
                 snapshot_file_obj['file_size']))
    return available_snapshots


def _snapshot_manage(list_snapshots, status, cancel, json):
    """
    Manage snapshots

    :param list_snapshots: a list of available snapshots
    :type  list_snapshots: bool
    :param status: show snapshot job status
    :type  status: bool
    :param cancel: cancel snapshot job
    :type  cancel: bool
    :return: process return code
    :rtype: int
    """

    _check_3dt_version()
    if list_snapshots:
        if json:
            emitter.publish(_get_snapshots_json())
            return 0

        available_snapshots = _get_snapshots_list()
        if not available_snapshots:
            emitter.publish("No snapshots")
            return 0
        emitter.publish("Available snapshots:")
        for available_snapshot in sorted(available_snapshots,
                                         key=lambda t: t[0]):
            emitter.publish('{} {}'.format(available_snapshot[0],
                                           sizeof_fmt(available_snapshot[1])))
        return 0
    elif status:
        url = urllib.parse.urljoin(SNAPSHOT_BASE_URL, 'status/all')
        snapshot_response = _do_snapshot_request(url, 'GET')
        if json:
            emitter.publish(snapshot_response)
            return 0

        for host, props in sorted(snapshot_response.items()):
            emitter.publish(host)
            for key, value in sorted(props.items()):
                emitter.publish('  {}: {}'.format(key, value))
            emitter.publish('\n')
        return 0
    elif cancel:
        url = urllib.parse.urljoin(SNAPSHOT_BASE_URL, 'cancel')
        snapshot_response = _do_snapshot_request(url, 'POST')
        if json:
            emitter.publish(snapshot_response)
            return 0

        if 'status' not in snapshot_response:
            raise DCOSException(
                'Request to cancel a snapshot job {} returned '
                'an unexpected response {}'.format(url, snapshot_response))

        emitter.publish(snapshot_response['status'])
        return 0
    else:
        raise DCOSException(
            'Must specify one of list_snapshots, status, cancel')


@snapshot_error
def _do_request(url, method, timeout=None, stream=False, **kwargs):
    """
    make HTTP request

    :param url: url
    :type url: string
    :param method: HTTP method, GET or POST
    :type  method: string
    :param timeout: HTTP request timeout, default 3 seconds
    :type  timeout: integer
    :param stream: stream parameter for requests lib
    :type  stream: bool
    :return: http response
    :rtype: requests.Response
    """

    def _is_success(status_code):
        # consider 400 and 503 to be successful status codes.
        # API will return the error message.
        if status_code in [200, 400, 503]:
            return True
        return False

    # if timeout is not passed, try to read `core.timeout`
    # if `core.timeout` is not set, default to 3 min.
    if timeout is None:
        timeout = config.get_config_val('core.timeout')
        if not timeout:
            timeout = 180

    # POST to snapshot api
    base_url = config.get_config_val("core.dcos_url")
    if not base_url:
        raise config.missing_config_exception(['core.dcos_url'])

    url = urllib.parse.urljoin(base_url, url)
    if method.lower() == 'get':
        http_response = http.get(url, is_success=_is_success, timeout=timeout,
                                 **kwargs)
    elif method.lower() == 'post':
        http_response = http.post(url, is_success=_is_success, timeout=timeout,
                                  stream=stream, **kwargs)
    else:
        raise DCOSException('Unsupported HTTP method: ' + method)
    return http_response


def _do_snapshot_request(url, method, **kwargs):
    """
    Make HTTP request and expect a JSON response.

    :param url: url
    :type url: string
    :param method: HTTP method, GET or POST
    :type method: string
    :return: snapshot JSON repsponse
    :rtype: dict
    """

    http_response = _do_request(url, method, **kwargs)
    return _read_http_response_body(http_response)


def _read_http_response_body(http_response):
    """
    Get an requests HTTP response, read it and deserialize to json.

    :param http_response: http response
    :type http_response: requests.Response onject
    :return: deserialized json
    :rtype: dict
    """

    data = b''
    try:
        for chunk in http_response.iter_content(1024):
            data += chunk
        snapshot_response = util.load_jsons(data.decode('utf-8'))
        return snapshot_response
    except DCOSException:
        raise


def _snapshot_download(snapshot, location):
    """
    Download snapshot and put in the the current directory.

    :param snapshot: snapshot file name.
    :type snapshot: string
    :return: status code
    :rtype: int
    """

    # make sure the requested snapshot exists
    snapshot_size = 0
    for available_snapshot in _get_snapshots_list():
        # _get_snapshot_list must return a list of tuples
        # where first element is file name and second is its size.
        if len(available_snapshot) != 2:
            raise DCOSException(
                'Request to get a list of snapshots returned an '
                'unexpected response: {}'.format(available_snapshot))

        # available_snapshot[0] is a snapshot file name
        # available_snapshot[1] is a snapshot file size
        if available_snapshot[0] == snapshot:
            snapshot_size = available_snapshot[1]

    url = urllib.parse.urljoin(SNAPSHOT_BASE_URL, 'serve/' + snapshot)
    snapshot_location = os.path.join(os.getcwd(), snapshot)
    if location:
        if os.path.isdir(location):
            snapshot_location = os.path.join(location, snapshot)
        else:
            snapshot_location = location

    if snapshot_size > SNAPSHOT_WARN_SIZE:
        if not confirm('Snapshot size is {}, are you sure you want '
                       'to download it?'.format(sizeof_fmt(snapshot_size)),
                       False):
            return 0

    r = _do_request(url, 'GET', stream=True)
    try:
        with open(snapshot_location, 'wb') as f:
            for chunk in r.iter_content(1024):
                f.write(chunk)
    except Exception as e:
        raise DCOSException(e)
    emitter.publish('Snapshot downloaded to ' + snapshot_location)
    return 0


def _snapshot_delete(snapshot):
    """
    Delete a snapshot

    :param snapshot: snapshot file name
    :type: str
    :return: status code
    :rtype: int
    """

    _check_3dt_version()
    url = urllib.parse.urljoin(
        SNAPSHOT_BASE_URL, 'delete/' + snapshot)
    response = _do_snapshot_request(url, 'POST')

    if 'status' not in response:
        raise DCOSException(
            'Request to delete the snapshot {} returned an '
            'unexpected response {}'.format(url, response))

    emitter.publish(response['status'])
    return 0


def _snapshot_create(nodes):
    """
    Create a snapshot.

    :param nodes: a list of nodes to collect the logs from.
    :type nodes: list
    :returns: process return code
    :rtype: int
    """

    _check_3dt_version()
    url = urllib.parse.urljoin(SNAPSHOT_BASE_URL, 'create')
    response = _do_snapshot_request(url,
                                    'POST',
                                    json={'nodes': nodes})
    if ('status' not in response or 'extra' not in response
            or 'snapshot_name' not in response['extra']):
        raise DCOSException(
            'Request to create snapshot {} returned an '
            'unexpected response {}'.format(url, response))

    emitter.publish('\n{}, available snapshot: {}'.format(
        response['status'],
        response['extra']['snapshot_name']))
    return 0


def _info():
    """Print node cli information.

    :returns: process return code
    :rtype: int
    """

    emitter.publish(default_command_info("node"))
    return 0


def _list(json_):
    """List DC/OS nodes

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
        output = six.text_type(table)
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


def _ssh(leader, slave, option, config_file, user, master_proxy, command):
    """SSH into a DC/OS node using the IP addresses found in master's
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
    :param command: Command to run on the node
    :type command: str | None
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

    if command is None:
        command = ''

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

        cmd = "ssh -A -t {0}{1}@{2} ssh -A -t {0}{1}@{3} {4}".format(
            ssh_options,
            user,
            master_public_ip,
            host,
            command)
    else:
        cmd = "ssh -t {0}{1}@{2} {3}".format(
            ssh_options,
            user,
            host,
            command)

    emitter.publish(DefaultError("Running `{}`".format(cmd)))
    if (not master_proxy) and master_public_ip:
        emitter.publish(
            DefaultError("If you are running this command from a separate "
                         "network than DC/OS, consider using "
                         "`--master-proxy`"))

    return subprocess.call(cmd, shell=True)
