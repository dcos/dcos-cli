def agent_metrics_node_details_fixture():
    """Agent metrics /node fixture

    :rtype: [dict]
    """

    return [
        {"name": "uptime", "value": 1245, "tags": ""},

        {"name": "cpu.cores", "value": 4, "tags": ""},
        {"name": "cpu.total", "value": "74.94%", "tags": ""},
        {"name": "cpu.user", "value": "15.67%", "tags": ""},
        {"name": "cpu.system", "value": "59.27%", "tags": ""},
        {"name": "cpu.idle", "value": "24.38%", "tags": ""},
        {"name": "cpu.wait", "value": "0.03%", "tags": ""},

        {"name": "load.1min", "value": 2.85, "tags": ""},
        {"name": "load.5min", "value": 2.92, "tags": ""},
        {"name": "load.15min", "value": 2.74, "tags": ""},

        {"name": "filesystem.capacity.total", "value": "5.44GiB",
         "tags": "path: /"},
        {"name": "filesystem.capacity.used", "value": "1.65GiB",
         "tags": "path: /"},
        {"name": "filesystem.capacity.free", "value": "3.53GiB",
         "tags": "path: /"},

        {"name": "memory.total", "value": "14.69GiB", "tags": ""},
        {"name": "memory.free", "value": "12.20GiB", "tags": ""},
        {"name": "memory.buffers", "value": "0.09GiB", "tags": ""},
        {"name": "memory.cached", "value": "1.72GiB", "tags": ""},

        {"name": "swap.total", "value": "0.00GiB", "tags": ""},
        {"name": "swap.free", "value": "0.00GiB", "tags": ""},
        {"name": "swap.used", "value": "0.00GiB", "tags": ""}
    ]


def agent_metrics_node_summary_fixture():
    """Fixture for summary information for node

    :rtype: dict
    """
    return {
        'cpu': '2.85 (74.94%)',
        'mem': '2.49GiB (16.98%)',
        'disk': '1.65GiB (30.30%)'
    }


def agent_metrics_task_details_fixture():
    """Agent metrics /container fixture

    :rtype: [dict]"""

    tags = "executor_id: abc-123, source: consume-cpui.d3df66d3-08dc-11e7-8d53"

    return [
        {"name": "cpus.user.time", "tags": tags, "value": 4902.86},
        {"name": "cpus.system.time", "tags": tags, "value": 8749.93},
        {"name": "cpus.limit", "tags": tags, "value": 0.6},
        {"name": "cpus.throttled.time", "tags": tags, "value": 100.01},
        {"name": "mem.total", "tags": tags, "value": "0.01GiB"},
        {"name": "mem.limit", "tags": tags, "value": "0.16GiB"},
        {"name": "disk.limit", "tags": tags, "value": "0.00GiB"},
        {"name": "disk.used", "tags": tags, "value": "0.00GiB"},
    ]
