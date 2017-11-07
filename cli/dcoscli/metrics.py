import contextlib
import json

from dcos import emitting, http, util
from dcos.errors import DCOSException, DCOSHTTPException
from dcoscli import tables

logger = util.get_logger(__name__)
emitter = emitting.FlatEmitter()


class EmptyMetricsException(DCOSException):
    def __init__(self):
        super().__init__('No metrics found')


def _gib(n):
    return n * pow(2, -30)


def _percentage(dividend, divisor):
    if divisor > 0:
        return dividend / divisor * 100
    return 0


def _fetch_metrics_datapoints(url):
    """Retrieve the metrics data from any `dcos-metrics` endpoint.

    :param url: `dcos-metrics` endpoint
    :type url: str
    :returns: List of metrics datapoints
    :rtype: [dict]
    """
    with contextlib.closing(http.get(url)) as r:

        if r.status_code == 204:
            raise EmptyMetricsException()

        if r.status_code != 200:
            raise DCOSHTTPException(r)

        return r.json().get('datapoints', [])


def _get_datapoint(datapoints, name, tags=None):
    """Find a specific datapoint by name and tags

    :param datapoints: a list of datapoints
    :type datapoints: [dict]
    :param name: the name of the required datapoint
    :type name: str
    :param tags: required tags by key and value
    :type tags: dict
    :return: a matching datapoint
    :rtype: dict
    """
    for datapoint in datapoints:
        if datapoint['name'] == name:
            if tags is None:
                return datapoint

            dtags = datapoint.get('tags', {})
            tag_match = True
            for k, v in tags.items():
                tag_match = tag_match and dtags.get(k) == v
            if tag_match:
                return datapoint


def _get_datapoint_value(datapoints, name, tags=None):
    """Safely return only the value from a datapoint, defaulting to 0.

    :param datapoints: a list of datapoints
    :type datapoints: [dict]
    :param name: the name of the required datapoint
    :type name: str
    :param tags: required tags by key and value
    :type tags: dict
    :return: a matching datapoint
    :rtype: float
    """
    datapoint = _get_datapoint(datapoints, name, tags)
    if datapoint is not None:
        return datapoint.get('value', 0.0)

    return 0.0


def _node_summary_json(datapoints):
    """Filters datapoints down to CPU, memory and root disk space fields.

    :param datapoints: a list of datapoints
    :type datapoints: [dict]
    :return: JSON data
    :rtype: str
    """
    summary_datapoints = [
        _get_datapoint(datapoints, 'cpu.total'),
        _get_datapoint(datapoints, 'memory.total'),
        _get_datapoint(datapoints, 'filesystem.capacity.used', {'path': '/'})
    ]
    return json.dumps(summary_datapoints)


def _node_summary_data(datapoints):
    """Extracts CPU, memory and root disk space fields from node datapoints.

    :param datapoints: a list of raw datapoints
    :type datapoints: [dict]
    :return: a dictionary of summary fields
    :rtype: dict
    """

    cpu_used = _get_datapoint_value(datapoints, 'load.1min')
    cpu_used_pc = _get_datapoint_value(datapoints, 'cpu.total')

    mem_total = _get_datapoint_value(datapoints, 'memory.total')
    mem_free = _get_datapoint_value(datapoints, 'memory.free')
    mem_used = mem_total - mem_free
    mem_used_pc = _percentage(mem_used, mem_total)

    disk_total = _get_datapoint_value(
        datapoints, 'filesystem.capacity.total', {'path': '/'})
    disk_free = _get_datapoint_value(
        datapoints, 'filesystem.capacity.used', {'path': '/'})
    disk_used = disk_total - disk_free
    disk_used_pc = _percentage(disk_used, disk_total)

    return {
        'cpu': '{:0.2f} ({:0.2f}%)'.format(cpu_used, cpu_used_pc),
        'mem': '{:0.2f}GiB ({:0.2f}%)'.format(_gib(mem_used), mem_used_pc),
        'disk': '{:0.2f}GiB ({:0.2f}%)'.format(_gib(disk_used), disk_used_pc)
    }


def _task_summary_json(datapoints):
    """Filters datapoints down to CPU, memory and disk space fields.

    :param datapoints: a list of datapoints
    :type datapoints: [dict]
    :return: JSON data
    :rtype: str
    """
    summary_datapoints = [
        _get_datapoint(datapoints, 'cpus.user.time'),
        _get_datapoint(datapoints, 'mem.total'),
        _get_datapoint(datapoints, 'disk.used')
    ]
    return json.dumps(summary_datapoints)


def _task_summary_data(datapoints):
    """Extracts CPU, memory and root disk space fields from task datapoints.

    :param datapoints: a list of raw datapoints
    :type datapoints: [dict]
    :return: a dictionary of summary fields
    :rtype: dict
    """

    cpu_user = _get_datapoint_value(datapoints, 'cpus.user.time')
    cpu_system = _get_datapoint_value(datapoints, 'cpus.system.time')
    cpu_throttled = _get_datapoint_value(datapoints, 'cpus.throttled.time')
    cpu_used = cpu_user + cpu_system
    cpu_total = cpu_used + cpu_throttled
    cpu_used_pc = _percentage(cpu_used, cpu_total)

    mem_total = _get_datapoint_value(datapoints, 'mem.limit')
    mem_used = _get_datapoint_value(datapoints, 'mem.total')
    mem_used_pc = _percentage(mem_used, mem_total)

    disk_total = _get_datapoint_value(datapoints, 'disk.used')
    disk_used = _get_datapoint_value(datapoints, 'disk.limit')
    disk_used_pc = _percentage(disk_used, disk_total)

    return {
        'cpu': '{:0.2f} ({:0.2f}%)'.format(cpu_used, cpu_used_pc),
        'mem': '{:0.2f}GiB ({:0.2f}%)'.format(_gib(mem_used), mem_used_pc),
        'disk': '{:0.2f}GiB ({:0.2f}%)'.format(_gib(disk_used), disk_used_pc)
    }


def _format_datapoints(datapoints):
    """Format raw datapoints for output by making values human-readable
    according to their unit and formatting tags.

    :param datapoints: a list of datapoints
    :type datapoints: [dict]
    :return: a list of formatted datapoints
    :rtype: [dict]
    """

    def _format_tags(tags):
        if tags is None:
            return ''
        pairs = []
        for k, v in tags.items():
            pairs.append('{}: {}'.format(k, v))
        return ', '.join(pairs)

    def _format_value(v, u):
        if u == 'bytes':
            return '{:0.2f}GiB'.format(_gib(v))
        if u == 'percent':
            return '{:0.2f}%'.format(v)
        if type(v) == float:
            return '{:0.2f}'.format(v)
        return v

    formatted_datapoints = []
    for d in datapoints:
        formatted_datapoints.append({
            'name': d['name'],
            'value': _format_value(d['value'], d['unit']),
            'tags': _format_tags(d.get('tags'))
        })

    return formatted_datapoints


def print_node_metrics(url, summary, json_):
    """Retrieve and pretty-print key fields from the `dcos-metrics`' `node`
    endpoint.

    :param url: `dcos-metrics` `node` endpoint
    :type url: str
    :param summary: print summary if true, or all fields if false
    :type summary: bool
    :param json_: print json list if true
    :type json_: bool
    :returns: Process status
    :rtype: int
    """

    datapoints = _fetch_metrics_datapoints(url)

    if summary:
        if json_:
            return emitter.publish(_node_summary_json(datapoints))
        table = tables.metrics_summary_table(_node_summary_data(datapoints))
    else:
        if json_:
            return emitter.publish(datapoints)
        table = tables.metrics_details_table(_format_datapoints(datapoints))

    return emitter.publish(table)


def print_task_metrics(url, app_url, summary, json_):
    """Retrieve and pretty-print fields from the `dcos-metrics`' `containers/id`
    endpoint and `containers/id/app` endpoint.

    :param url: `dcos-metrics` `containers/id` endpoint
    :type url: str
    :param app_url: `dcos-metrics` `containers/id/app` endpoint
    :type app_url: str
    :param json_: print json list if true
    :type json_: bool
    :param summary: print summary if true, or all fields if false
    :type summary: bool
    :return: Process status
    :rtype: int
    """

    container_datapoints = []
    app_datapoints = []

    # In the case of an executor, app data may exist when
    # container data does not.
    try:
        container_datapoints = _fetch_metrics_datapoints(url)
    except EmptyMetricsException:
        pass

    app_datapoints = _fetch_metrics_datapoints(app_url)
    datapoints = container_datapoints + app_datapoints

    if summary:
        if json_:
            return emitter.publish(_task_summary_json(datapoints))
        table = tables.metrics_summary_table(_task_summary_data(datapoints))
    else:
        if json_:
            return emitter.publish(datapoints)
        table = tables.metrics_details_table(_format_datapoints(datapoints),
                                             False)

    return emitter.publish(table)
