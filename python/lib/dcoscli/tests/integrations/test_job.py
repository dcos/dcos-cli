import contextlib
import json
import os

import pytest

from dcos import constants

from dcoscli.test.common import assert_command, exec_command
from dcoscli.test.job import job, show_job, show_job_schedule


def test_help():
    with open('dcoscli/data/help/job.txt') as content:
        assert_command(['dcos', 'job', '--help'],
                       stdout=content.read().encode('utf-8'))


def test_version():
    assert_command(['dcos', 'job', '--version'],
                   stdout=b'dcos-job version SNAPSHOT\n')


def test_schema_config():
    with open('tests/data/metronome/jobs/schema-config.json') as f:
        returncode_, stdout_, stderr_ = exec_command(
            ['dcos', 'job', '--config-schema'], env=None, stdin=None)
        assert str(stdout_.decode("utf-8")) == f.read()


def test_info():
    assert_command(['dcos', 'job', '--info'],
                   stdout=b'Deploy and manage jobs in DC/OS\n')


@pytest.fixture
def env():
    r = os.environ.copy()
    r.update({constants.PATH_ENV: os.environ[constants.PATH_ENV]})

    return r


def test_empty_list():
    _list_jobs()


def test_add_job():
    with _no_schedule_instance_job():
        _list_jobs('pikachu')


def test_add_job_with_schedule():
    with _schedule_instance_job():
        _list_jobs('snorlax')


def test_show_job_schedule():
    with _schedule_instance_job():
        show_job_schedule('snorlax', 'snore-nightly')


def test_add_job_bad_resource():
    stderr = (b'Can\'t read from resource: bad_resource.\n'
              b'Please check that it exists.\n')
    assert_command(['dcos', 'job', 'add', 'bad_resource'],
                   returncode=1,
                   stderr=stderr)


def test_add_bad_json_job():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'job', 'add', 'tests/data/metronome/jobs/bad.json'])

    assert returncode == 1
    assert stderr.decode('utf-8').startswith('Error loading JSON: ')


def test_show_job():
    with _no_schedule_instance_job():
        show_job('pikachu')


def test_show_job_with_blank_jobname():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'job', 'show'])

    assert returncode == 1
    assert "Invalid subcommand usage" in stdout.decode('utf-8')


def test_show_job_with_invalid_jobname():
    assert_command(
        ['dcos', 'job', 'show', 'invalid'],
        stdout=b'',
        stderr=b"Error: Job not found\n",
        returncode=1)


def test_show_job_runs_blank_jobname():
    assert_command(
        ['dcos', 'job', 'show', 'runs'],
        stdout=b'',
        stderr=b"Error: Job not found\n",
        returncode=1)


def test_show_schedule_blank_jobname():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'job', 'schedule', 'show'])

    assert returncode == 1
    assert stdout.decode('utf-8').startswith('Invalid subcommand usage')


def test_show_schedule_invalid_jobname():
    assert_command(
        ['dcos', 'job', 'schedule', 'show', 'invalid'],
        stdout=b'',
        stderr=b"Error: Job not found\n",
        returncode=1)


def test_remove_job():
    with _no_schedule_instance_job():
        pass
    _list_jobs()


def test_update_job():
    with _no_schedule_instance_job():

        original = show_job('pikachu')
        _update_job(
            'pikachu',
            'tests/data/metronome/jobs/update-pikachu.json')

        result = show_job('pikachu')
        assert original['run']['cmd'] != result['run']['cmd']


def test_no_history():

    returncode, stdout, stderr = exec_command(
        ['dcos', 'job', 'history', 'BAD'])

    assert returncode == 1


def test_no_history_with_job():
    with _no_schedule_instance_job():

        returncode, stdout, stderr = exec_command(
            ['dcos', 'job', 'history', 'pikachu'])

        assert returncode == 0


def test_history_deprecated_show_failures():

    with _no_schedule_instance_job():
        returncode, stdout, stderr = exec_command(
            ['dcos', 'job', 'history', 'pikachu', '--show-failures'])

        assert returncode == 0
        assert stderr.decode('utf-8').startswith(
                "'--show-failures' is deprecated")


def test_show_runs():
    with _no_schedule_instance_job():

        _run_job('pikachu')

        returncode, stdout, stderr = exec_command(
            ['dcos', 'job', 'show', 'runs', 'pikachu'])

        assert returncode == 0
        assert 'JOB ID' in stdout.decode('utf-8')
        assert 'pikachu' in stdout.decode('utf-8')


def _run_job(job_id):
    returncode, stdout, stderr = exec_command(
        ['dcos', 'job', 'run', job_id])

    assert returncode == 0
    assert 'Run ID:' in stdout.decode('utf-8')


@contextlib.contextmanager
def _no_schedule_instance_job():
    with job('tests/data/metronome/jobs/pikachu.json',
             'pikachu'):
        yield


@contextlib.contextmanager
def _schedule_instance_job():
    with job('tests/data/metronome/jobs/snorlax.json',
             'snorlax'):
        yield


def _update_job(app_id, file_path):
    assert_command(['dcos', 'job', 'update', file_path])


def _list_jobs(app_id=None):
    returncode, stdout, stderr = exec_command(
        ['dcos', 'job', 'list', '--json'])

    result = json.loads(stdout.decode('utf-8'))

    if app_id is None:
        assert len(result) == 0
    else:
        assert len(result) == 1
        assert result[0]['id'] == app_id

    assert returncode == 0
    assert stderr == b''

    return result
