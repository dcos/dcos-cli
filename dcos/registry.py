
from __future__ import absolute_import, print_function

try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

from .cfg import CURRENT as CFG

# XXX - This command is used for every completion right now. It should
# take a very short time to complete.
def list():
    return [
        OrderedDict([
            ("name", "spark"),
            ("version", "0.1.1")
        ]),
        OrderedDict([
            ("name", "cassandra"),
            ("version", "0.1.1")
        ]),
        OrderedDict([
            ("name", "kafka"),
            ("version", "0.1.1")
        ]),
        OrderedDict([
            ("name", "kubernetes"),
            ("version", "0.1.1")
        ]),
        OrderedDict([
            ("name", "chronos"),
            ("version", "0.1.1")
        ]),
        OrderedDict([
            ("name", "jenkins"),
            ("version", "0.1.1")
        ]),
        OrderedDict([
            ("name", "spark"),
            ("version", "0.1.1")
        ]),
        OrderedDict([
            ("name", "hdfs"),
            ("version", "0.1.1")
        ]),
        OrderedDict([
            ("name", "deis"),
            ("version", "0.1.1")
        ]),
        OrderedDict([
            ("name", "hadoop"),
            ("version", "0.1.1")
        ]),
        OrderedDict([
            ("name", "yarn"),
            ("version", "0.1.1")
        ]),
        OrderedDict([
            ("name", "accumulo"),
            ("version", "0.1.1")
        ]),
        OrderedDict([
            ("name", "elasticsearch"),
            ("version", "0.1.1")
        ]),
        OrderedDict([
            ("name", "aurora"),
            ("version", "0.1.1")
        ]),
        OrderedDict([
            ("name", "storm"),
            ("version", "0.1.1")
        ])
    ]

def names():
    return map(lambda x: x["name"], list())

def installed():
    return CFG["installed"]
