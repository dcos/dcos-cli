import contextlib

from dcos import emitting, http, util
from dcos.errors import DCOSException, DCOSHTTPException
from dcoscli import tables

logger = util.get_logger(__name__)
emitter = emitting.FlatEmitter()


def _fetch_node_metrics(url):
    """Retrieve the metrics data from `dcos-metrics`' `node` endpoint.

    :param url: `dcos-metrics` `node` endpoint
    :type url: str
    :returns: List of metrics datapoints
    :rtype: [dict]
    """
    with contextlib.closing(http.get(url)) as r:

        if r.status_code == 204:
            raise DCOSException('No metrics found')

        if r.status_code != 200:
            raise DCOSHTTPException(r)

        return r.json().get('datapoints', [])


def _filter_datapoints(all_datapoints, fields):
    names = [d['name'] for d in all_datapoints]
    indexed_datapoints = dict(zip(names, all_datapoints))

    datapoints = []
    for field in sorted(fields):
        if field in names:
            datapoints.append(indexed_datapoints[field])
        else:
            raise DCOSException(
                'Could not find metrics data for field: {}'.format(field))

    return datapoints


def print_node_metrics(url, fields, json):
    """Retrieve and pretty-print key fields from the `dcos-metrics`' `node`
    endpoint.

    :param url: `dcos-metrics` `node` endpoint
    :type url: str
    :param fields: list of metrics fields to print
    :type fields: [str]
    :param json: print json list if true
    :type json: bool
    :returns: Process status
    :rtype: int
    """

    datapoints = _fetch_node_metrics(url)

    if json:
        return emitter.publish(datapoints)

    if len(fields) > 0:
        filtered_datapoints = _filter_datapoints(datapoints, fields)
        table = tables.metrics_fields_table(filtered_datapoints)
    else:
        table = tables.metrics_summary_table(datapoints)

    return emitter.publish(table)
