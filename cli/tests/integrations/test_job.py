import contextlib
import json
import os
import re
import sys
import threading

from dcos import constants

import pytest
from six.moves.BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

from .common import (app, job, assert_command, assert_lines, config_set,
                     config_unset, exec_command, list_deployments, popen_tty,
                     show_app, update_config, watch_all_deployments,
                     watch_deployment)

def test_help():
    with open('tests/data/help/job.txt') as content:
        assert_command(['dcos', 'job', '--help'],
                       stdout=content.read().encode('utf-8'))


def test_version():
    assert_command(['dcos', 'job', '--version'],
                   stdout=b'dcos-job version SNAPSHOT\n')


def test_info():
    assert_command(['dcos', 'marathon', '--info'],
                   stdout=b'Deploy and manage applications to DC/OS\n')


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

def test_add_job_bad_resource():
    stderr = (b'Can\'t read from resource: bad_resource.\n'
              b'Please check that it exists.\n')
    assert_command(['dcos', 'job', 'add', 'bad_resource'],
                   returncode=1,
                   stderr=stderr)


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
