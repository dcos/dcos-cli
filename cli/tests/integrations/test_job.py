import contextlib
import json
import os

import pytest

from dcos import constants

from .common import (assert_command, exec_command, job, show_job,
                     show_job_schedule, update_config)


def test_help():
    with open('tests/data/help/job.txt') as content:
        assert_command(['dcos', 'job', '--help'],
                       stdout=content.read().encode('utf-8'))


def test_version():
    assert_command(['dcos', 'job', '--version'],
                   stdout=b'dcos-job version SNAPSHOT\n')


def test_info():
    assert_command(['dcos', 'job', '--info'],
                   stdout=b'Deploy and manage jobs in DC/OS\n')


@pytest.fixture
def env():
    r = os.environ.copy()
    r.update({
        constants.PATH_ENV: os.environ[constants.PATH_ENV],
        constants.DCOS_CONFIG_ENV: os.path.join("tests", "data", "dcos.toml"),
    })

    return r


def test_missing_config(env):
    with update_config("core.dcos_url", None, env):
        assert_command(
            ['dcos', 'job', 'list'],
            returncode=1,
            stderr=(b'Missing required config parameter: "core.dcos_url".  '
                    b'Please run `dcos config set core.dcos_url <value>`.\n'),
            env=env)


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
    assert "Command not recognized" in stdout.decode('utf-8')


def test_show_job_with_invalid_jobname():
    assert_command(
        ['dcos', 'job', 'show', 'invalid'],
        stdout=b'',
        stderr=b"Job ID: 'invalid' does NOT exist.\n",
        returncode=1)


def test_show_job_runs_blank_jobname():
    assert_command(
        ['dcos', 'job', 'show', 'runs'],
        stdout=b'',
        stderr=b"Job ID: 'runs' does NOT exist.\n",
        returncode=1)


def test_show_schedule_blank_jobname():
    returncode, stdout, stderr = exec_command(
        ['dcos', 'job', 'schedule', 'show'])

    assert returncode == 1
    assert stdout.decode('utf-8').startswith('Command not recognized')


def test_show_schedule_invalid_jobname():
    assert_command(
        ['dcos', 'job', 'schedule', 'show', 'invalid'],
        stdout=b'',
        stderr=b"Job ID: 'invalid' does NOT exist.\n",
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


def test_show_runs():
    with _no_schedule_instance_job():

        _run_job('pikachu')

        returncode, stdout, stderr = exec_command(
            ['dcos', 'job', 'show', 'runs', 'pikachu'])

        assert returncode == 0
        assert 'JOB ID' in stdout.decode('utf-8')
        assert 'pikachu' in stdout.decode('utf-8')


def _run_job(job_id):
    assert_command(['dcos', 'job', 'run', job_id])


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
