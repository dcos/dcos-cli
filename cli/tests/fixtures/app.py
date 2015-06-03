def app_fixture():
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
