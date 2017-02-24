import contextlib
import json

from .common import assert_command, exec_command
from .marathon import watch_deployment


def remove_job(job_id):
    """ Remove a job

    :param job_id: id of job to remove
    :type job_id: str
    :rtype: None
    """

    assert_command(['dcos', 'job', 'remove',
                    '--stop-current-job-runs', job_id])


def show_job(app_id):
    """Show details of a Metronome job.

    :param app_id: The id for the application
    :type app_id: str
    :returns: The requested Metronome job.
    :rtype: dict
    """

    cmd = ['dcos', 'job', 'show', app_id]

    returncode, stdout, stderr = exec_command(cmd)

    assert returncode == 0
    assert stderr == b''

    result = json.loads(stdout.decode('utf-8'))
    assert isinstance(result, dict)
    assert result['id'] == app_id

    return result


def show_job_schedule(app_id, schedule_id):
    """Show details of a Metronome schedule.

    :param app_id: The id for the job
    :type app_id: str
    :param schedule_id: The id for the schedule
    :type schedule_id: str
    :returns: The requested Metronome job.
    :rtype: dict
    """

    cmd = ['dcos', 'job', 'schedule', 'show', app_id, '--json']

    returncode, stdout, stderr = exec_command(cmd)

    assert returncode == 0
    assert stderr == b''

    result = json.loads(stdout.decode('utf-8'))
    assert isinstance(result[0], dict)
    assert result[0]['id'] == schedule_id

    return result[0]


@contextlib.contextmanager
def job(path, job_id):
    """Context manager that deploys a job on entrance, and removes it on
    exit.

    :param path: path to job's json definition:
    :type path: str
    :param job_id: job id
    :type job_id: str
    :param wait: whether to wait for the deploy
    :type wait: bool
    :rtype: None
    """

    add_job(path)
    try:
        yield
    finally:
        remove_job(job_id)


def watch_job_deployments(count=300):
    """Wait for all deployments to complete.

    :param count: max number of seconds to wait
    :type count: int
    :rtype: None
    """

    deps = list_job_deployments()
    for dep in deps:
        watch_deployment(dep['id'], count)


def add_job(job_path):
    """ Add a job, and wait for it to deploy

    :param job_path: path to job's json definition
    :type job_path: str
    :param wait: whether to wait for the deploy
    :type wait: bool
    :rtype: None
    """

    assert_command(['dcos', 'job', 'add', job_path])


def list_job_deployments(expected_count=None, app_id=None):
    """Get all active deployments.

    :param expected_count: assert that number of active deployments
    equals `expected_count`
    :type expected_count: int
    :param app_id: only get deployments for this app
    :type app_id: str
    :returns: active deployments
    :rtype: [dict]
    """

    cmd = ['dcos', 'job', 'list', '--json']
    if app_id is not None:
        cmd.append(app_id)

    returncode, stdout, stderr = exec_command(cmd)

    result = json.loads(stdout.decode('utf-8'))

    assert returncode == 0
    if expected_count is not None:
        assert len(result) == expected_count
    assert stderr == b''

    return result
