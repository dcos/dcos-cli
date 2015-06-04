def app_fixture():
    """ Marathon app fixture.

    :rtype: dict
    """

    return {
        "acceptedResourceRoles": None,
        "args": None,
        "backoffFactor": 1.15,
        "backoffSeconds": 1,
        "cmd": "sleep 1000",
        "constraints": [],
        "container": None,
        "cpus": 0.1,
        "dependencies": [],
        "deployments": [],
        "disk": 0.0,
        "env": {},
        "executor": "",
        "healthChecks": [],
        "id": "/test-app",
        "instances": 1,
        "labels": {
            "PACKAGE_ID": "test-app",
            "PACKAGE_VERSION": "1.2.3"
        },
        "maxLaunchDelaySeconds": 3600,
        "mem": 16.0,
        "ports": [
            10000
        ],
        "requirePorts": False,
        "storeUrls": [],
        "tasksHealthy": 0,
        "tasksRunning": 1,
        "tasksStaged": 0,
        "tasksUnhealthy": 0,
        "upgradeStrategy": {
            "maximumOverCapacity": 1.0,
            "minimumHealthCapacity": 1.0
        },
        "uris": [],
        "user": None,
        "version": "2015-05-28T21:21:05.064Z"
    }


def deployment_fixture():
    """ Marathon deployment fixture.

    :rtype: dict
    """

    return {
        "affectedApps": [
            "/cassandra/dcos"
        ],
        "currentActions": [
            {
                "action": "ScaleApplication",
                "app": "/cassandra/dcos"
            }
        ],
        "currentStep": 2,
        "id": "bebb8ffd-118e-4067-8fcb-d19e44126911",
        "steps": [
            [
                {
                    "action": "StartApplication",
                    "app": "/cassandra/dcos"
                }
            ],
            [
                {
                    "action": "ScaleApplication",
                    "app": "/cassandra/dcos"
                }
            ]
        ],
        "totalSteps": 2,
        "version": "2015-05-29T01:13:47.694Z"
    }


def app_task_fixture():
    """ Marathon task fixture.

    :rtype: dict
    """

    return {
        "appId": "/zero-instance-app",
        "host": "dcos-01",
        "id": "zero-instance-app.027b3a83-063d-11e5-84a3-56847afe9799",
        "ports": [
            8165
        ],
        "servicePorts": [
            10001
        ],
        "stagedAt": "2015-05-29T19:58:00.907Z",
        "startedAt": "2015-05-29T19:58:01.114Z",
        "version": "2015-05-29T18:50:58.941Z"
    }


def group_fixture():
    """ Marathon group fixture.

    :rtype: dict
    """

    return {
        "apps": [],
        "dependencies": [],
        "groups": [
            {
                "apps": [
                    {
                        "acceptedResourceRoles": None,
                        "args": None,
                        "backoffFactor": 1.15,
                        "backoffSeconds": 1,
                        "cmd": "sleep 1",
                        "constraints": [],
                        "container": None,
                        "cpus": 1.0,
                        "dependencies": [],
                        "disk": 0.0,
                        "env": {},
                        "executor": "",
                        "healthChecks": [],
                        "id": "/test-group/sleep/goodnight",
                        "instances": 0,
                        "labels": {},
                        "maxLaunchDelaySeconds": 3600,
                        "mem": 128.0,
                        "ports": [
                            10000
                        ],
                        "requirePorts": False,
                        "storeUrls": [],
                        "upgradeStrategy": {
                            "maximumOverCapacity": 1.0,
                            "minimumHealthCapacity": 1.0
                        },
                        "uris": [],
                        "user": None,
                        "version": "2015-05-29T23:12:46.187Z"
                    }
                ],
                "dependencies": [],
                "groups": [],
                "id": "/test-group/sleep",
                "version": "2015-05-29T23:12:46.187Z"
            }
        ],
        "id": "/test-group",
        "version": "2015-05-29T23:12:46.187Z"
    }
