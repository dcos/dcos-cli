from dcos.mesos import Framework


def framework_fixture():
    """ Framework fixture

    :rtype: Framework
    """

    return Framework({
        "active": True,
        "capabilities": [],
        "checkpoint": True,
        "completed_tasks": [],
        "executors": [],
        "failover_timeout": 604800.0,
        "hostname": "mesos.vm",
        "id": "20150502-231327-16842879-5050-3889-0000",
        "name": "marathon",
        "offered_resources": {
            "cpus": 0.0,
            "disk": 0.0,
            "mem": 0.0,
            "ports": "[1379-1379, 10000-10000]"
        },
        "offers": [],
        "pid":
        "scheduler-a58cd5ba-f566-42e0-a283-b5f39cb66e88@172.17.8.101:55130",
        "registered_time": 1431543498.31955,
        "reregistered_time": 1431543498.31959,
        "resources": {
            "cpus": 0.2,
            "disk": 0.0,
            "mem": 32.0,
            "ports": "[1379-1379, 10000-10000]"
        },
        "role": "*",
        "tasks": [],
        "unregistered_time": 0.0,
        "used_resources": {
            "cpus": 0.2,
            "disk": 0.0,
            "mem": 32.0,
            "ports": "[1379-1379, 10000-10000]"
        },
        "user": "root",
        "webui_url": "http://mesos:8080"
    }, None)
