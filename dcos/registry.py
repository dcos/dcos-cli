
from __future__ import absolute_import, print_function

try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

# XXX - This command is used for every completion right now. It should
# take a very short time to complete.
def list():
    return [
        OrderedDict([
            ("name", "marathon"),
            ("version", "0.7.5")
        ]),
        OrderedDict([
            ("name", "spark"),
            ("version", "0.1.1")
        ]),
        OrderedDict([
            ("name", "casandra"),
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
            ("name", "HDFS"),
            ("version", "0.1.1")
        ]),
        OrderedDict([
            ("name", "DEIS"),
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
            ("name", "ElasticSearch"),
            ("version", "0.1.1")
        ]),
        OrderedDict([
            ("name", "Aurora"),
            ("version", "0.1.1")
        ]),
        OrderedDict([
            ("name", "Storm"),
            ("version", "0.1.1")
        ])
    ]

def names():
    return map(lambda x: x["name"], list())
