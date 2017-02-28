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


def print_node_metrics(url, summary, json):
    """Retrieve and pretty-print key fields from the `dcos-metrics`' `node`
    endpoint.

    :param url: `dcos-metrics` `node` endpoint
    :type url: str
    :param summary: print summary if true, or all fields if false
    :type summary: bool
    :param json: print json list if true
    :type json: bool
    :returns: Process status
    :rtype: int
    """

    datapoints = _fetch_node_metrics(url)

    if json:
        return emitter.publish(datapoints)

    if summary:
        table = tables.metrics_summary_table(datapoints)
    else:
        table = tables.metrics_details_table(datapoints)

    return emitter.publish(table)
