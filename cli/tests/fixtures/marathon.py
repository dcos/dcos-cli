import os

from ..integrations.common import file_json_ast

PODS_FILE_PATH_BASE = 'tests/data/marathon/pods'

GOOD_POD_ID = 'good-pod'
GOOD_POD_FILE_PATH = os.path.join(PODS_FILE_PATH_BASE, 'good.json')
UNGOOD_POD_FILE_PATH = \
    os.path.join(PODS_FILE_PATH_BASE, 'ungood.json')
UPDATED_GOOD_POD_FILE_PATH = \
    os.path.join(PODS_FILE_PATH_BASE, 'updated_good.json')
GOOD_POD_STATUS_FILE_PATH = \
    os.path.join(PODS_FILE_PATH_BASE, 'good_status.json')

DOUBLE_POD_ID = 'double-pod'
DOUBLE_POD_FILE_PATH = os.path.join(PODS_FILE_PATH_BASE, 'double.json')

TRIPLE_POD_ID = 'winston'
TRIPLE_POD_FILE_PATH = os.path.join(PODS_FILE_PATH_BASE, 'doubleplusgood.json')

POD_KILL_ID = 'pod-kill'
POD_KILL_FILE_PATH = os.path.join(PODS_FILE_PATH_BASE,
                                  'pod_kill.json')


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


def deployment_fixture_app_pre_pods():
    """ Marathon app deployment fixture, for Marathon versions without pods.

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


def deployment_fixture_app_post_pods():
    """ Marathon app deployment fixture, for Marathon versions with pods.

    :rtype: dict
    """

    return {
        "affectedApps": [
            "/cassandra/dcos"
        ],
        "affectedPods": [],
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


def deployment_fixture_pod():
    """ Marathon pod deployment fixture.

    :rtype: dict
    """

    return {
        "affectedApps": [],
        "affectedPods": [
            "/cassandra/dcos"
        ],
        "currentActions": [
            {
                "action": "ScalePod",
                "pod": "/cassandra/dcos"
            }
        ],
        "currentStep": 2,
        "id": "bebb8ffd-118e-4067-8fcb-d19e44126911",
        "steps": [
            [
                {
                    "action": "StartPod",
                    "pod": "/cassandra/dcos"
                }
            ],
            [
                {
                    "action": "ScalePod",
                    "pod": "/cassandra/dcos"
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


def pod_list_fixture():
    """"Marathon pod list fixture.

    :rtype: [{}]
    """

    good_pod_spec = file_json_ast(GOOD_POD_FILE_PATH)
    double_pod_spec = file_json_ast(DOUBLE_POD_FILE_PATH)
    triple_pod_spec = file_json_ast(TRIPLE_POD_FILE_PATH)

    good_pod_spec["version"] = "2016-10-05T16:18:03.399Z"
    double_pod_spec["version"] = "2016-10-04T27:18:28.183Z"
    triple_pod_spec["version"] = "2016-09-01T31:41:59.265Z"

    good_pod_status = {
        "id": good_pod_spec["id"],
        "instances": [{}, {}, {}],
        "spec": good_pod_spec,
        "status": "stable",
        "statusSince": "2016-10-05T15:36:54.123Z"
    }

    double_pod_status = {
        "id": double_pod_spec["id"],
        "instances": [{}, {}],
        "spec": double_pod_spec,
        "status": "terminal",
        "statusSince": "2016-10-04T03:13:37.101Z"
    }

    triple_pod_status = {
        "id": triple_pod_spec["id"],
        "instances": [{}],
        "spec": triple_pod_spec,
        "status": "degraded",
        "statusSince": "2016-09-30T22:28:09.201Z"
    }

    return [good_pod_status, double_pod_status, triple_pod_status]


def pod_list_without_instances_fixture():
    """Marathon pod without an "instances" field.

    :rtype: {}
    """

    return {
        "id": "/pod-without-instances",
        "spec": {
            "id": "/pod-without-instances",
            "containers": [
                {
                    "name": "no-instances",
                    "exec": {
                        "command": {
                            "shell": "sleep 1000"
                        }
                    },
                    "resources": {
                        "cpus": 0.1,
                        "mem": 16.0
                    }
                }
            ],
            "networks": [
                {
                    "mode": "host"
                }
            ],
            "version": "2016-10-05T16:18:03.399Z"
        },
        "status": "stable",
        "statusSince": "2016-10-05T15:36:54.123Z"
    }


def pod_list_without_spec_version_fixture():
    """Marathon pod without a "spec"."version" field.

    :rtype: {}
    """

    return {
        "id": "/pod-without-spec-version",
        "instances": [{}],
        "spec": {
            "id": "/pod-without-spec-version",
            "containers": [
                {
                    "name": "no-spec-version",
                    "exec": {
                        "command": {
                            "shell": "sleep 1000"
                        }
                    },
                    "resources": {
                        "cpus": 0.1,
                        "mem": 16.0
                    }
                }
            ],
            "networks": [
                {
                    "mode": "host"
                }
            ]
        },
        "status": "stable",
        "statusSince": "2016-10-05T15:36:54.123Z"
    }
