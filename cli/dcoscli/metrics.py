import contextlib
from collections import OrderedDict

from dcos import emitting, http, util
from dcos.errors import DCOSException
from dcoscli import tables

logger = util.get_logger(__name__)
emitter = emitting.FlatEmitter()


def _fetch_node_metrics(url):
    """Retrieve the output from`dcos-metrics`' `node` endpoint.

    :param url: `dcos-metrics` `node` endpoint
    :type url: str
    """
    with contextlib.closing(http.get(url)) as r:

        # No need to guard against 204; metrics should never be empty
        if r.status_code != 200:
            raise DCOSException(
                'Error getting metrics. Url: {};'
                'response code: {}'.format(url, r.status_code))

        return r.json()


def print_node_metrics_table(url):
    """Retrieve and pretty-print the output from `dcos-metrics`' `node`
    endpoint.

    :param url: `dcos-metrics` `node` endpoint
    :type url: str
    """
    node_json = _fetch_node_metrics(url)
    datapoints = node_json.get('datapoints', [])

    fields = OrderedDict([
        ('NAME', lambda a: a['name']),
        ('VALUE', lambda a: a['value'])
    ])
    table = tables.table(fields, datapoints)
    return emitter.publish(table)
