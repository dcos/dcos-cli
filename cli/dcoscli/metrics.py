import contextlib
from collections import OrderedDict

from dcos import emitting, http, util
from dcos.errors import DCOSException
from dcoscli import tables

logger = util.get_logger(__name__)
emitter = emitting.FlatEmitter()


def print_node_metrics_table(url):
    """Retrieve, parse, and pretty-print the output from `dcos-metrics`' `node`
    endpoint.

    :param url: `dcos-metrics` `node` endpoint
    :type url: str
    """

    with contextlib.closing(http.get(url)) as r:

        if r.status_code != 200:
            raise DCOSException(
                'Error getting logs. Url: {};'
                'response code: {}'.format(url, r.status_code))

        fields = OrderedDict([
            ('NAME', lambda a: a['name']),
            ('VALUE', lambda a: a['value'])
        ])
        table = tables.table(fields, r.json().get('datapoints', []))
        return emitter.publish(table)
