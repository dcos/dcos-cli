import contextlib

from dcos import emitting, http, util
from dcos.errors import DCOSException
from dcoscli import tables

logger = util.get_logger(__name__)
emitter = emitting.FlatEmitter()


def _fetch_node_metrics(url):
    """Retrieve the metrics data from `dcos-metrics`' `node` endpoint.

    :param url: `dcos-metrics` `node` endpoint
    :type url: str
    """
    with contextlib.closing(http.get(url)) as r:

        # No need to guard against 204; metrics should never be empty
        if r.status_code != 200:
            raise DCOSException(
                'Error getting metrics. Url: {};'
                'response code: {}'.format(url, r.status_code))

        return r.json().get('datapoints', [])


def print_node_metrics_json(url):
    """Retrieve and print the raw output from `dcos-metrics`' `node` endpoint.

    :param url: `dcos-metrics` `node` endpoint
    :type url: str
    """
    datapoints = _fetch_node_metrics(url)
    return emitter.publish(datapoints)


def print_node_metrics_summary(url):
    """Retrieve and pretty-print key fields from the `dcos-metrics`' `node`
    endpoint.

    :param url: `dcos-metrics` `node` endpoint
    :type url: str
    """

    datapoints = _fetch_node_metrics(url)

    table = tables.metrics_summary_table(datapoints)
    return emitter.publish(table)


def print_node_metrics_fields(url, fields):
    """Retrieve and pretty-print selected fields from the `dcos-metrics`' `node`
    endpoint.

    :param url: `dcos-metrics` `node` endpoint
    :type url: str
    :param fields: a list of field names
    :type fields: [str]
    """

    all_datapoints = _fetch_node_metrics(url)

    names = [d['name'] for d in all_datapoints]
    indexed_datapoints = dict(zip(names, all_datapoints))

    datapoints = []
    for field in sorted(fields):
        if field in names:
            datapoints.append(indexed_datapoints[field])
        else:
            raise DCOSException(
                'Could not find metrics data for field: {}'.format(field))

    table = tables.metrics_fields_table(datapoints)
    return emitter.publish(table)
