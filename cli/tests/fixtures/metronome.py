
def job_list_fixture():
    """Job list fixture

    :rtype: dict
    """

    return [
      {
        "description": "sleeping is what is do",
        "historySummary": {
          "failureCount": 0,
          "lastFailureAt": None,
          "lastSuccessAt": None,
          "successCount": 0
        },
        "id": "snorlax",
        "labels": {},
        "run": {
          "artifacts": [],
          "cmd": "sleep 10",
          "cpus": 0.01,
          "disk": 0,
          "env": {},
          "maxLaunchDelay": 3600,
          "mem": 32,
          "placement": {
            "constraints": []
          },
          "restart": {
            "policy": "NEVER"
          },
          "volumes": []
        }
      },
      {
        "description": "electrifying rodent",
        "historySummary": {
          "failureCount": 0,
          "lastFailureAt": None,
          "lastSuccessAt": "2017-03-31T14:22:01.541+0000",
          "successCount": 1
        },
        "id": "pikachu",
        "labels": {},
        "run": {
          "artifacts": [],
          "cmd": "sleep 10",
          "cpus": 0.01,
          "disk": 0,
          "env": {},
          "maxLaunchDelay": 3600,
          "mem": 32,
          "placement": {
            "constraints": []
          },
          "restart": {
            "policy": "NEVER"
          },
          "volumes": []
        }
      }]
