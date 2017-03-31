
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
        "createdAt": "2017-03-31T16:13:02.937+0000",
        "id": "20170331161302ezZZm",
        "jobId": "pikachu",
        "status": "ACTIVE",
        "tasks": [
          {
            "id": "pikachu_20170331161302ezZZm.eaa9d517-162c-11e7-8bd5-6ef119b8e20f",  # NOQA
            "startedAt": "2017-03-31T16:13:03.842+0000",
            "status": "TASK_RUNNING"
          }
        ]
      },
      {
        "completedAt": None,
        "createdAt": "2017-03-31T16:13:04.398+0000",
        "id": "20170331161304DsJon",
        "jobId": "pikachu",
        "status": "ACTIVE",
        "tasks": [
          {
            "id": "pikachu_20170331161304DsJon.eda7abc8-162c-11e7-8bd5-6ef119b8e20f",  # NOQA
            "startedAt": "2017-03-31T16:13:08.711+0000",
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
        "createdAt": "2017-03-31T16:13:04.398+0000",
        "finishedAt": "2017-03-31T16:13:19.098+0000",
        "id": "20170331161304DsJon"
      },
      {
        "createdAt": "2017-03-31T16:13:02.937+0000",
        "finishedAt": "2017-03-31T16:13:14.339+0000",
        "id": "20170331161302ezZZm"
      },
      {
        "createdAt": "2017-03-31T16:12:33.230+0000",
        "finishedAt": "2017-03-31T16:12:47.829+0000",
        "id": "20170331161233RAlOk"
      },
      {
        "createdAt": "2017-03-31T16:12:31.640+0000",
        "finishedAt": "2017-03-31T16:12:42.898+0000",
        "id": "20170331161231pHgxy"
      },
      {
        "createdAt": "2017-03-31T16:12:03.965+0000",
        "finishedAt": "2017-03-31T16:12:18.601+0000",
        "id": "20170331161203fFize"
      },
      {
        "createdAt": "2017-03-31T16:12:02.264+0000",
        "finishedAt": "2017-03-31T16:12:13.609+0000",
        "id": "20170331161202ew6hO"
      },
      {
        "createdAt": "2017-03-31T16:09:44.433+0000",
        "finishedAt": "2017-03-31T16:09:55.606+0000",
        "id": "201703311609442AaO9"
      },
      {
        "createdAt": "2017-03-31T16:09:39.241+0000",
        "finishedAt": "2017-03-31T16:09:50.703+0000",
        "id": "20170331160939Xfk3N"
      },
      {
        "createdAt": "2017-03-31T16:09:22.510+0000",
        "finishedAt": "2017-03-31T16:09:33.743+0000",
        "id": "20170331160922WfROW"
      },
      {
        "createdAt": "2017-03-31T16:06:17.669+0000",
        "finishedAt": "2017-03-31T16:06:28.908+0000",
        "id": "20170331160617we5IR"
      },
      {
        "createdAt": "2017-03-31T14:21:50.100+0000",
        "finishedAt": "2017-03-31T14:22:01.542+0000",
        "id": "20170331142150e5VB1"
      }
    ]


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
