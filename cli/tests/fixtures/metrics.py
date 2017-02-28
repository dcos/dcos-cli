def agent_metrics_node_fixture():
    """Agent metrics /node fixture

    :rtype: dict
    """

    return {
        "datapoints": [

            {"name": "cpu.cores", "value": 4, "unit": "count",
             "timestamp": "2017-02-25T00:06:28.51132503Z"},
            {"name": "cpu.total", "value": 74.94,
             "unit": "count",
             "timestamp": "2017-02-25T00:06:28.51132503Z"},
            {"name": "cpu.user", "value": 15.67, "unit": "count",
             "timestamp": "2017-02-25T00:06:28.51132503Z"},
            {"name": "cpu.system", "value": 59.27,
             "unit": "count",
             "timestamp": "2017-02-25T00:06:28.51132503Z"},
            {"name": "cpu.idle", "value": 24.38, "unit": "count",
             "timestamp": "2017-02-25T00:06:28.51132503Z"},
            {"name": "cpu.wait", "value": 0.03, "unit": "count",
             "timestamp": "2017-02-25T00:06:28.51132503Z"},
            {"name": "load.1min", "value": 2.85, "unit": "count",
             "timestamp": "2017-02-25T00:06:28.511847442Z"},
            {"name": "load.5min", "value": 2.92, "unit": "count",
             "timestamp": "2017-02-25T00:06:28.511847442Z"},
            {"name": "load.15min", "value": 2.74,
             "unit": "count",
             "timestamp": "2017-02-25T00:06:28.511847442Z"},

            {"name": "filesystem.capacity.total",
             "value": 5843333120, "unit": "bytes",
             "timestamp": "2017-02-25T00:06:28.511894716Z",
             "tags": {"path": "/"}},
            {"name": "filesystem.capacity.used",
             "value": 1770651648, "unit": "bytes",
             "timestamp": "2017-02-25T00:06:28.511894716Z",
             "tags": {"path": "/"}},
            {"name": "filesystem.capacity.free",
             "value": 3789721600, "unit": "bytes",
             "timestamp": "2017-02-25T00:06:28.511894716Z",
             "tags": {"path": "/"}},

            {"name": "memory.total", "value": 15773708288,
             "unit": "bytes",
             "timestamp": "2017-02-25T00:06:28.512323579Z"},
            {"name": "memory.free", "value": 13095510016,
             "unit": "bytes",
             "timestamp": "2017-02-25T00:06:28.512323579Z"},
            {"name": "memory.buffers", "value": 94969856,
             "unit": "bytes",
             "timestamp": "2017-02-25T00:06:28.512323579Z"},
            {"name": "memory.cached", "value": 1851731968,
             "unit": "bytes",
             "timestamp": "2017-02-25T00:06:28.512323579Z"},

            {"name": "swap.total", "value": 0, "unit": "bytes",
             "timestamp": "2017-02-25T00:06:28.512323579Z"},
            {"name": "swap.free", "value": 0, "unit": "bytes",
             "timestamp": "2017-02-25T00:06:28.512323579Z"},
            {"name": "swap.used", "value": 0, "unit": "bytes",
             "timestamp": "2017-02-25T00:06:28.512323579Z"}
        ]
    }

