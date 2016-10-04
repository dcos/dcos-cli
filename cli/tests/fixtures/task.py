from dcos.mesos import Task


def task_fixture():
    """ Task fixture

    :rtype: Task
    """

    task = Task({
        "executor_id": "",
        "framework_id": "20150502-231327-16842879-5050-3889-0000",
        "id": "test-app.d44dd7f2-f9b7-11e4-bb43-56847afe9799",
        "labels": [],
        "name": "test-app",
        "resources": {
            "cpus": 0.1,
            "disk": 0.0,
            "mem": 16.0,
            "ports": "[31651-31651]"
        },
        "slave_id": "20150513-185808-177048842-5050-1220-S0",
        "state": "TASK_RUNNING",
        "statuses": [
            {
                "container_status": {
                    "network_infos": [
                        {
                            "ip_addresses": [
                                {
                                    "ip_address": "127.17.8.12"
                                }
                            ]
                        }
                    ]
                },
                "state": "TASK_RUNNING",
                "timestamp": 1431552866.52692
            }
        ]
    }, None)

    return task


def browse_fixture():
    return [
        {u'uid': u'root',
         u'mtime': 1437089500,
         u'nlink': 1,
         u'mode': u'-rw-r--r--',
         u'gid': u'root',
         u'path': (u'/var/lib/mesos/slave/slaves/' +
                   u'20150716-183440-1695027628-5050-2710-S0/frameworks/' +
                   u'20150716-183440-1695027628-5050-2710-0000/executors/' +
                   u'chronos.8810d396-2c09-11e5-af1a-080027d3e806/runs/' +
                   u'aaecec57-7c7c-4030-aca3-d7aac2f9fd29/stderr'),
         u'size': 4507},

        {u'uid': u'root',
         u'mtime': 1437089604,
         u'nlink': 1,
         u'mode': u'-rw-r--r--',
         u'gid': u'root',
         u'path': (u'/var/lib/mesos/slave/slaves/' +
                   u'20150716-183440-1695027628-5050-2710-S0/frameworks/' +
                   u'20150716-183440-1695027628-5050-2710-0000/executors/' +
                   u'chronos.8810d396-2c09-11e5-af1a-080027d3e806/runs/' +
                   u'aaecec57-7c7c-4030-aca3-d7aac2f9fd29/stdout'),
         u'size': 353857}
    ]
