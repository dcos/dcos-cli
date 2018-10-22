import os
from functools import partial, wraps

import docopt
import six
from six.moves import urllib

import dcoscli
from dcos import (cmds, config, emitting, errors,
                  http, mesos, packagemanager, ssh_util, subprocess, util)
from dcos.cosmos import get_cosmos_url
from dcos.errors import DCOSException, DefaultError
from dcoscli import log, metrics, tables
from dcoscli.subcommand import default_command_info, default_doc
from dcoscli.util import cluster_version_check, confirm, decorate_docopt_usage


logger = util.get_logger(__name__)
emitter = emitting.FlatEmitter()

DIAGNOSTICS_BASE_URL = '/system/health/v1/report/diagnostics/'


# if a bundle size if more then 100Mb then warn user.
BUNDLE_WARN_SIZE = 100 * 1000 * 1000


def main(argv):
    try:
        return _main(argv)
    except DCOSException as e:
        emitter.publish(e)
        return 1


@decorate_docopt_usage
@cluster_version_check
def _main(argv):
    args = docopt.docopt(
        default_doc("node"),
        argv=argv,
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
            arg_keys=['--follow', '--lines', '--leader', '--mesos-id',
                      '--component', '--filter'],
            function=_log),

        cmds.Command(
            hierarchy=['node', 'metrics', 'details'],
            arg_keys=['<mesos-id>', '--json'],
            function=partial(_metrics, False)),

        cmds.Command(
            hierarchy=['node', 'metrics', 'summary'],
            arg_keys=['<mesos-id>', '--json'],
            function=partial(_metrics, True)),

        cmds.Command(
            hierarchy=['node', 'list-components'],
            arg_keys=['--leader', '--mesos-id', '--json'],
            function=_list_components),

        cmds.Command(
            hierarchy=['node', 'ssh'],
            arg_keys=['--leader', '--mesos-id', '--option', '--config-file',
                      '--user', '--master-proxy', '--proxy-ip', '--private-ip',
                      '<command>'],
            function=_ssh),

        cmds.Command(
            hierarchy=['node', 'diagnostics', 'create'],
            arg_keys=['<nodes>'],
            function=_bundle_create),

        cmds.Command(
            hierarchy=['node', 'diagnostics', 'delete'],
            arg_keys=['<bundle>'],
            function=_bundle_delete),

        cmds.Command(
            hierarchy=['node', 'diagnostics', 'download'],
            arg_keys=['<bundle>', '--location'],
            function=_bundle_download),

        cmds.Command(
            hierarchy=['node', 'diagnostics'],
            arg_keys=['--list', '--status', '--cancel', '--json'],
            function=_bundle_manage),

        cmds.Command(
            hierarchy=['node', 'dns'],
            arg_keys=['<dns-name>', '--json'],
            function=_dns_lookup),

        cmds.Command(
            hierarchy=['node', 'decommission'],
            arg_keys=['<mesos-id>'],
            function=_decommission),

        cmds.Command(
            hierarchy=['node'],
            arg_keys=['--json', '--field'],
            function=_list)
    ]


def diagnostics_error(fn):
    @wraps(fn)
    def check_for_diagnostics_error(*args, **kwargs):
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
    return check_for_diagnostics_error


def _check_3dt_version():
    """
    The function checks if cluster has diagnostics capability.

    :raises: DCOSException if cluster does not have diagnostics capability
    """

    cosmos = packagemanager.PackageManager(get_cosmos_url())
    if not cosmos.has_capability('SUPPORT_CLUSTER_REPORT'):
        raise DCOSException(
            'DC/OS backend does not support diagnostics capabilities in this '
            'version. Must be DC/OS >= 1.8')


# http://stackoverflow.com/questions/1094841/reusable-library-to-get-human-readable-version-of-file-size  # noqa
def sizeof_fmt(num, suffix='B'):
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


def _get_bundles_json():
    """
    Get a json with a list of diagnostics bundles.

    :return: available diagnostics bundles on a cluster.
    :rtype: dict
    """

    return _do_diagnostics_request(
        urllib.parse.urljoin(DIAGNOSTICS_BASE_URL, 'list/all'),
        'GET')


def _get_bundle_list():
    """
    Get a list of tuples (bundle_file_name, file_size), ..

    :return: list of diagnostic bundles
    :rtype: list of tuples
    """

    available_bundles = []
    for _, bundle_files in _get_bundles_json().items():
        if bundle_files is None:
            continue
        for bundle_file_obj in bundle_files:
            if ('file_name' not in bundle_file_obj
                    or 'file_size' not in bundle_file_obj):
                raise DCOSException(
                    'Request to get a list of available diagnostic bundles '
                    'returned unexpected response {}'.format(bundle_file_obj))

            available_bundles.append(
                (os.path.basename(bundle_file_obj['file_name']),
                 bundle_file_obj['file_size']))
    return available_bundles


def _bundle_manage(list_bundles, status, cancel, json):
    """
    Manage diagnostic bundles

    :param list_bundles: a list of available bundles
    :type  list_bundles: bool
    :param status: show diagnostics job status
    :type  status: bool
    :param cancel: cancel diagnostics job
    :type  cancel: bool
    :return: process return code
    :rtype: int
    """

    _check_3dt_version()
    if list_bundles:
        if json:
            emitter.publish(_get_bundles_json())
            return 0

        available_bundles = _get_bundle_list()
        if not available_bundles:
            emitter.publish("No available diagnostic bundles")
            return 0
        emitter.publish("Available diagnostic bundles:")
        for available_bundle in sorted(available_bundles,
                                       key=lambda t: t[0]):
            emitter.publish('{} {}'.format(available_bundle[0],
                                           sizeof_fmt(available_bundle[1])))
        return 0
    elif status:
        url = urllib.parse.urljoin(DIAGNOSTICS_BASE_URL, 'status/all')
        bundle_response = _do_diagnostics_request(url, 'GET')
        if json:
            emitter.publish(bundle_response)
            return 0

        for host, props in sorted(bundle_response.items()):
            emitter.publish(host)
            for key, value in sorted(props.items()):
                emitter.publish('  {}: {}'.format(key, value))
            emitter.publish('\n')
        return 0
    elif cancel:
        url = urllib.parse.urljoin(DIAGNOSTICS_BASE_URL, 'cancel')
        bundle_response = _do_diagnostics_request(url, 'POST')
        if json:
            emitter.publish(bundle_response)
            return 0

        if 'status' not in bundle_response:
            raise DCOSException(
                'Request to cancel a diagnostics job {} returned '
                'an unexpected response {}'.format(url, bundle_response))

        emitter.publish(bundle_response['status'])
        return 0
    else:
        raise DCOSException(
            'Must specify one of list_bundles, status, cancel')


@diagnostics_error
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


def _do_diagnostics_request(url, method, **kwargs):
    """
    Make HTTP request and expect a JSON response.

    :param url: url
    :type url: string
    :param method: HTTP method, GET or POST
    :type method: string
    :return: bundle JSON response
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
        bundle_response = util.load_jsons(data.decode('utf-8'))
        return bundle_response
    except DCOSException:
        raise


def _bundle_download(bundle, location):
    """
    Download diagnostics bundle.

    :param bundle: bundle file name.
    :type bundle: string
    :param location: location on a local filesystem.
    :type location: string
    :return: status code
    :rtype: int
    """

    # make sure the requested bundle exists
    bundle_size = 0
    for available_bundle in _get_bundle_list():
        # _get_bundle_list must return a list of tuples
        # where first element is file name and second is its size.
        if len(available_bundle) != 2:
            raise DCOSException(
                'Request to get a list of diagnostic bundles returned an '
                'unexpected response: {}'.format(available_bundle))

        # available_bundle[0] is a file name
        # available_bundle[1] is a file size
        if available_bundle[0] == bundle:
            bundle_size = available_bundle[1]

    url = urllib.parse.urljoin(DIAGNOSTICS_BASE_URL, 'serve/' + bundle)
    bundle_location = os.path.join(os.getcwd(), bundle)
    if location:
        if os.path.isdir(location):
            bundle_location = os.path.join(location, bundle)
        else:
            bundle_location = location

    if bundle_size > BUNDLE_WARN_SIZE:
        msg = ('Diagnostics bundle size is {}, '
               'are you sure you want to download it?')
        if not confirm(msg.format(sizeof_fmt(bundle_size)), False):
            return 1

    r = _do_request(url, 'GET', stream=True)
    try:
        with open(bundle_location, 'wb') as f:
            for chunk in r.iter_content(1024):
                f.write(chunk)
    except Exception as e:
        raise DCOSException(e)
    emitter.publish('Diagnostics bundle downloaded to ' + bundle_location)
    return 0


def _bundle_delete(bundle):
    """
    Delete a bundle

    :param bundle: file name
    :type: str
    :return: status code
    :rtype: int
    """

    _check_3dt_version()
    url = urllib.parse.urljoin(
        DIAGNOSTICS_BASE_URL, 'delete/' + bundle)
    response = _do_diagnostics_request(url, 'POST')

    if 'status' not in response:
        raise DCOSException(
            'Request to delete the diagnostics bundle {} returned an '
            'unexpected response {}'.format(url, response))

    emitter.publish(response['status'])
    return 0


def _bundle_create(nodes):
    """
    Create a diagnostics bundle.

    :param nodes: a list of nodes to collect the logs from.
    :type nodes: list
    :returns: process return code
    :rtype: int
    """

    _check_3dt_version()
    url = urllib.parse.urljoin(DIAGNOSTICS_BASE_URL, 'create')
    response = _do_diagnostics_request(url,
                                       'POST',
                                       json={'nodes': nodes})

    if ('status' not in response or 'extra' not in response
            or 'bundle_name' not in response['extra']):
        raise DCOSException(
            'Request to create a diagnostics bundle {} returned an '
            'unexpected response {}'.format(url, response))

    emitter.publish('\n{}, available bundle: {}'.format(
        response['status'],
        response['extra']['bundle_name']))
    return 0


def _dns_lookup(dns_name, json_):
    """
    Returns the IP of the dns-name in the cluster

    :param dns_name: dns name to lookup
    :type dns_name: string
    :param json_: If true, output json.
        Otherwise, output a human readable table.
    :type json_: bool
    """

    ips = mesos.MesosDNSClient().hosts(dns_name)

    if json_:
        emitter.publish(ips)
    else:
        table = tables.dns_table(ips)
        output = six.text_type(table)
        if output:
            emitter.publish(output)

    return 0


def _info():
    """Print node cli information.

    :returns: process return code
    :rtype: int
    """

    emitter.publish(default_command_info("node"))
    return 0


def _list(json_, extra_field_names):
    """List DC/OS nodes

    :param json_: If true, output json.
        Otherwise, output a human readable table.
    :type json_: bool
    :param extra_field_names: List of additional field names to include in
        table output
    :type extra_field_names: [str]
    :returns: process return code
    :rtype: int
    """

    client = mesos.DCOSClient()
    masters = mesos.MesosDNSClient().masters()
    master_state = client.get_master_state()
    slaves = client.get_state_summary()['slaves']
    for master in masters:
        if master['ip'] == master_state['hostname']:
            master['type'] = 'master (leader)'
            region, zone = util.get_fault_domain(master_state)
            master['region'] = region
            master['zone'] = zone
            for key in ('id', 'pid', 'version'):
                master[key] = master_state.get(key)
        else:
            master['type'] = 'master'
    for slave in slaves:
        region, zone = util.get_fault_domain(slave)
        slave['type'] = 'agent'
        slave['region'] = region
        slave['zone'] = zone
    nodes = masters + slaves
    if json_:
        emitter.publish(nodes)
    else:
        for extra_field_name in extra_field_names:
            field_name = extra_field_name.split(':')[-1]
            if len(slaves) > 0:
                try:
                    tables._dotted_itemgetter(field_name)(slaves[0])
                except KeyError:
                    emitter.publish(errors.DefaultError(
                        'Field "%s" is invalid.' % field_name))
                    return
        table = tables.node_table(nodes, extra_field_names)
        output = six.text_type(table)
        if output:
            emitter.publish(output)
        else:
            emitter.publish(errors.DefaultError('No agents found.'))


def _log(follow, lines, leader, slave, component, filters):
    """ Prints the contents of leader and slave logs.

    :param follow: same as unix tail's -f
    :type follow: bool
    :param lines: number of lines to print
    :type lines: int
    :param leader: whether to print the leading master's log
    :type leader: bool
    :param slave: the slave ID to print
    :type slave: str | None
    :param component: DC/OS component name
    :type component: string
    :param filters: a list of filters ["key:value", ...]
    :type filters: list
    :returns: process return code
    :rtype: int
    """

    if not (leader or slave):
        raise DCOSException('You must choose one of --leader or --mesos-id.')

    if lines is None:
        lines = 10

    lines = util.parse_int(lines)

    if log.dcos_log_enabled(version=2):
        _dcos_log_v2(follow, lines, leader, slave, component, filters)
        return 0

    if not log.has_journald_capability():
        if component or filters:
            raise DCOSException('--component or --filter is not '
                                'supported by files API')

        # fall back to mesos files API.
        mesos_files = _mesos_files(leader, slave)
        log.log_files(mesos_files, follow, lines)
        return 0

    # dcos-log does not support logs from leader and agent.
    if leader and slave:
        raise DCOSException(
            'You must choose one of --leader or --mesos-id.')

    # if journald logging enabled.
    _dcos_log(follow, lines, leader, slave, component, filters)
    return 0


def _metrics(summary, mesos_id, json_):
    """ Get metrics from the specified agent.

    :param summary: summarise output if true, output all if false
    :type summary: bool
    :param mesos_id: mesos node id
    :type mesos_id: str
    :param json_: print raw JSON
    :type json_: bool
    :returns: Process status
    :rtype: int
    """

    endpoint = '/system/v1/agent/{}/metrics/v0/node'.format(mesos_id)

    dcos_url = config.get_config_val('core.dcos_url').rstrip('/')
    if not dcos_url:
        raise config.missing_config_exception(['core.dcos_url'])

    url = dcos_url + endpoint
    return metrics.print_node_metrics(url, summary, json_)


def _get_slave_ip(slave):
    """ Get an agent IP address based on mesos id.
        If slave parameter is empty, the function will return

    :param slave: mesos node id
    :type slave: str
    :return: node ip address
    :rtype: str
    """
    if not slave:
        return

    summary = mesos.DCOSClient().get_state_summary()
    if 'slaves' not in summary:
        raise DCOSException(
            'Invalid summary report. '
            'Missing field `slaves`. {}'.format(summary))

    for s in summary['slaves']:
        if 'hostname' not in s or 'id' not in s:
            raise DCOSException(
                'Invalid summary report. Missing field `id` '
                'or `hostname`. {}'.format(summary))

        if s['id'] == slave:
            return s['hostname']

    raise DCOSException('Agent `{}` not found'.format(slave))


def _list_components(leader, slave, use_json):
    """ List components for a leader or slave_ip node

    :param leader: use leader ip flag
    :type leader: bool
    :param slave_ip: agent ip address
    :type slave_ip: str
    :param use_json: print components in json format
    :type use_json: bool
    """
    if not (leader or slave):
        raise DCOSException('--leader or --mesos-id must be provided')

    if leader and slave:
        raise DCOSException(
            'Unable to use leader and mesos id at the same time')

    slave_ip = _get_slave_ip(slave)
    if slave_ip:
        print_components(slave_ip, use_json)
        return

    leaders = mesos.MesosDNSClient().hosts('leader.mesos')
    if len(leaders) != 1:
        raise DCOSException('Expecting one leader. Got {}'.format(leaders))

    if 'ip' not in leaders[0]:
        raise DCOSException(
            'Invalid leader response, missing field `ip`. '
            'Got {}'.format(leaders[0]))

    print_components(leaders[0]['ip'], use_json)


def print_components(ip, use_json):
    """ Print components for a given node ip.
        The data is taked from 3dt endpoint:
        /system/health/v1/nodes/<ip>/units

    :param ip: DC/OS node ip address
    :type ip: str
    :param use_json: print components in json format
    :type use_json: bool
    """
    dcos_url = config.get_config_val('core.dcos_url').rstrip("/")
    if not dcos_url:
        raise config.missing_config_exception(['core.dcos_url'])

    url = dcos_url + '/system/health/v1/nodes/{}/units'.format(ip)
    response = http.get(url).json()
    if 'units' not in response:
        raise DCOSException(
            'Invalid response. Missing field `units`. {}'.format(response))

    if use_json:
        emitter.publish(response['units'])
    else:
        for component in response['units']:
            emitter.publish(component['id'])


def _get_unit_type(unit_name):
    """ Get the full unit name including the type postfix
        or default to service.

    :param unit_name: unit name with or without type
    :type unit_name: str
    :return: unit name with type
    :rtype: str
    """
    if not unit_name:
        raise DCOSException('Empty systemd unit parameter')

    # https://www.freedesktop.org/software/systemd/man/systemd.unit.html
    unit_types = ['service', 'socket', 'device', 'mount', 'automount',
                  'swap', 'target', 'path', 'timer', 'slice', 'scope']

    for unit_type in unit_types:
        if unit_name.endswith('.{}'.format(unit_type)):
            return unit_name

    return '{}.service'.format(unit_name)


def _build_leader_url(component, version=1):
    """ Return a leader URL based on passed component name.

    :param component: DC/OS component name
    :type component: str
    :param version: Use logging API version. Default to 1.
    :rtype: int
    :return: leader logs url
    :rtype: str
    """

    if version < 1 or version > 2:
        raise DCOSException('valid API versions: 1, 2.Used {}'.format(version))

    leaders_map = {
        'dcos-marathon.service': 'marathon',
        'dcos-mesos-master.service': 'mesos',
    }

    # set default leader to 'mesos' to be consistent with files API
    leader_prefix = 'mesos'
    component_name = ''
    if component:
        component_name = _get_unit_type(component)
        leader_prefix = leaders_map.get(component_name)
        if not leader_prefix:
            raise DCOSException('Component {} does not have a leader'.format(
                component))
    endpoint = '/leader/{}/logs/v{}/'.format(leader_prefix, version)
    if version == 1:
        return endpoint

    if component_name:
        return endpoint + 'component/{}'.format(component_name)
    return endpoint + 'component'


def _dcos_log_v2(follow, lines, leader, slave, component, filters):
    """ Print logs from dcos-log v2 backend.

    :param follow: same as unix tail's -f
    :type follow: bool
    :param lines: number of lines to print
    :type lines: int
    :param leader: whether to print the leading master's log
    :type leader: bool
    :param slave: the slave ID to print
    :type slave: str | None
    :param component: DC/OS component name
    :type component: string
    :param filters: a list of filters ["key:value", ...]
    :type filters: list
    """

    filter_query = ''
    for f in filters:
        key_value = f.split(':')
        if len(key_value) != 2:
            raise DCOSException('Invalid filter parameter {}. '
                                'Must be --filter=key:value'.format(f))
        filter_query += '&filter={}'.format(f)

    endpoint = '/system/v1'
    if leader:
        endpoint += _build_leader_url(component, version=2)
    elif slave:
        endpoint += '/agent/{}/logs/v2/component'.format(slave)
        if component:
            component_with_type = _get_unit_type(component)
            endpoint += '/{}'.format(component_with_type)

    dcos_url = config.get_config_val('core.dcos_url').rstrip("/")
    if not dcos_url:
        raise config.missing_config_exception(['core.dcos_url'])

    # dcos-log v2 required the skip option be a negative integer
    if lines > 0:
        lines *= -1

    url = dcos_url + endpoint + '?skip={}'.format(lines) + filter_query

    if follow:
        return log.follow_logs(url)
    return log.print_logs_range(url)


def _dcos_log(follow, lines, leader, slave, component, filters):
    """ Print logs from dcos-log backend.

    :param follow: same as unix tail's -f
    :type follow: bool
    :param lines: number of lines to print
    :type lines: int
    :param leader: whether to print the leading master's log
    :type leader: bool
    :param slave: the slave ID to print
    :type slave: str | None
    :param component: DC/OS component name
    :type component: string
    :param filters: a list of filters ["key:value", ...]
    :type filters: list
    """

    filter_query = ''
    if component:
        filters.append('_SYSTEMD_UNIT:{}'.format(_get_unit_type(component)))

    for f in filters:
        key_value = f.split(':')
        if len(key_value) != 2:
            raise SystemExit('Invalid filter parameter {}. '
                             'Must be --filter=key:value'.format(f))
        filter_query += '&filter={}'.format(f)

    endpoint = '/system/v1'
    if leader:
        endpoint += _build_leader_url(component)
    elif slave:
        endpoint += '/agent/{}/logs/v1/'.format(slave)

    endpoint_type = 'range'
    if follow:
        endpoint_type = 'stream'

    dcos_url = config.get_config_val('core.dcos_url').rstrip("/")
    if not dcos_url:
        raise config.missing_config_exception(['core.dcos_url'])

    url = (dcos_url + endpoint + endpoint_type +
           '/?skip_prev={}'.format(lines) + filter_query)

    if follow:
        return log.follow_logs(url)
    return log.print_logs_range(url)


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


def _ssh(leader, slave, option, config_file, user, master_proxy, proxy_ip,
         private_ip, command):
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
    :param proxy_ip: If set, SSH-hop from this IP address
    :type proxy_ip: str | None
    :param private_ip: The private IP address of the node we want to SSH to.
    :type private_ip: str | None
    :param command: Command to run on the node
    :type command: str | None
    :rtype: int
    :returns: process return code
    """

    dcos_client = mesos.DCOSClient()

    if leader:
        host = mesos.MesosDNSClient().leader()[0]['ip']
    elif private_ip:
        host = private_ip
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

    ssh_options = ssh_util.get_ssh_options(
        config_file, option, user, proxy_ip, master_proxy)
    cmd = "ssh {0} {1} -- {2}".format(ssh_options, host, command)

    emitter.publish(DefaultError("Running `{}`".format(cmd)))
    if not master_proxy and not proxy_ip:
        emitter.publish(
            DefaultError("If you are running this command from a separate "
                         "network than DC/OS, consider using "
                         "`--master-proxy` or `--proxy-ip`"))

    return subprocess.Subproc().call(cmd, shell=True)


def _decommission(mesos_id):
    try:
        mesos.DCOSClient().mark_agent_gone(mesos_id)
    except errors.DCOSException as e:
        emitter.publish(
            DefaultError("Couldn't mark agent {} as gone :\n\n{}".format(
                mesos_id, e)))
        return 1

    emitter.publish("Agent {} has been marked as gone.".format(mesos_id))
