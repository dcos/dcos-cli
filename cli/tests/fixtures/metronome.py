
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


def job_run_fixture():
    """Job run fixture

    :rtype: dict
    """

    return [
      {
        "completedAt": None,
        "createdAt": "2017-03-31T21:05:30.613+0000",
        "id": "20170331210530QHpRU",
        "jobId": "pikachu",
        "status": "ACTIVE",
        "tasks": [
          {
            "id": "pikachu_20170331210530QHpRU.c5e4b1e7-1655-11e7-8bd5-6ef119b8e20f",  # NOQA
            "startedAt": "2017-03-31T21:05:31.499+0000",
            "status": "TASK_RUNNING"
          }
        ]
      },
      {
        "completedAt": None,
        "createdAt": "2017-03-31T21:05:32.422+0000",
        "id": "20170331210532uxgVF",
        "jobId": "pikachu",
        "status": "ACTIVE",
        "tasks": [
          {
            "id": "pikachu_20170331210532uxgVF.c8e324d8-1655-11e7-8bd5-6ef119b8e20f",  # NOQA
            "startedAt": "2017-03-31T21:05:36.417+0000",
            "status": "TASK_RUNNING"
          }
        ]
      }]


def job_history_fixture():
    """Job history fixture

    :rtype: dict
    """

    return [
      {
        "createdAt": "2017-03-31T21:05:32.422+0000",
        "finishedAt": "2017-03-31T21:05:46.805+0000",
        "id": "20170331210532uxgVF"
      },
      {
        "createdAt": "2017-03-31T21:05:30.613+0000",
        "finishedAt": "2017-03-31T21:05:41.740+0000",
        "id": "20170331210530QHpRU"
      }]


def job_schedule_fixture():
    """Job schedule fixture

    :rtype: dict
    """

    return [
      {
        "concurrencyPolicy": "ALLOW",
        "cron": "20 0 * * *",
        "enabled": True,
        "id": "nightly",
        "nextRunAt": "2017-04-01T00:20:00.000+0000",
        "startingDeadlineSeconds": 900,
        "timezone": "UTC"
      }]
