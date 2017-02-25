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


def print_node_metrics_table(url):
    """Retrieve and pretty-print key fields from the `dcos-metrics`' `node`
    endpoint.

    :param url: `dcos-metrics` `node` endpoint
    :type url: str
    """

    datapoints = _fetch_node_metrics(url)

    table = tables.metrics_summary_table(datapoints)
    return emitter.publish(table)
